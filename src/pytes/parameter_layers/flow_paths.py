#
# Flow path layers
#
"""
Flow path layers: the path the heat transfer fluid follows through the device, and so the
size of the device. One kind per family (DESIGN D4): ``finned_tube_flow_path`` and
``packed_bed_flow_path``.

Each layer is a function returning a fresh dict, registered in
:data:`FINNED_TUBE_LAYERS` or :data:`PACKED_BED_LAYERS`, with the sources of its values in
``"citations"``.
"""

import numpy as np


def finned_tube_default():
    """
    The tube of the default finned-tube battery.

    These values are illustrative and not based on any source.
    """
    return {
        "citations": [],
        "Number of tubes": 1,
        "Tube radius [m]": 3e-3,
        "Tube length [m]": 10,
    }


def nallusamy2007():
    """
    The tank of Nallusamy, Sampath and Velraj (2007): 360 mm in diameter, 460 mm high.

    Source: `Nallusamy, Sampath and Velraj (2007)
    <https://doi.org/10.1016/j.renene.2006.04.015>`__.
    """
    return {
        "citations": ["Nallusamy2007"],
        "Bed length [m]": 0.46,
        "Bed cross-sectional area [m2]": np.pi * 0.18**2,
    }


def raul2018():
    """
    The bed of Raul et al. (2018): 170 mm in diameter, 360 mm long.

    Source: `Raul et al. (2018)
    <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__.
    """
    return {
        "citations": ["Raul2018"],
        "Bed length [m]": 0.36,
        "Bed cross-sectional area [m2]": np.pi * 0.085**2,
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
