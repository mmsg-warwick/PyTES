#
# Metal layers
#
"""
Metal layers, as read by :class:`pytes.materials.SensibleMaterial` (the fins). One metal per
device for now (issue #3).

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`, with the
sources of its values in ``"citations"``. Each docstring records the temperature at
which the constant values were taken (DESIGN, deferred: temperature-dependent properties).
"""


def aluminium():
    """
    Pure aluminium.

    Source: `CRC Handbook of Chemistry and Physics, 95th edition (2014)
    <https://doi.org/10.1201/b17118>`__.
    Taken at: 298 K for density and heat capacity, 300 K for thermal conductivity.
    """
    return {
        "citations": ["CRC"],
        "Metal conductivity [W.m-1.K-1]": 237,
        "Metal density [kg.m-3]": 2700,
        "Metal specific heat capacity [J.kg-1.K-1]": 897,
    }


def steel():
    """
    Stainless steel, grade 310.

    Source: `CRC Handbook of Chemistry and Physics, 95th edition (2014)
    <https://doi.org/10.1201/b17118>`__.
    Taken at: 298 K.
    """
    return {
        "citations": ["CRC"],
        "Metal conductivity [W.m-1.K-1]": 12.67,
        "Metal density [kg.m-3]": 7829,
        "Metal specific heat capacity [J.kg-1.K-1]": 483,
    }


def copper():
    """
    Copper.

    Source: `CRC Handbook of Chemistry and Physics, 95th edition (2014)
    <https://doi.org/10.1201/b17118>`__.
    Taken at: 298 K for density and heat capacity, 300 K for thermal conductivity.
    """
    return {
        "citations": ["CRC"],
        "Metal conductivity [W.m-1.K-1]": 401,
        "Metal density [kg.m-3]": 8960,
        "Metal specific heat capacity [J.kg-1.K-1]": 385,
    }


#: The metal layers, by name
LAYERS = {
    "Aluminium": aluminium,
    "Steel": steel,
    "Copper": copper,
}
