#
# Storage element layers
#
"""
Storage element layers: the repeating unit of the storage, independent of the size of the
device. Fins for the finned tube, capsules for the packed bed; one kind per family (DESIGN
D4): ``finned_tube_storage_element`` and ``packed_bed_storage_element``. Every name is per
unit length or per tube, so a longer tube or more tubes keep the same element.

Each layer is a function returning a fresh dict, registered in
:data:`FINNED_TUBE_LAYERS` or :data:`PACKED_BED_LAYERS`. Values and citations are to be
added, from cited sources.
"""


def finned_tube_default():
    """
    The fins of the default finned-tube battery. Stands in for the fin part of the
    finned-tube default set. "Storage depth [m]" is the height of the fins, which span the
    storage from the tube wall to about half the distance between tubes.

    Source: to be added.
    """
    return {
        "citations": [],
        "Fin thickness [m]": None,
        "Fin pitch [m]": None,
        "Storage depth [m]": None,
    }


def nallusamy2007():
    """
    The capsules of Nallusamy, Sampath and Velraj (2007), and how they pack. Stands in for
    the capsule part of the packed-bed "Nallusamy2007" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Capsule radius [m]": None,
        "Bed porosity": None,
    }


def raul2018():
    """
    The capsules of the "Raul2018" bed, and how they pack. Stands in for the capsule part of
    the packed-bed "Raul2018" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "Capsule radius [m]": None,
        "Bed porosity": None,
    }


#: The finned-tube storage element layers, by name
FINNED_TUBE_LAYERS = {
    "Finned tube default": finned_tube_default,
}

#: The packed-bed storage element layers, by name
PACKED_BED_LAYERS = {
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
}
