#
# Variable conventions shared by all models
#
"""
Standard variable names (DESIGN D12) and the helper that generates Celsius twins.

Temperatures are defined in K only. :func:`add_temperature_variables` adds each one with its
[degC] twin. Temperature differences have no twin (a difference of 5 K is not 5 degC): their
names contain "temperature difference" (e.g. "Inlet-outlet temperature difference [K]"),
and :func:`add_temperature_difference_variables` adds them in K only (DESIGN D12).
"""

#: Variables every model must provide
REQUIRED_VARIABLES = (
    "Time [s]",
    "Mass flow rate [kg.s-1]",
    "Inlet temperature [K]",
    "Outlet temperature [K]",
    "Inlet specific enthalpy [J.kg-1]",
    "Outlet specific enthalpy [J.kg-1]",
    "Power [W]",
    "Discharged energy [J]",
    "Storage thermal energy [J]",
    "Total thermal energy [J]",
    "Heat loss power [W]",
    "Heat transfer fluid specific enthalpy [J.kg-1]",
    "Heat transfer fluid temperature [K]",
)

#: Variables a model may provide, under these names when it does
OPTIONAL_VARIABLES = (
    "Average liquid fraction",
    "Mean storage temperature [K]",
    "Pressure drop [Pa]",
)

#: Name of the flow-path coordinate in every family
FLOW_COORDINATE = "z"

#: Name of the flow-path domain in every family
FLOW_DOMAIN = "flow path"

_KELVIN_OFFSET = 273.15


def is_temperature_difference(name):
    """Whether a variable name denotes a temperature difference (K only, no twin)"""
    return "temperature difference" in name.lower()


def add_temperature_variables(variables, temperatures):
    """
    Add temperatures in [K] to a dictionary of variables, each with its [degC] twin.

    Parameters
    ----------
    variables : dict
        The variables to add to (modified in place).
    temperatures : dict
        Temperatures [K], keyed by names ending in "[K]".

    Returns
    -------
    dict
        ``variables``, for chaining.

    Raises
    ------
    ValueError
        If a name does not end in "[K]", or is a temperature difference (see
        :func:`add_temperature_difference_variables`).
    """
    for name, T in temperatures.items():
        if not name.endswith("[K]"):
            raise ValueError(f"Temperature names must end in '[K]', got '{name}'")
        if is_temperature_difference(name):
            raise ValueError(
                f"'{name}' is a temperature difference, which has no [degC] twin: use "
                "add_temperature_difference_variables"
            )
        variables[name] = T
        variables[name[: -len("[K]")] + "[degC]"] = T - _KELVIN_OFFSET
    return variables


def add_temperature_difference_variables(variables, differences):
    """
    Add temperature differences in [K] to a dictionary of variables, without a twin.

    Parameters
    ----------
    variables : dict
        The variables to add to (modified in place).
    differences : dict
        Temperature differences [K], keyed by names containing "temperature difference"
        and ending in "[K]".

    Returns
    -------
    dict
        ``variables``, for chaining.

    Raises
    ------
    ValueError
        If a name does not end in "[K]" or does not contain "temperature difference".
    """
    for name, dT in differences.items():
        if not (name.endswith("[K]") and is_temperature_difference(name)):
            raise ValueError(
                "Temperature difference names must contain 'temperature difference' and "
                f"end in '[K]', got '{name}'"
            )
        variables[name] = dT
    return variables
