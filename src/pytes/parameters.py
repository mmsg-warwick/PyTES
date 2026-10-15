#
# Device-level parameters
#
"""
Parameters shared by every family: the device-level description (DESIGN D4, D14).

Family parameter classes inherit from :class:`DeviceParameters` and add their geometry and
materials.
"""

import pybamm


class DeviceParameters:
    """
    Device-level parameters, as PyBaMM symbols.

    Attributes
    ----------
    T_ref : pybamm.Parameter
        "Reference temperature [K]": every energy is zero at the uniform state at this
        temperature (DESIGN D14). Energy differences do not depend on it.
    T_init : pybamm.Parameter
        "Initial temperature [K]": the initial state is the uniform equilibrium state at
        this temperature (DESIGN D14); for a sharp melting point, solid at the melting
        temperature.
    T_in : pybamm.FunctionParameter
        "Inlet temperature [K]", a function of time ("Time [s]"). A control.
    mdot : pybamm.Parameter
        "Mass flow rate [kg.s-1]", through the whole device. A control.
    temperature_scale : float
        Scale of the temperature variables [K].
    """

    temperature_scale = 200

    def __init__(self):
        self.T_ref = pybamm.Parameter("Reference temperature [K]")
        self.T_init = pybamm.Parameter("Initial temperature [K]")
        self.T_in = pybamm.FunctionParameter(
            "Inlet temperature [K]", {"Time [s]": pybamm.t}
        )
        self.mdot = pybamm.Parameter("Mass flow rate [kg.s-1]")


def validate_parameter_values(parameter_values, non_negative=()):
    """
    Check that parameter values are physical (DESIGN D14).

    Parameters
    ----------
    parameter_values : pybamm.ParameterValues or dict
        The parameter values.
    non_negative : iterable of str, optional
        Names of parameters that must not be negative, e.g. "PCM melting range [K]" and
        "PCM smoothing width [K]".

    Raises
    ------
    ValueError
        If a temperature is not positive or a parameter in ``non_negative`` is negative.
    """
    for name in ("Reference temperature [K]", "Initial temperature [K]"):
        if not parameter_values[name] > 0:
            raise ValueError(f"'{name}' must be positive, got {parameter_values[name]}")
    for name in non_negative:
        if parameter_values[name] < 0:
            raise ValueError(
                f"'{name}' must not be negative, got {parameter_values[name]}"
            )
