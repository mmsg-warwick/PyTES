#
# Parameter layers
#
"""
Parameter sets composed from independent layers (DESIGN D1, issue #3).

A parameter set is the union of layers of different kinds: the operation (energy reference,
initial state, controls), the coupling (surface flux law), the heat transfer fluid, the PCM,
the metal of the fins, and the family geometry in two parts: the flow path (the tubes or the
bed, which set the size of the device) and the storage element (the fins or the capsules,
the repeating unit). Each kind holds its own names
(:mod:`pytes.parameter_layers.kinds`), so layers merge without clashes and one can be
swapped, e.g. a PCM, without touching the rest. A layer is a plain dict of PyBaMM parameter
names and values, with the sources of its values in ``"citations"``, and a composed set is a
plain :class:`pybamm.ParameterValues`.

>>> import pytes
>>> parameter_values = pytes.parameter_layers.compose(
...     operation="Finned tube discharge",
...     coupling="Finned tube default",
...     heat_transfer_fluid="Water",
...     pcm="Finned tube PCM",
...     metal="Aluminium",
...     finned_tube_flow_path="Finned tube default",
...     finned_tube_storage_element="Finned tube default",
... )  # doctest: +SKIP
>>> pytes.parameter_layers.swap(parameter_values, pcm=my_pcm)  # doctest: +SKIP
"""

import pybamm

from . import (
    coupling,
    flow_paths,
    heat_transfer_fluids,
    kinds,
    metals,
    operation,
    pcms,
    storage_elements,
)
from .kinds import KINDS, LayerKind

#: The registered layers: for each kind, the functions returning them, by name
LAYERS = {
    "operation": operation.LAYERS,
    "coupling": coupling.LAYERS,
    "heat_transfer_fluid": heat_transfer_fluids.LAYERS,
    "pcm": pcms.LAYERS,
    "metal": metals.LAYERS,
    "finned_tube_flow_path": flow_paths.FINNED_TUBE_LAYERS,
    "finned_tube_storage_element": storage_elements.FINNED_TUBE_LAYERS,
    "packed_bed_flow_path": flow_paths.PACKED_BED_LAYERS,
    "packed_bed_storage_element": storage_elements.PACKED_BED_LAYERS,
}

#: Named compositions: for each set, the name of the layer of each kind. They stand in for
#: the flat default sets of the families, which they replace once their values are added
SETS = {
    "Finned tube default": {
        "operation": "Finned tube discharge",
        "coupling": "Finned tube default",
        "heat_transfer_fluid": "Water",
        "pcm": "Finned tube PCM",
        "metal": "Aluminium",
        "finned_tube_flow_path": "Finned tube default",
        "finned_tube_storage_element": "Finned tube default",
    },
    "Nallusamy2007": {
        "operation": "Nallusamy2007",
        "coupling": "Nallusamy2007",
        "heat_transfer_fluid": "Water",
        "pcm": "Nallusamy2007 paraffin",
        "packed_bed_flow_path": "Nallusamy2007",
        "packed_bed_storage_element": "Nallusamy2007",
    },
    "Raul2018": {
        "operation": "Raul2018",
        "coupling": "Raul2018",
        "heat_transfer_fluid": "Raul2018 thermal oil",
        "pcm": "Raul2018 PCM",
        "packed_bed_flow_path": "Raul2018",
        "packed_bed_storage_element": "Raul2018",
    },
}


def _kind(key):
    try:
        return KINDS[key]
    except KeyError:
        raise ValueError(
            f"Unknown layer kind '{key}'; the kinds are {', '.join(KINDS)}"
        ) from None


def available(kind):
    """
    Names of the registered layers of a kind.

    Parameters
    ----------
    kind : str
        The kind, e.g. "pcm" (see :data:`pytes.parameter_layers.kinds.KINDS`).

    Returns
    -------
    tuple of str
    """
    return tuple(LAYERS[_kind(kind).key])


def get(kind, name):
    """
    A registered layer.

    Parameters
    ----------
    kind : str
        The kind, e.g. "pcm".
    name : str
        The name of the layer (see :func:`available`).

    Returns
    -------
    dict
        A fresh copy of the layer, with its ``"citations"``.
    """
    layers = LAYERS[_kind(kind).key]
    try:
        return layers[name]()
    except KeyError:
        raise ValueError(
            f"Unknown {kind} layer '{name}'; the {kind} layers are {', '.join(layers)}"
        ) from None


def check(kind, layer, populated=True):
    """
    Check that a layer holds the names of its kind, and only those.

    Parameters
    ----------
    kind : str
        The kind, e.g. "pcm".
    layer : dict
        The layer. ``"citations"`` is allowed and not checked.
    populated : bool, optional
        Whether every value must be set (not None). Default True.

    Raises
    ------
    ValueError
        If a required name is missing, a name does not belong to the kind, or (with
        ``populated``) a value is None.
    """
    layer_kind = _kind(kind)
    names = set(layer) - {"citations"}
    missing = set(layer_kind.required) - names
    if missing:
        raise ValueError(f"The {kind} layer lacks {sorted(missing)}")
    foreign = names - set(layer_kind.names)
    if foreign:
        raise ValueError(
            f"The {kind} layer holds names of other kinds: {sorted(foreign)}"
        )
    if populated:
        unset = sorted(name for name in names if layer[name] is None)
        if unset:
            raise ValueError(f"The {kind} layer has no value for {unset}")


def _resolve(kind, layer):
    """The layer itself, given as a dict or as the name of a registered layer"""
    return get(kind, layer) if isinstance(layer, str) else dict(layer)


def compose(**layers):
    """
    Compose a parameter set from layers.

    Parameters
    ----------
    **layers : str or dict
        One layer per kind, keyed by kind (e.g. ``pcm="Finned tube PCM"``): the name of a
        registered layer, or a layer as a dict.

    Returns
    -------
    :class:`pybamm.ParameterValues`
        The union of the layers, with their citations.

    Raises
    ------
    ValueError
        If a layer fails :func:`check`.
    """
    values = {}
    citations = []
    for kind, layer in layers.items():
        layer = _resolve(kind, layer)
        check(kind, layer)
        citations += [c for c in layer.pop("citations", []) if c not in citations]
        values.update(layer)
    return pybamm.ParameterValues({**values, "citations": citations})


def compose_set(name):
    """
    Compose a named set (see :data:`SETS`).

    Parameters
    ----------
    name : str
        The name of the set.

    Returns
    -------
    :class:`pybamm.ParameterValues`
    """
    try:
        layers = SETS[name]
    except KeyError:
        raise ValueError(
            f"Unknown parameter set '{name}'; the sets are {', '.join(SETS)}"
        ) from None
    return compose(**layers)


def swap(parameter_values, **layers):
    """
    Replace layers in a parameter set, in place.

    The set must already hold every name of each new layer's kind it holds, so that a swap
    replaces a layer and cannot add stray names. (This is the check that
    ``ParameterValues.update(check_already_exists=True)`` made before PyBaMM deprecated it.)

    Parameters
    ----------
    parameter_values : :class:`pybamm.ParameterValues`
        The set to update.
    **layers : str or dict
        The new layers, keyed by kind, as for :func:`compose`.

    Raises
    ------
    ValueError
        If a layer fails :func:`check`, or the set does not hold the required names of its
        kind.
    """
    for kind, layer in layers.items():
        layer = _resolve(kind, layer)
        check(kind, layer)
        for citation in layer.pop("citations", []):
            pybamm.citations.register(citation)
        absent = sorted(set(_kind(kind).required) - set(parameter_values.keys()))
        if absent:
            raise ValueError(
                f"The parameter set holds no {kind} layer to swap: it lacks {absent}"
            )
        parameter_values.update(layer)


__all__ = [
    "KINDS",
    "LAYERS",
    "SETS",
    "LayerKind",
    "available",
    "check",
    "compose",
    "compose_set",
    "get",
    "kinds",
    "swap",
]
