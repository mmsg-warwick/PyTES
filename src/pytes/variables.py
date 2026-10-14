#
# Variable conventions shared by all models
#
"""
Standard variable names (DESIGN D12) and the helper that generates Celsius twins.

Temperatures are defined in K only. :func:`add_temperature_variables` adds each one with its
[degC] twin; temperature differences get K-only names and must not go through it.
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
FLOW_DOMAIN = "pipe"

_KELVIN_OFFSET = 273.15


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
        If a name does not end in "[K]".
    """
    for name, T in temperatures.items():
        if not name.endswith("[K]"):
            raise ValueError(f"Temperature names must end in '[K]', got '{name}'")
        variables[name] = T
        variables[name[: -len("[K]")] + "[degC]"] = T - _KELVIN_OFFSET
    return variables
