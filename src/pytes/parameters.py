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
    T_low, T_high : pybamm.Parameter
        "Lower temperature limit [K]" and "Upper temperature limit [K]": the temperature
        window. It defines the capacity and what states of charge 0 and 1 mean: the uniform
        states at these temperatures (DESIGN D14).
    initial_soc : pybamm.Parameter
        "Initial state of charge". With ``initial_state="state of charge"`` (the default),
        the initial state is the uniform state with this state of charge.
    T_init : pybamm.Parameter
        "Initial temperature [K]". With ``initial_state="temperature"``, the initial state
        is uniform at this temperature (solid at the melting temperature).
    T_in : pybamm.FunctionParameter
        "Inlet temperature [K]", a function of time ("Time [s]"). A control.
    mdot : pybamm.Parameter
        "Mass flow rate [kg.s-1]", through the whole device. A control.
    T_cut : pybamm.Parameter
        "Cut-off temperature [K]", used by the models' ``operating_mode`` events.
    temperature_scale : float
        Scale of the temperature variables [K].
    """

    temperature_scale = 200

    def __init__(self):
        self.T_low = pybamm.Parameter("Lower temperature limit [K]")
        self.T_high = pybamm.Parameter("Upper temperature limit [K]")
        self.initial_soc = pybamm.Parameter("Initial state of charge")
        self.T_init = pybamm.Parameter("Initial temperature [K]")
        self.T_in = pybamm.FunctionParameter(
            "Inlet temperature [K]", {"Time [s]": pybamm.t}
        )
        self.mdot = pybamm.Parameter("Mass flow rate [kg.s-1]")
        self.T_cut = pybamm.Parameter("Cut-off temperature [K]")


def validate_parameter_values(
    parameter_values, melting_temperature=None, melting_range=None
):
    """
    Check the temperature window (DESIGN D14).

    Parameters
    ----------
    parameter_values : pybamm.ParameterValues or dict
        The parameter values.
    melting_temperature, melting_range : str, optional
        Names of the melting temperature and melting range parameters, to check that the
        melting range lies inside the window.

    Raises
    ------
    ValueError
        If the upper limit is not above the lower one, or the melting range is not inside
        the window.
    """
    T_low = parameter_values["Lower temperature limit [K]"]
    T_high = parameter_values["Upper temperature limit [K]"]
    if not T_high > T_low:
        raise ValueError(
            f"The upper temperature limit ({T_high} K) must be above the lower one "
            f"({T_low} K)"
        )
    if melting_temperature is not None:
        T_m = parameter_values[melting_temperature]
        dT_m = parameter_values[melting_range] if melting_range else 0
        if not (T_low < T_m - dT_m and T_m + dT_m < T_high):
            raise ValueError(
                f"The melting range {T_m} ± {dT_m} K must lie inside the temperature "
                f"window [{T_low}, {T_high}] K"
            )
