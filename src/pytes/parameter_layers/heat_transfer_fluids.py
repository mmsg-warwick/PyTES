#
# Heat transfer fluid layers
#
"""
Heat transfer fluid layers, as read by :class:`pytes.fluids.ConstantPropertyLiquid`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`. Values and
citations are to be added, from cited sources. "Heat transfer fluid viscosity [Pa.s]" is
optional (no model uses it yet, issue #6).
"""


def water():
    """
    Liquid water. Stands in for the fluid part of the finned-tube default set and of the
    packed-bed "Nallusamy2007" set (the same values in both).

    Source: to be added.
    """
    return {
        "citations": [],
        "Heat transfer fluid density [kg.m-3]": None,
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": None,
        "Heat transfer fluid conductivity [W.m-1.K-1]": None,
    }


def raul2018_thermal_oil():
    """
    The thermal oil of the "Raul2018" bed. Stands in for the fluid part of the packed-bed
    "Raul2018" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Heat transfer fluid density [kg.m-3]": None,
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": None,
        "Heat transfer fluid conductivity [W.m-1.K-1]": None,
    }


#: The heat transfer fluid layers, by name
LAYERS = {
    "Water": water,
    "Raul2018 thermal oil": raul2018_thermal_oil,
}
