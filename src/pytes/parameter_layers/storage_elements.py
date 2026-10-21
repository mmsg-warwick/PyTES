#
# Storage element layers
#
"""
Storage element layers: the repeating unit of the storage, independent of the size of the
device. Fins for the finned tube, capsules for the packed bed; one kind per family (DESIGN
D4): ``finned_tube_storage_element`` and ``packed_bed_storage_element``. Every name is per
unit length or per tube, so a longer tube or more tubes keep the same element.

Each layer is a function returning a fresh dict, registered in
:data:`FINNED_TUBE_LAYERS` or :data:`PACKED_BED_LAYERS`, with the sources of its values in
``"citations"``.
"""


def finned_tube_default():
    """
    The fins of the default finned-tube battery.

    These values are illustrative and not based on any source.
    """
    return {
        "citations": [],
        "Fin thickness [m]": 2e-4,
        "Fin pitch [m]": 3e-3,
        "Storage depth [m]": 2e-2,
    }


def nallusamy2007():
    """
    The capsules of Nallusamy, Sampath and Velraj (2007), 55 mm in diameter, and how they
    pack.

    Source: `Nallusamy, Sampath and Velraj (2007)
    <https://doi.org/10.1016/j.renene.2006.04.015>`__.
    """
    return {
        "citations": ["Nallusamy2007"],
        "Capsule radius [m]": 27.5e-3,
        "Bed porosity": 0.5,
    }


def raul2018():
    """
    The capsules of Raul et al. (2018), 31 mm in diameter, and how they pack.

    Source: `Raul et al. (2018)
    <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__.
    """
    return {
        "citations": ["Raul2018"],
        "Capsule radius [m]": 1.55e-2,
        "Bed porosity": 0.6,
    }


def default_capsule():
    """
    A generic spherical capsule, randomly packed in a bed large compared with the capsules.

    These values are illustrative and not based on any source.
    """
    return {
        "citations": [],
        "Capsule radius [m]": 2e-2,
        "Bed porosity": 0.5,
    }


#: The finned-tube storage element layers, by name
FINNED_TUBE_LAYERS = {
    "Finned tube default": finned_tube_default,
}

#: The packed-bed storage element layers, by name
PACKED_BED_LAYERS = {
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
    "Default capsule": default_capsule,
}
