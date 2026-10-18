#
# Operation layers
#
"""
Operation layers: the energy reference, the initial state and the controls (DESIGN D14).
The same hardware can be run under several of them, e.g. a charge and a discharge.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`. Values and
citations are to be added, from cited sources.
"""


def finned_tube_discharge():
    """
    A discharge of the default finned-tube battery: from uniform and liquid, with cold water.
    Stands in for the operation part of the finned-tube default set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Reference temperature [K]": None,
        "Initial temperature [K]": None,
        "Inlet temperature [K]": None,
        "Mass flow rate [kg.s-1]": None,
    }


def nallusamy2007():
    """
    The charge of Nallusamy, Sampath and Velraj (2007). Stands in for the operation part of the
    packed-bed "Nallusamy2007" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Reference temperature [K]": None,
        "Initial temperature [K]": None,
        "Inlet temperature [K]": None,
        "Mass flow rate [kg.s-1]": None,
    }


def raul2018():
    """
    The charge of the "Raul2018" bed. Stands in for the operation part of the packed-bed
    "Raul2018" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Reference temperature [K]": None,
        "Initial temperature [K]": None,
        "Inlet temperature [K]": None,
        "Mass flow rate [kg.s-1]": None,
    }


#: The operation layers, by name
LAYERS = {
    "Finned tube discharge": finned_tube_discharge,
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
}
