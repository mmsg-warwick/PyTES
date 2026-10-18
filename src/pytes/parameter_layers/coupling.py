#
# Coupling layers
#
"""
Coupling layers: the parameters of the surface flux law between the fluid and the storage
(DESIGN D6, D8). Today, the constant coefficient of :class:`pytes.submodels.NewtonCooling`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`. Values and
citations are to be added, from cited sources.
"""


def finned_tube_default():
    """
    The coefficient of the default finned-tube battery. Stands in for the coupling part of
    the finned-tube default set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Heat transfer coefficient [W.m-2.K-1]": None,
    }


def nallusamy2007():
    """
    The coefficient of the Nallusamy (2007) bed. Stands in for the coupling part of the
    packed-bed "Nallusamy2007" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Heat transfer coefficient [W.m-2.K-1]": None,
    }


def raul2018():
    """
    The coefficient of the "Raul2018" bed. Stands in for the coupling part of the
    packed-bed "Raul2018" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Heat transfer coefficient [W.m-2.K-1]": None,
    }


#: The coupling layers, by name
LAYERS = {
    "Finned tube default": finned_tube_default,
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
}
