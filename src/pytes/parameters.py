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
        "Initial temperature [K]": the initial state is uniform at this temperature, solid
        at the melting temperature (DESIGN D14).
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


def validate_parameter_values(parameter_values, melting_range=None):
    """
    Check that parameter values are physical (DESIGN D14).

    Parameters
    ----------
    parameter_values : pybamm.ParameterValues or dict
        The parameter values.
    melting_range : str, optional
        Name of the melting range parameter, to check that it is not negative.

    Raises
    ------
    ValueError
        If a temperature is not positive or the melting range is negative.
    """
    for name in ("Reference temperature [K]", "Initial temperature [K]"):
        if not parameter_values[name] > 0:
            raise ValueError(f"'{name}' must be positive, got {parameter_values[name]}")
    if melting_range is not None and parameter_values[melting_range] < 0:
        raise ValueError(
            f"'{melting_range}' must not be negative, got "
            f"{parameter_values[melting_range]}"
        )
