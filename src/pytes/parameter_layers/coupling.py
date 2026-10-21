#
# Coupling layers
#
"""
Coupling layers: the parameters of the surface flux law between the fluid and the storage
(DESIGN D6, D8). Today, the constant coefficient of :class:`pytes.submodels.NewtonCooling`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`.
"""


def finned_tube_default():
    """
    The coefficient of the default finned-tube battery.

    The value is an estimate, not based on any source.
    """
    return {
        "citations": [],
        "Heat transfer coefficient [W.m-2.K-1]": 1000,
    }


def packed_bed_default():
    """
    The coefficient of the packed beds ("Nallusamy2007" and "Raul2018" sets).

    The value is an estimate, not based on any source.
    """
    return {
        "citations": [],
        "Heat transfer coefficient [W.m-2.K-1]": 100,
    }


#: The coupling layers, by name
LAYERS = {
    "Finned tube default": finned_tube_default,
    "Packed bed default": packed_bed_default,
}
