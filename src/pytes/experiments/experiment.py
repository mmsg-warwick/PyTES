#
# Experiments for heat battery models
#
"""
Running experiments: sequences of steps (see :mod:`pytes.experiments.step`) that operate the
heat battery through the controls its model declares (DESIGN D9, D10).

The runner follows PyBaMM's "unified" experiment mode: it builds one model for the whole
experiment, in which the controls are solver unknowns. Each distinct kind of step is a
branch of their equations, selected by a step-index input, and each step's termination
conditions are combined into one event, selected the same way. The steps are then solved
one after another, each continuing from the state where the previous one ended.
"""

import warnings

import numpy as np
import pybamm

from .. import compat
from .step import (
    INLET_TEMPERATURE,
    MASS_FLOW_RATE,
    START_TIME,
    BaseStep,
    ConstantPowerFlowRate,
    ConstantPowerInletTemperature,
)

#: Input parameter selecting the active branch of the experiment model (1-based)
STEP_INDEX = pybamm.InputParameter("Step index")


class Experiment:
    """
    A sequence of steps.

    Parameters
    ----------
    operating_conditions : list
        Steps, or tuples (or lists) of steps that form a cycle. As in PyBaMM, a list
        can be repeated, e.g. ``[(charge, discharge)] * 5``.

    Attributes
    ----------
    cycles : list of list
        The steps of each cycle (a single step forms a cycle of its own).
    steps : list
        All the steps, in order.

    Raises
    ------
    TypeError
        If an item is not a :mod:`pytes.experiments.step` step (for example, a PyBaMM
        step string).
    """

    def __init__(self, operating_conditions):
        self.cycles = []
        for item in operating_conditions:
            cycle = list(item) if isinstance(item, tuple | list) else [item]
            for step in cycle:
                if not isinstance(step, BaseStep):
                    raise TypeError(
                        f"Experiment steps must be pytes.experiments.step steps, not "
                        f"{step!r}"
                    )
            self.cycles.append(cycle)
        self.steps = [step for cycle in self.cycles for step in cycle]

    @property
    def unique_steps(self):
        """One step per model branch, in order of first appearance"""
        unique = {}
        for step in self.steps:
            unique.setdefault(step.branch_key, step)
        return list(unique.values())


def _conditional(branches):
    """Select one of the branches with the step index (1-based)"""
    if len(branches) == 1:
        return branches[0]
    return pybamm.Conditional(STEP_INDEX, *branches)


def build_experiment_model(model, experiment, parameter_values):
    """
    Build the experiment version of a model: its controls become solver unknowns, fixed by
    the active step's control residuals.

    Parameters
    ----------
    model : :class:`pytes.BaseModel`
        The model, which is copied (not modified).
    experiment : :class:`Experiment`
        The experiment.
    parameter_values : :class:`pybamm.ParameterValues`
        The parameter values, which are copied (not modified).

    Returns
    -------
    model, parameter_values, branch_index, input_names
        The new model and parameter values, the branch (1-based) of each step's
        ``branch_key``, and the names of all the solver inputs the model needs.

    Raises
    ------
    ValueError
        If a step drives controls the model does not declare.
    """
    controls = model.controls
    for step in experiment.unique_steps:
        unknown = set(step.controls) - set(controls)
        if unknown or len(step.controls) != len(controls):
            raise ValueError(
                f"Step {step.description} drives the controls {sorted(step.controls)}, "
                f"but the model's controls are {sorted(controls)}"
            )
    power = model.power
    model = model.new_copy()
    parameter_values = parameter_values.copy()

    # Each step defines its own terminations; the model's own cut-off event (from
    # operating_mode) would otherwise end the whole experiment
    model.events = [e for e in model.events if e.name != "Cut-off temperature [K]"]

    unique_steps = experiment.unique_steps
    branch_index = {step.branch_key: i + 1 for i, step in enumerate(unique_steps)}

    # The controls become solver unknowns
    mdot_scale = parameter_values[MASS_FLOW_RATE]
    T_in = pybamm.Variable(
        "Inlet temperature control [K]",
        scale=model.temperature_scale,
        reference=model.param.temperature_reference,
    )
    mdot = pybamm.Variable("Mass flow rate control [kg.s-1]", scale=mdot_scale)
    unknowns = {INLET_TEMPERATURE: T_in, MASS_FLOW_RATE: mdot}

    variables = model.variables
    residuals = [
        step.control_residuals(
            variables,
            {name: t.symbol() for name, t in step.targets.items()},
            lambda replaced: power(variables, replaced),
        )
        for step in unique_steps
    ]
    for name, unknown in unknowns.items():
        model.algebraic[unknown] = _conditional([r[name] for r in residuals])
    # As in PyBaMM's unified mode: the solver then builds the Jacobian rows of these
    # switched equations sparsely (1.6 times faster for the sharp-front model)
    model.switching_control_variables = {u.name for u in unknowns.values()}
    # Guesses, made consistent by the solver at the start of the first step (later
    # steps start from the previous state). Use the first step's own values where it
    # has them: guessing an inlet temperature equal to the outlet temperature would
    # make the power independent of the flow rate, and a flow-controlled step could
    # not start.
    first = experiment.steps[0].targets
    T_guess = first.get(INLET_TEMPERATURE)
    mdot_guess = first.get(MASS_FLOW_RATE)
    model.initial_conditions[T_in] = (
        pybamm.Scalar(T_guess.initial_value)
        if T_guess
        else model.variables["Initial uniform temperature [K]"]
    )
    model.initial_conditions[mdot] = pybamm.Scalar(
        mdot_guess.initial_value if mdot_guess else mdot_scale
    )

    # The name marks it as an experiment event, after which the solver may continue
    model.events.append(
        pybamm.Event(
            "Step termination [experiment]",
            _conditional(
                [step.termination_expression(variables) for step in unique_steps]
            ),
        )
    )

    parameter_values[INLET_TEMPERATURE] = T_in
    parameter_values[MASS_FLOW_RATE] = mdot

    input_names = {STEP_INDEX.name, START_TIME.name}
    for step in unique_steps:
        input_names.update(t.input_name for t in step.targets.values() if t.is_constant)
    return model, parameter_values, branch_index, sorted(input_names)


def _failure_hint(step):
    """Likely cause of a solver failure in a step, for the warning"""
    if isinstance(step, ConstantPowerFlowRate):
        return (
            " The mass flow rate needed to hold the power grows without bound as the"
            " outlet temperature approaches the inlet temperature: limit it with"
            " step.mass_flow_rate_above(...)."
        )
    if isinstance(step, ConstantPowerInletTemperature):
        return (
            " Consider limiting the inlet temperature with"
            " step.inlet_temperature_below(...) or step.inlet_temperature_above(...)."
        )
    return ""


def run_experiment(model, experiment, parameter_values=None, var_pts=None, solver=None):
    """
    Run an experiment on a heat battery model.

    Parameters
    ----------
    model : :class:`pytes.BaseModel`
        The model. It is not modified.
    experiment : :class:`Experiment`
        The steps to run.
    parameter_values : :class:`pybamm.ParameterValues`, optional
        Defaults to the model's default parameter values. The controls in it are replaced
        by the steps.
    var_pts : dict, optional
        Mesh points, as for :class:`pybamm.Simulation`.
    solver : :class:`pybamm.BaseSolver`, optional
        Defaults to the model's default solver (it must handle algebraic equations).

    Returns
    -------
    :class:`pybamm.Solution`
        The solution of the whole experiment. ``solution.cycles`` holds one solution per
        cycle, and ``solution.cycles[i].steps`` one per step, each with its
        ``termination`` (the duration, or the termination condition that ended it) and its
        description (:func:`step_description`).
        Steps whose termination condition already holds when they start are skipped,
        with a warning. If the solver fails during a step, the experiment stops there
        with a warning, and the solution up to the end of the previous step is
        returned (as for PyBaMM experiments).
    """
    if parameter_values is None:
        parameter_values = model.default_parameter_values
    exp_model, exp_parameter_values, branch_index, input_names = build_experiment_model(
        model, experiment, parameter_values
    )
    sim = pybamm.Simulation(
        exp_model, parameter_values=exp_parameter_values, var_pts=var_pts, solver=solver
    )

    solution = None
    cycle_solutions = []
    failed = False
    for cycle in experiment.cycles:
        if failed:
            break
        step_solutions = []
        for step in cycle:
            start_time = 0.0 if solution is None else float(solution.t[-1])
            inputs = dict.fromkeys(input_names, 0.0)
            inputs.update(step.input_values())
            inputs[STEP_INDEX.name] = branch_index[step.branch_key]
            inputs[START_TIME.name] = start_time
            # Output times, measured from the start of the step. Passing them as
            # t_interp stops IDAKLU from storing every internal step
            npts = max(2, round(step.duration / step.period) + 1)
            t_interp = np.linspace(0, step.duration, npts)
            n_before = 0 if solution is None else len(solution.sub_solutions)
            try:
                solution = sim.step(
                    step.duration,
                    starting_solution=solution,
                    inputs=inputs,
                    t_eval=np.array([0, step.duration]),
                    t_interp=t_interp,
                )
            except pybamm.SolverError as error:
                if "initial conditions" in str(error):
                    warnings.warn(
                        f"Skipping step {step.description}: its termination condition "
                        f"already holds at the start ({error})",
                        stacklevel=2,
                    )
                    continue
                warnings.warn(
                    f"Stopping the experiment: the solver failed during step "
                    f"{step.description} ({error}).{_failure_hint(step)}",
                    stacklevel=2,
                )
                failed = True
                break
            new = solution.sub_solutions[n_before:]
            step_solution = new[0] if len(new) == 1 else sum(new[1:], new[0])
            compat.set_step_description(step_solution, step.description)
            step_solutions.append(step_solution)
        if step_solutions:
            cycle_solution = (
                step_solutions[0]
                if len(step_solutions) == 1
                else sum(step_solutions[1:], step_solutions[0])
            )
            cycle_solution.steps = step_solutions
            cycle_solutions.append(cycle_solution)
    if solution is None:
        raise pybamm.SolverError("No step of the experiment could be run")
    solution.cycles = cycle_solutions
    return solution


def step_description(step_solution):
    """
    The description of the step a step solution belongs to.

    Parameters
    ----------
    step_solution : pybamm.Solution
        One of ``solution.cycles[i].steps``.

    Returns
    -------
    str or None
    """
    return compat.solution.get_step_description(step_solution)
