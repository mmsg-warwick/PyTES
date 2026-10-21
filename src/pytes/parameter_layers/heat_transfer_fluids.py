#
# Heat transfer fluid layers
#
"""
Heat transfer fluid layers, as read by :class:`pytes.fluids.ConstantPropertyLiquid`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`, with the
sources of its values in ``"citations"``. "Heat transfer fluid viscosity [Pa.s]" is
optional (no model uses it yet, issue #6). Each docstring records the temperature at which
the constant values were taken (DESIGN, deferred: temperature-dependent properties).
"""


def water():
    """
    Liquid water. It does not change phase.

    Source: `CRC Handbook of Chemistry and Physics, 95th edition (2014)
    <https://doi.org/10.1201/b17118>`__.
    Taken at: 293.15 K.
    """
    return {
        "citations": ["CRC"],
        "Heat transfer fluid density [kg.m-3]": 998.21,
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 4184.1,
        "Heat transfer fluid conductivity [W.m-1.K-1]": 0.6,
        "Heat transfer fluid viscosity [Pa.s]": 1e-3,
    }


def hytherm_600():
    """
    Hytherm 600, a heat transfer oil.

    Source: `Raul et al. (2018)
    <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__.
    Taken at: not specified.
    """
    return {
        "citations": ["Raul2018"],
        "Heat transfer fluid density [kg.m-3]": 720.9,
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 3097.4,
        "Heat transfer fluid conductivity [W.m-1.K-1]": 0.116,
        "Heat transfer fluid viscosity [Pa.s]": 0.0195,
    }


#: The heat transfer fluid layers, by name
LAYERS = {
    "Water": water,
    "Hytherm 600": hytherm_600,
}
