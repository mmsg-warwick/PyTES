#
# Experiment steps and termination conditions
#
"""
Steps of a heat battery experiment, run with :func:`pytes.experiments.run_experiment`.

A model declares its controls (DESIGN D9); today they are the inlet temperature and the
mass flow rate. Each step declares the controls it drives. In an experiment the controls are
solver unknowns, and each step fixes them with one equation each (its control residuals):
either by holding them at given values, or by adjusting one of them to hold the power. This follows the "unified" experiment mode of
PyBaMM, so that the steps can move to PyBaMM's own experiment framework once it supports
models other than batteries.

The values a step holds can be constants, measured time series (a 2-column array of time
since the start of the step [s] and value) or functions of the time since the start of the
step [s]. Constant values are passed to the solver as inputs, so steps that only differ in
their constant values share the same compiled model branch.

The power is positive when the battery delivers heat (discharge), so a charge at constant
power uses a negative power.
"""

import numbers

import numpy as np
import pybamm

#: Input parameter holding the time [s] at which the current step started
START_TIME = pybamm.InputParameter("Step start time [s]")

#: Default step duration [s] when neither a duration nor a time series sets it
DEFAULT_DURATION = 24 * 3600

#: Default time between output points [s]
DEFAULT_PERIOD = 60

INLET_TEMPERATURE = "Inlet temperature [K]"
MASS_FLOW_RATE = "Mass flow rate [kg.s-1]"


class Termination:
    """
    A condition that ends a step, used in addition to its duration.

    Parameters
    ----------
    name : str
        Name of the condition, used to report why a step ended.
    function : callable
        Function of the model variables (a dict of symbols) returning an expression that
        is positive while the step should continue, and crosses zero when it should end.
    """

    def __init__(self, name, function):
        self.name = name
        self.function = function

    def expression(self, variables):
        """
        The condition as an expression.

        Parameters
        ----------
        variables : dict
            Model variables.

        Returns
        -------
        pybamm.Symbol
            Positive while the step should continue; the step ends when it crosses zero.
        """
        return self.function(variables)

    @property
    def key(self):
        """Identity of the condition, used to decide which steps share a model branch"""
        # The function object is part of the identity (the name alone is not enough)
        return f"{self.name}@{id(self.function)}"

    def __repr__(self):
        return f"Termination({self.name!r})"


class _ThresholdTermination(Termination):
    """
    A variable crossing a threshold.

    Parameters
    ----------
    variable : str
        Name of the model variable.
    threshold : float
        The threshold, in the units of the variable.
    below : bool
        True to end the step when the variable falls below the threshold, False when it
        rises above it.
    """

    def __init__(self, variable, threshold, below):
        self.variable = variable
        self.threshold = threshold
        self.below = below
        sign = "<" if below else ">"
        super().__init__(f"{variable} {sign} {threshold}", None)

    def expression(self, variables):
        """Distance from the threshold, positive while the step should continue"""
        value = variables[self.variable]
        return value - self.threshold if self.below else self.threshold - value

    @property
    def key(self):
        """The name, which includes the variable, direction and threshold"""
        return self.name


def outlet_temperature_below(T):
    """End the step when the outlet temperature [K] falls below T"""
    return _ThresholdTermination("Outlet temperature [K]", T, below=True)


def outlet_temperature_above(T):
    """End the step when the outlet temperature [K] rises above T"""
    return _ThresholdTermination("Outlet temperature [K]", T, below=False)


def inlet_temperature_below(T):
    """End the step when the inlet temperature [K] falls below T"""
    return _ThresholdTermination("Inlet temperature [K]", T, below=True)


def inlet_temperature_above(T):
    """End the step when the inlet temperature [K] rises above T"""
    return _ThresholdTermination("Inlet temperature [K]", T, below=False)


def mass_flow_rate_above(mdot):
    """End the step when the mass flow rate [kg.s-1] rises above mdot"""
    return _ThresholdTermination(MASS_FLOW_RATE, mdot, below=False)


def average_liquid_fraction_below(phi):
    """End the step when the average liquid fraction falls below phi"""
    return _ThresholdTermination("Average liquid fraction", phi, below=True)


def average_liquid_fraction_above(phi):
    """End the step when the average liquid fraction rises above phi"""
    return _ThresholdTermination("Average liquid fraction", phi, below=False)


class Target:
    """
    A value held by a step: a constant, a 2-column time series (time since the start of
    the step [s], value) or a function of the time since the start of the step [s].

    A time series is interpolated linearly, and its last value is held if the step lasts
    longer than the series (unlike PyBaMM drive cycles, which are repeated).

    Parameters
    ----------
    name : str
        Name of the quantity, e.g. "Inlet temperature [K]".
    value : float, numpy.ndarray or callable
        A constant, a 2-column array of time since the start of the step [s] (starting
        at 0) and value, or a function of the time since the start of the step [s]
        (a :class:`pybamm.Symbol`) returning a symbol.

    Raises
    ------
    ValueError
        If a time series is not a 2-column array starting at time 0.
    TypeError
        If the value is none of the above.
    """

    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.is_constant = isinstance(value, numbers.Real) and not isinstance(
            value, bool
        )
        if isinstance(value, np.ndarray):
            if value.ndim != 2 or value.shape[1] != 2:
                raise ValueError(
                    f"{name}: a time series must be a 2-column array of time since the "
                    "start of the step [s] and value"
                )
            if value[0, 0] != 0:
                raise ValueError(f"{name}: a time series must start at time 0")
        elif not self.is_constant and not callable(value):
            raise TypeError(
                f"{name}: must be a number, a 2-column array or a function of time"
            )

    @property
    def input_name(self):
        """Name of the input parameter holding a constant value"""
        return f"{self.name} target"

    def symbol(self):
        """The value as a symbol in the model"""
        if self.is_constant:
            return pybamm.InputParameter(self.input_name)
        t = pybamm.t - START_TIME
        if callable(self.value):
            return self.value(t)
        # Clip the time to the series, which holds the last value after its end. This
        # also keeps the interpolant in range while other steps are active (their
        # branches are evaluated, though not used, at every time).
        t = pybamm.maximum(pybamm.minimum(t, self.value[-1, 0]), 0)
        return pybamm.Interpolant(
            self.value[:, 0], self.value[:, 1], t, name=f"{self.name} time series"
        )

    @property
    def key(self):
        """Identity, used to decide which steps share a model branch"""
        return "input" if self.is_constant else f"series@{id(self.value)}"

    @property
    def initial_value(self):
        """Value at the start of the step, as a number"""
        if self.is_constant:
            return float(self.value)
        if callable(self.value):
            return float(self.value(pybamm.Scalar(0)).evaluate())
        return float(self.value[0, 1])

    @property
    def end_time(self):
        """Last time of a time series, or None"""
        if isinstance(self.value, np.ndarray):
            return float(self.value[-1, 0])
        return None


class BaseStep:
    """
    Base class for experiment steps.

    Subclasses declare the controls they drive (``controls``), pass their targets to this
    constructor and implement :meth:`control_residuals`.

    Parameters
    ----------
    targets : list of :class:`Target`
        The values the step holds.
    duration : float, optional
        Maximum duration of the step [s]. Defaults to the length of the step's time
        series if it has one, otherwise one day.
    termination : :class:`Termination` or list of them, optional
        Conditions that end the step before its duration.
    period : float, optional
        Time between output points [s] (default 60 s).
    description : str, optional
        Description of the step, used when reporting results.
    """

    #: Names of the controls the step drives
    controls = (INLET_TEMPERATURE, MASS_FLOW_RATE)

    def __init__(
        self, targets, duration=None, termination=None, period=None, description=None
    ):
        self.targets = {target.name: target for target in targets}
        if duration is None:
            end_times = [t.end_time for t in targets if t.end_time is not None]
            duration = max(end_times) if end_times else DEFAULT_DURATION
        self.duration = float(duration)
        if termination is None:
            termination = []
        elif isinstance(termination, Termination):
            termination = [termination]
        self.termination = list(termination) + self.safety_terminations()
        self.period = float(period or DEFAULT_PERIOD)
        self.description = description or repr(self)

    def safety_terminations(self):
        """Terminations every step of this type needs (none by default)"""
        return []

    def control_residuals(self, variables, targets, power):
        """
        Equations fixing the controls.

        Parameters
        ----------
        variables : dict
            Model variables, including the controls and "Power [W]".
        targets : dict
            The step's target values as symbols, keyed by name.
        power : callable
            The model's power [W] with some controls replaced: ``power(controls)``, with
            ``controls`` a dict of symbols keyed by control name (see
            :meth:`pytes.BaseModel.power`).

        Returns
        -------
        dict
            One residual per control in ``controls``, keyed by control name.
        """
        raise NotImplementedError

    def termination_expression(self, variables):
        """Combined termination: positive while the step should continue"""
        if not self.termination:
            return pybamm.Scalar(1)
        expressions = [term.expression(variables) for term in self.termination]
        expression = expressions[0]
        for other in expressions[1:]:
            expression = pybamm.minimum(expression, other)
        return expression

    @property
    def branch_key(self):
        """
        Steps with the same key share a model branch: the same type, the same kind of
        targets (constant inputs, or the same time series) and the same terminations.
        """
        targets = ",".join(f"{n}={t.key}" for n, t in sorted(self.targets.items()))
        terms = ",".join(term.key for term in self.termination)
        return f"{type(self).__name__}({targets}; {terms})"

    def input_values(self):
        """Values of the constant targets, as solver inputs"""
        return {
            t.input_name: float(t.value) for t in self.targets.values() if t.is_constant
        }

    def __repr__(self):
        values = ", ".join(
            f"{n}={t.value if t.is_constant else 'series'}"
            for n, t in self.targets.items()
        )
        return f"{type(self).__name__}({values}, duration={self.duration:g} s)"


class ConstantInputs(BaseStep):
    """
    Hold the inlet temperature [K] and the mass flow rate [kg.s-1]. Each can be a constant,
    a time series or a function of time (see :class:`Target`).

    Parameters
    ----------
    inlet_temperature : float, numpy.ndarray or callable
        Inlet temperature [K].
    mass_flow_rate : float, numpy.ndarray or callable
        Mass flow rate through the whole device [kg.s-1]. 0 stops the flow (a rest).
    **kwargs
        ``duration``, ``termination``, ``period`` and ``description``, see
        :class:`BaseStep`.
    """

    def __init__(self, inlet_temperature, mass_flow_rate, **kwargs):
        super().__init__(
            [
                Target(INLET_TEMPERATURE, inlet_temperature),
                Target(MASS_FLOW_RATE, mass_flow_rate),
            ],
            **kwargs,
        )

    def control_residuals(self, variables, targets, power):
        """Both controls equal their targets"""
        return {
            name: variables[name] - targets[name]
            for name in (INLET_TEMPERATURE, MASS_FLOW_RATE)
        }


class ConstantPowerInletTemperature(BaseStep):
    """
    Hold the power [W] (positive for discharge) by adjusting the inlet temperature, at a
    given mass flow rate [kg.s-1]. Use :func:`inlet_temperature_below` and
    :func:`inlet_temperature_above` to limit the inlet temperature.

    Parameters
    ----------
    power : float, numpy.ndarray or callable
        Power of the whole battery [W], positive for discharge and negative for charge.
    mass_flow_rate : float, numpy.ndarray or callable
        Mass flow rate through the whole device [kg.s-1]. Must not be 0: no power can be
        exchanged without flow.
    **kwargs
        ``duration``, ``termination``, ``period`` and ``description``, see
        :class:`BaseStep`.
    """

    def __init__(self, power, mass_flow_rate, **kwargs):
        super().__init__(
            [Target("Power [W]", power), Target(MASS_FLOW_RATE, mass_flow_rate)],
            **kwargs,
        )

    def control_residuals(self, variables, targets, power):
        """
        The power, written with the target mass flow rate, equals its target, and the mass
        flow rate equals its target
        """
        # The power with the target mass flow rate (which the mass flow rate equals in
        # this step), so that the equation depends on the inlet temperature even when the
        # mass flow rate starts from 0 (e.g. after a rest)
        mdot = targets[MASS_FLOW_RATE]
        return {
            INLET_TEMPERATURE: power({MASS_FLOW_RATE: mdot}) - targets["Power [W]"],
            MASS_FLOW_RATE: variables[MASS_FLOW_RATE] - mdot,
        }


class ConstantPowerFlowRate(BaseStep):
    """
    Hold the power [W] (positive for discharge) by adjusting the mass flow rate, at a given
    inlet temperature [K]. Use :func:`mass_flow_rate_above` to limit the mass flow rate: the
    flow needed grows without bound as the outlet temperature approaches the inlet
    temperature. The step also ends if the mass flow rate would become negative.

    Parameters
    ----------
    power : float, numpy.ndarray or callable
        Power of the whole battery [W], positive for discharge and negative for charge.
    inlet_temperature : float, numpy.ndarray or callable
        Inlet temperature [K].
    **kwargs
        ``duration``, ``termination``, ``period`` and ``description``, see
        :class:`BaseStep`.
    """

    def __init__(self, power, inlet_temperature, **kwargs):
        super().__init__(
            [
                Target("Power [W]", power),
                Target(INLET_TEMPERATURE, inlet_temperature),
            ],
            **kwargs,
        )

    def safety_terminations(self):
        """End the step if the flow rate would become negative"""
        return [_ThresholdTermination(MASS_FLOW_RATE, 0, below=True)]

    def control_residuals(self, variables, targets, power):
        """
        The inlet temperature equals its target, and the power, written with the target
        inlet temperature, equals its target
        """
        # The power with the target inlet temperature (which the inlet temperature
        # equals in this step), so that the equation depends on the mass flow rate
        # whatever the inlet temperature starts from
        T_in = targets[INLET_TEMPERATURE]
        return {
            INLET_TEMPERATURE: variables[INLET_TEMPERATURE] - T_in,
            MASS_FLOW_RATE: power({INLET_TEMPERATURE: T_in}) - targets["Power [W]"],
        }
