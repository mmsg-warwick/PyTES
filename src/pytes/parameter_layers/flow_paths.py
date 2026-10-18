#
# Flow path layers
#
"""
Flow path layers: the path the heat transfer fluid follows through the device, and so the
size of the device. One kind per family (DESIGN D4): ``finned_tube_flow_path`` and
``packed_bed_flow_path``.

Each layer is a function returning a fresh dict, registered in
:data:`FINNED_TUBE_LAYERS` or :data:`PACKED_BED_LAYERS`. Values and citations are to be
added, from cited sources.
"""


def finned_tube_default():
    """
    The tubes of the default finned-tube battery (14 tubes). Stands in for the tube part of
    the finned-tube default set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Number of tubes": None,
        "Tube radius [m]": None,
        "Tube length [m]": None,
    }


def nallusamy2007():
    """
    The tank of Nallusamy, Sampath and Velraj (2007). Stands in for the bed size in the
    packed-bed "Nallusamy2007" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Bed length [m]": None,
        "Bed cross-sectional area [m2]": None,
    }


def raul2018():
    """
    The "Raul2018" bed. Stands in for the bed size in the packed-bed "Raul2018" set, whose
    source gives no cross-section (the flat set uses a 1 m2 placeholder).

    Source: to be added.
    """
    return {
        "citations": [],
        "Bed length [m]": None,
        "Bed cross-sectional area [m2]": None,
    }


#: The finned-tube flow path layers, by name
FINNED_TUBE_LAYERS = {
    "Finned tube default": finned_tube_default,
}

#: The packed-bed flow path layers, by name
PACKED_BED_LAYERS = {
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
}
