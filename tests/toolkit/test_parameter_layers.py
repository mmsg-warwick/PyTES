"""Parameter sets composed from layers (DESIGN D1, issue #3)."""

import pybamm
import pytest

from pytes import parameter_layers as layers
from pytes.fluids import ConstantPropertyLiquid
from pytes.materials import PureMaterial, SensibleMaterial
from pytes.models import finned_tube, packed_bed
from pytes.parameters import DeviceParameters
from pytes.submodels.base_submodel import parameter_names
from pytes.submodels.flux_laws import NewtonCooling

#: The flat default set each named set stands in for
FLAT_SETS = {
    "Finned tube default": finned_tube.get_parameter_values(),
    "Nallusamy2007": packed_bed.get_parameter_values("Nallusamy2007"),
    "Raul2018": packed_bed.get_parameter_values("Raul2018"),
}


def declared(obj):
    """Names of the parameters held by an object's attributes"""
    return set(
        parameter_names(v for v in vars(obj).values() if isinstance(v, pybamm.Symbol))
    )


def flat_layer(set_name, kind):
    """The layer of a kind, with its values from a flat default set"""
    flat = FLAT_SETS[set_name]
    names = layers.KINDS[kind].required
    return {"citations": [], **{name: flat[name] for name in names}}


def flat_layers(set_name):
    return {kind: flat_layer(set_name, kind) for kind in layers.SETS[set_name]}


def is_populated(layer):
    return all(value is not None for key, value in layer.items() if key != "citations")


# Kinds


def test_kinds_hold_the_names_their_classes_read():
    kinds = layers.KINDS
    assert set(kinds["operation"].names) == declared(DeviceParameters())
    assert set(kinds["coupling"].names) == declared(NewtonCooling())
    assert set(kinds["heat_transfer_fluid"].names) == declared(ConstantPropertyLiquid())
    assert set(kinds["pcm"].names) == declared(PureMaterial())
    assert set(kinds["metal"].names) == declared(SensibleMaterial())
    shared = declared(DeviceParameters()) | declared(ConstantPropertyLiquid())
    shared |= declared(PureMaterial()) | declared(SensibleMaterial())
    finned = declared(finned_tube.FinnedTubeParameters()) - shared
    finned_layers = kinds["finned_tube_flow_path"].names
    finned_layers += kinds["finned_tube_storage_element"].names
    assert set(finned_layers) == finned
    bed = declared(packed_bed.PackedBedParameters()) - shared
    bed_layers = kinds["packed_bed_flow_path"].names
    bed_layers += kinds["packed_bed_storage_element"].names
    assert set(bed_layers) == bed


def test_kinds_share_no_names():
    names = [name for kind in layers.KINDS.values() for name in kind.names]
    assert len(names) == len(set(names))


# Registered layers and named sets


@pytest.mark.parametrize("kind", layers.KINDS)
def test_registered_layers_hold_the_names_of_their_kind(kind):
    assert layers.available(kind)
    for name in layers.available(kind):
        layer = layers.get(kind, name)
        assert isinstance(layer["citations"], list)
        layers.check(kind, layer, populated=False)
        # A fresh copy each time
        assert layers.get(kind, name) is not layer


@pytest.mark.parametrize("set_name", layers.SETS)
def test_named_sets_hold_the_names_of_the_flat_sets(set_name):
    names = set()
    for kind, layer_name in layers.SETS[set_name].items():
        names |= set(layers.get(kind, layer_name)) - {"citations"}
    assert names == set(FLAT_SETS[set_name].keys())


@pytest.mark.parametrize("set_name", layers.SETS)
def test_named_sets_reproduce_the_flat_sets(set_name):
    """
    Once a set's layers are populated, it must reproduce the flat default set it replaces.
    A difference is a finding (CLAUDE.md), not a test to edit.
    """
    composition = layers.SETS[set_name]
    if not all(is_populated(layers.get(*item)) for item in composition.items()):
        pytest.skip(f"The layers of '{set_name}' are not populated yet")
    composed = layers.compose_set(set_name)
    flat = FLAT_SETS[set_name]
    for name in flat.keys():
        assert composed[name] == pytest.approx(flat[name]), name


# Checks


def test_check_rejects_missing_foreign_and_unset_names():
    layer = flat_layer("Finned tube default", "metal")
    layers.check("metal", layer)
    with pytest.raises(ValueError, match="lacks"):
        layers.check("metal", {k: v for k, v in layer.items() if "density" not in k})
    with pytest.raises(ValueError, match="names of other kinds"):
        layers.check("metal", {**layer, "PCM latent heat [J.kg-1]": 1})
    unset = {**layer, "Metal density [kg.m-3]": None}
    with pytest.raises(ValueError, match="no value"):
        layers.check("metal", unset)
    layers.check("metal", unset, populated=False)


def test_unknown_kinds_layers_and_sets():
    with pytest.raises(ValueError, match="Unknown layer kind 'fin'"):
        layers.available("fin")
    with pytest.raises(ValueError, match="Unknown pcm layer 'Wax'"):
        layers.get("pcm", "Wax")
    with pytest.raises(ValueError, match="Unknown parameter set 'Big battery'"):
        layers.compose_set("Big battery")


# Composition and swaps


def test_compose_gives_the_union_of_the_layers():
    composed = layers.compose(**flat_layers("Finned tube default"))
    assert isinstance(composed, pybamm.ParameterValues)
    flat = FLAT_SETS["Finned tube default"]
    assert set(composed.keys()) - {"citations"} == set(flat.keys())
    for name in flat.keys():
        assert composed[name] == flat[name]


def test_compose_merges_citations_once():
    composition = flat_layers("Nallusamy2007")
    composition["pcm"]["citations"] = ["Nallusamy2007"]
    composition["packed_bed_storage_element"]["citations"] = ["Nallusamy2007"]
    composed = layers.compose(**composition)
    assert composed["citations"] == ["Nallusamy2007"]


def test_compose_rejects_unpopulated_layers():
    with pytest.raises(ValueError, match="no value"):
        layers.compose(pcm="Finned tube PCM")
    with pytest.raises(ValueError, match="no value"):
        layers.compose_set("Finned tube default")


def test_composed_set_runs_a_model():
    composed = layers.compose(**flat_layers("Finned tube default"))
    model = finned_tube.SharpFrontModel()
    simulation = pybamm.Simulation(
        model, parameter_values=composed, var_pts={"y": 5, "z": 10}
    )
    simulation.solve([0, 60])


def test_swap_replaces_a_layer():
    composed = layers.compose(**flat_layers("Finned tube default"))
    pcm = flat_layer("Nallusamy2007", "pcm")
    pcm["citations"] = ["Nallusamy2007"]
    layers.swap(composed, pcm=pcm)
    for name in layers.KINDS["pcm"].required:
        assert composed[name] == pcm[name]
    assert (
        composed["Tube radius [m]"]
        == FLAT_SETS["Finned tube default"]["Tube radius [m]"]
    )


def test_swap_rejects_a_kind_the_set_lacks():
    composed = layers.compose(**flat_layers("Nallusamy2007"))
    with pytest.raises(ValueError, match="holds no metal layer"):
        layers.swap(composed, metal=flat_layer("Finned tube default", "metal"))
    with pytest.raises(ValueError, match="no value"):
        layers.swap(composed, pcm="Nallusamy2007 paraffin")
