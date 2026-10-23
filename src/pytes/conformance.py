#
# Conformance checks
#
"""
Conformance checks: the executable contract (see ``docs/design/contract.md``).

Every admitted model passes these checks (``tests/conformance/`` runs them over every model).
They are importable so that anyone building a model with PyBaMM directly can check it against
the same contract. Each check raises :class:`AssertionError` with a message when it fails.
"""

import numpy as np
import pybamm

from .postprocessing import energy_between
from .submodels import BaseSubModel, EnthalpyStorage
from .variables import REQUIRED_VARIABLES, is_temperature_difference, unit_twins


def check_required_variables(model):
    """
    Every required variable is defined, and every variable in [K], [W] or [J] has its unit
    twin, except temperature differences, which have none (DESIGN D12)
    """
    missing = [name for name in REQUIRED_VARIABLES if name not in model.variables]
    assert not missing, f"{model.name}: missing required variables {missing}"
    no_twin = [
        name
        for name in model.variables
        if any(twin not in model.variables for twin in unit_twins(name))
    ]
    assert not no_twin, f"{model.name}: variables without a unit twin {no_twin}"
    twinned = [
        name
        for name in model.variables
        if is_temperature_difference(name)
        and name[: -len("[K]")] + "[degC]" in model.variables
    ]
    assert not twinned, (
        f"{model.name}: temperature differences with a [degC] twin {twinned}"
    )


def check_submodels(model):
    """The model lists its submodels, and their declarations fit together"""
    assert model.submodels, f"{model.name}: no submodels"
    for name, submodel in model.submodels.items():
        assert isinstance(submodel, BaseSubModel), (
            f"{model.name}: {name} is not a submodel"
        )
        assert submodel.provides, f"{model.name}: {name} provides nothing"
    model.check_wiring()


def check_controls(model):
    """The model declares its controls, each with a variable of the same name"""
    assert model.controls, f"{model.name}: no controls declared"
    for name in model.controls:
        assert name in model.variables, (
            f"{model.name}: control '{name}' has no variable"
        )


def check_stateless_materials(model):
    """
    For storage whose material declares no internal states, the temperature is a function
    of the enthalpy alone (DESIGN D7)
    """
    for submodel in model.submodels.values():
        if not isinstance(submodel, EnthalpyStorage):
            continue
        if submodel.material.internal_states:
            continue
        variables = {
            node for node in submodel.T.pre_order() if isinstance(node, pybamm.Variable)
        }
        assert variables == {submodel.H}, (
            f"{model.name}: the temperature of {submodel.name!r} depends on "
            f"{sorted(v.name for v in variables)}, not only on the enthalpy"
        )


def check_unit_twins(solution):
    """
    Every unit twin equals its SI variable converted (DESIGN D12), to round-off: the
    solver may evaluate a twin's expression in another order than the conversion here
    """
    model = solution.all_models[0]
    for name in model.variables:
        for twin, convert in unit_twins(name).items():
            expected = convert(solution[name].entries)
            np.testing.assert_allclose(
                solution[twin].entries,
                expected,
                rtol=1e-10,
                atol=1e-10 * np.max(np.abs(expected)),
                err_msg=f"{model.name}: {twin}",
            )


def check_energy_conservation(solution, rtol=1e-9):
    """
    The conservation identity (DESIGN D12), exactly up to round-off:
    ``change in total energy = -int(power) dt - int(heat loss) dt``.

    The heat loss is zero for every current model, so this checks that it is zero and that
    the change in total thermal energy is minus the discharged energy.
    """
    model = solution.all_models[0]
    loss = solution["Heat loss power [W]"].entries
    assert np.all(loss == 0), f"{model.name}: heat losses are not yet in the identity"
    E = solution["Total thermal energy [J]"].entries
    discharged = solution["Discharged energy [J]"].entries
    scale = max(np.max(np.abs(discharged)), np.max(np.abs(E - E[0])))
    np.testing.assert_allclose(
        E - E[0],
        -discharged,
        rtol=0,
        atol=rtol * scale,
        err_msg=f"{model.name}: energy is not conserved",
    )


def check_power_from_enthalpy(solution):
    """The power is ``mdot (h_out - h_in)`` (DESIGN D8)"""
    model = solution.all_models[0]
    expected = solution["Mass flow rate [kg.s-1]"].entries * (
        solution["Outlet specific enthalpy [J.kg-1]"].entries
        - solution["Inlet specific enthalpy [J.kg-1]"].entries
    )
    power = solution["Power [W]"].entries
    np.testing.assert_allclose(
        power,
        expected,
        rtol=1e-12,
        atol=1e-12 * np.max(np.abs(expected)),
        err_msg=f"{model.name}: power is not mdot (h_out - h_in)",
    )


def check_initial_state(model, parameter_values=None, var_pts=None):
    """
    The initial state is uniform at "Initial temperature [K]", and every energy is zero at
    the uniform state at "Reference temperature [K]" (DESIGN D14): the initial total
    thermal energy equals :func:`pytes.energy_between` from the reference temperature to
    the initial one, at the reference itself, below, at and above the melting temperature
    (inside the mushy zone if the material has a melting range)
    """
    parameter_values = (parameter_values or model.default_parameter_values).copy()
    T_ref = parameter_values["Reference temperature [K]"]
    T_m = parameter_values.evaluate(model.param.T_m)
    scale = abs(energy_between(model, T_ref, T_m + 10, parameter_values, var_pts))
    for T in (T_ref, (T_ref + T_m) / 2, T_m, T_m + 10):
        parameter_values["Initial temperature [K]"] = T
        sim = pybamm.Simulation(
            model, parameter_values=parameter_values, var_pts=var_pts
        )
        solution = sim.solve([0, 1])
        T_0 = solution["Initial uniform temperature [K]"].entries[0]
        assert T_0 == T, f"{model.name}: initial temperature {T_0} K, expected {T} K"
        np.testing.assert_allclose(
            solution["Heat transfer fluid temperature [K]"].entries[:, 0],
            T,
            rtol=1e-12,
            err_msg=f"{model.name}: fluid not uniform at {T} K",
        )
        expected = energy_between(model, T_ref, T, parameter_values, var_pts)
        np.testing.assert_allclose(
            solution["Total thermal energy [J]"].entries[0],
            expected,
            rtol=0,
            atol=1e-12 * scale,
            err_msg=f"{model.name}: initial energy at {T} K",
        )


def check_model(model, parameter_values=None, var_pts=None, t_end=600):
    """
    Run every check on a model: its structure, then a solve of ``t_end`` seconds from its
    initial state for the conservation, power and unit-twin checks, then its initial state.
    For a model built from submodels or options of your own, e.g. with a correlation added
    by :func:`pytes.submodels.register_correlation`.

    Parameters
    ----------
    model : :class:`pytes.BaseModel`
        The model.
    parameter_values : :class:`pybamm.ParameterValues`, optional
        The parameter values (default: the model's).
    var_pts : dict, optional
        The mesh (default: the model's).
    t_end : float, optional
        The duration of the solve [s] (default 600).

    Returns
    -------
    :class:`pybamm.Solution`
        The solution of the solve, to inspect further.

    Raises
    ------
    AssertionError
        If a check fails.
    """
    check_required_variables(model)
    check_submodels(model)
    check_controls(model)
    check_stateless_materials(model)
    parameter_values = parameter_values or model.default_parameter_values
    solution = pybamm.Simulation(
        model, parameter_values=parameter_values, var_pts=var_pts
    ).solve([0, t_end])
    check_energy_conservation(solution)
    check_power_from_enthalpy(solution)
    check_unit_twins(solution)
    check_initial_state(model, parameter_values, var_pts)
    return solution
