#
# Operation layers
#
"""
Operation layers: the energy reference, the initial state and the controls (DESIGN D14).
The same hardware can be run under several of them, e.g. a charge and a discharge.

Each registered layer is a function returning a fresh dict, registered in :data:`LAYERS`,
with the sources of its values in ``"citations"``.

An operation only makes sense relative to the PCM (a discharge starts with the PCM liquid
and cools it below its melting range), so :func:`charge` and :func:`discharge` build one
from a PCM layer and margins chosen by the user, with no values of their own.
"""


def finned_tube_discharge():
    """
    A discharge of the default finned-tube battery: from uniform and liquid at 70 °C, with
    water at 10 °C. Meant for "PCM 60", which melts at 60 °C.

    These values are illustrative and not based on any source.
    """
    return {
        "citations": [],
        "Reference temperature [K]": 283.15,
        "Initial temperature [K]": 343.15,
        "Inlet temperature [K]": 283.15,
        "Mass flow rate [kg.s-1]": 0.02,
    }


def nallusamy2007():
    """
    The charge of Nallusamy, Sampath and Velraj (2007): from 32 °C, with water at 70 °C and
    2 l/min.

    Source: `Nallusamy, Sampath and Velraj (2007)
    <https://doi.org/10.1016/j.renene.2006.04.015>`__.
    """
    return {
        "citations": ["Nallusamy2007"],
        "Reference temperature [K]": 305.15,
        "Initial temperature [K]": 305.15,
        "Inlet temperature [K]": 343.15,
        "Mass flow rate [kg.s-1]": 1 / 30,
    }


def raul2018():
    """
    The charge of Raul et al. (2018): from 400 K, with Hytherm 600 at 180 °C and 8.2 l/min.

    Source: `Raul et al. (2018)
    <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__.
    """
    return {
        "citations": ["Raul2018"],
        "Reference temperature [K]": 400,
        "Initial temperature [K]": 400,
        "Inlet temperature [K]": 453.15,
        "Mass flow rate [kg.s-1]": 98.5e-3,
    }


#: The operation layers, by name
LAYERS = {
    "Finned tube discharge": finned_tube_discharge,
    "Nallusamy2007": nallusamy2007,
    "Raul2018": raul2018,
}


def _melting_range(pcm):
    """The solidus and liquidus temperatures [K] of a PCM layer, or of a registered one"""
    from . import _resolve, check

    pcm = _resolve("pcm", pcm)
    check("pcm", pcm, populated=False)
    T_m = pcm["PCM melting temperature [K]"]
    melting_range = pcm["PCM melting range [K]"]
    if T_m is None or melting_range is None:
        raise ValueError(
            "The PCM layer needs its melting temperature and melting range to build an "
            "operation"
        )
    return T_m - melting_range / 2, T_m + melting_range / 2


def _operation(reference, initial, inlet, mass_flow_rate, margins):
    for name, margin in margins.items():
        if not margin > 0:
            raise ValueError(f"'{name}' must be positive, got {margin}")
    return {
        "citations": [],
        "Reference temperature [K]": reference,
        "Initial temperature [K]": initial,
        "Inlet temperature [K]": inlet,
        "Mass flow rate [kg.s-1]": mass_flow_rate,
    }


def charge(pcm, initial_margin, inlet_margin, mass_flow_rate):
    """
    A charge: from uniform and solid, with fluid hotter than the melting range.

    The initial temperature is ``initial_margin`` below the solidus, the inlet temperature
    ``inlet_margin`` above the liquidus, and the energy reference is the initial
    temperature, so that energies start at zero and grow as the device charges.

    Parameters
    ----------
    pcm : str or dict
        The PCM layer, or the name of a registered one. Its melting temperature and range
        must be set.
    initial_margin, inlet_margin : float
        Positive margins [K] below the solidus and above the liquidus. Margins larger than
        the PCM smoothing width keep the states clear of the smoothed corners.
    mass_flow_rate : float
        "Mass flow rate [kg.s-1]" through the whole device. It depends on the size of the
        device, so it has no default.

    Returns
    -------
    dict
        An operation layer.
    """
    solidus, liquidus = _melting_range(pcm)
    initial = solidus - initial_margin
    return _operation(
        initial,
        initial,
        liquidus + inlet_margin,
        mass_flow_rate,
        {"initial_margin": initial_margin, "inlet_margin": inlet_margin},
    )


def discharge(pcm, initial_margin, inlet_margin, mass_flow_rate):
    """
    A discharge: from uniform and liquid, with fluid colder than the melting range.

    The initial temperature is ``initial_margin`` above the liquidus, the inlet temperature
    ``inlet_margin`` below the solidus, and the energy reference is the inlet temperature,
    so that energies reach zero when the device is fully discharged.

    In both :func:`charge` and :func:`discharge`, the energy reference is the colder end of
    the operation, so energies are never negative.

    Parameters
    ----------
    pcm : str or dict
        The PCM layer, or the name of a registered one. Its melting temperature and range
        must be set.
    initial_margin, inlet_margin : float
        Positive margins [K] above the liquidus and below the solidus.
    mass_flow_rate : float
        "Mass flow rate [kg.s-1]" through the whole device. It has no default.

    Returns
    -------
    dict
        An operation layer.
    """
    solidus, liquidus = _melting_range(pcm)
    inlet = solidus - inlet_margin
    return _operation(
        inlet,
        liquidus + initial_margin,
        inlet,
        mass_flow_rate,
        {"initial_margin": initial_margin, "inlet_margin": inlet_margin},
    )
