#
# Metal layers
#
"""
Metal layers, as read by :class:`pytes.materials.SensibleMaterial` (the fins). One metal per
device for now (issue #3).

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`. Values and
citations are to be added, from cited sources.
"""


def aluminium():
    """
    Aluminium. Stands in for the fin part of the finned-tube default set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Metal conductivity [W.m-1.K-1]": None,
        "Metal density [kg.m-3]": None,
        "Metal specific heat capacity [J.kg-1.K-1]": None,
    }


#: The metal layers, by name
LAYERS = {
    "Aluminium": aluminium,
}
