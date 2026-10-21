"""Parameter sets composed from layers (DESIGN D1, issue #3)."""

import inspect

import pybamm
import pytest

from pytes import parameter_layers as layers
from pytes.fluids import ConstantPropertyLiquid
from pytes.materials import PureMaterial, SensibleMaterial
from pytes.models import finned_tube, packed_bed
from pytes.parameters import DeviceParameters
from pytes.submodels.base_submodel import parameter_names
from pytes.submodels.flux_laws import NewtonCooling

#: The DOI of each citation key a layer may hold
DOIS = {
    "CRC": "10.1201/b17118",
    "Nallusamy2007": "10.1016/j.renene.2006.04.015",
    "Raul2018": "10.1016/j.applthermaleng.2018.07.123",
}

#: Each family's default sets, by the name of their composition
FAMILY_SETS = {
    "Finned tube default": (finned_tube, None),
    "Nallusamy2007": (packed_bed, "Nallusamy2007"),
    "Raul2018": (packed_bed, "Raul2018"),
}


def declared(obj):
    """Names of the parameters held by an object's attributes"""
    return set(
        parameter_names(v for v in vars(obj).values() if isinstance(v, pybamm.Symbol))
    )


def registered_layers():
    return [
        pytest.param(kind, name, id=f"{kind}: {name}")
        for kind in layers.KINDS
        for name in layers.available(kind)
    ]


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
def test_every_kind_has_a_registered_layer(kind):
    assert layers.available(kind)


@pytest.mark.parametrize("kind, name", registered_layers())
def test_registered_layers_are_complete(kind, name):
    layer = layers.get(kind, name)
    assert isinstance(layer["citations"], list)
    layers.check(kind, layer)
    # A fresh copy each time
    assert layers.get(kind, name) is not layer


@pytest.mark.parametrize("kind, name", registered_layers())
def test_registered_layers_state_their_sources(kind, name):
    """
    A layer links the DOI of each source it cites, and a layer that cites none says that its
    values are illustrative, an estimate or representative.
    """
    doc = inspect.getdoc(layers.LAYERS[kind][name])
    citations = layers.get(kind, name)["citations"]
    for key in citations:
        assert f"<https://doi.org/{DOIS[key]}>`__" in doc, key
    if not citations:
        assert any(
            word in doc for word in ("illustrative", "estimate", "representative")
        )


@pytest.mark.parametrize("set_name", layers.SETS)
def test_named_sets_are_the_family_defaults(set_name):
    family, parameter_set = FAMILY_SETS[set_name]
    default = family.get_parameter_values(parameter_set)
    composed = layers.compose_set(set_name)
    assert set(default.keys()) == set(composed.keys())
    for name in composed.keys():
        assert default[name] == composed[name], name


# Templates


@pytest.mark.parametrize("kind", layers.KINDS)
def test_template_holds_every_name_unset(kind):
    template = layers.template(kind)
    assert template.pop("citations") == []
    assert set(template) == set(layers.KINDS[kind].names)
    assert all(value is None for value in template.values())
    layers.check(kind, template, populated=False)


# Operations built from a PCM


def test_discharge_reproduces_the_finned_tube_operation():
    """70 °C is 9 K above the liquidus of PCM 60 (61 °C), 10 °C is 49 K below the solidus"""
    expected = layers.get("operation", "Finned tube discharge")
    operation = layers.operation.discharge(
        "PCM 60", 9, 49, expected["Mass flow rate [kg.s-1]"]
    )
    layers.check("operation", operation)
    for name in layers.KINDS["operation"].required:
        assert operation[name] == pytest.approx(expected[name]), name


@pytest.mark.parametrize("set_name", ["Nallusamy2007", "Raul2018"])
def test_charge_reproduces_the_packed_bed_operations(set_name):
    composition = layers.SETS[set_name]
    pcm = layers.get("pcm", composition["pcm"])
    expected = layers.get("operation", composition["operation"])
    T_m = pcm["PCM melting temperature [K]"]
    operation = layers.operation.charge(
        pcm,
        T_m - expected["Initial temperature [K]"],
        expected["Inlet temperature [K]"] - T_m,
        expected["Mass flow rate [kg.s-1]"],
    )
    for name in layers.KINDS["operation"].required:
        assert operation[name] == pytest.approx(expected[name]), name


def test_operations_start_clear_of_the_melting_range():
    pcm = {**layers.get("pcm", "Paraffin (Nallusamy 2007)"), "PCM melting range [K]": 4}
    T_m = pcm["PCM melting temperature [K]"]
    charge = layers.operation.charge(pcm, 5, 10, 0.1)
    assert charge["Initial temperature [K]"] == pytest.approx(T_m - 2 - 5)
    assert charge["Inlet temperature [K]"] == pytest.approx(T_m + 2 + 10)
    assert charge["Reference temperature [K]"] == charge["Initial temperature [K]"]
    discharge = layers.operation.discharge(pcm, 5, 10, 0.1)
    assert discharge["Initial temperature [K]"] == pytest.approx(T_m + 2 + 5)
    assert discharge["Inlet temperature [K]"] == pytest.approx(T_m - 2 - 10)
    assert discharge["Reference temperature [K]"] == discharge["Inlet temperature [K]"]


def test_operations_reject_bad_margins_and_unset_pcms():
    pcm = "Paraffin (Nallusamy 2007)"
    with pytest.raises(ValueError, match="'inlet_margin' must be positive"):
        layers.operation.charge(pcm, 5, 0, 0.1)
    with pytest.raises(ValueError, match="'initial_margin' must be positive"):
        layers.operation.discharge(pcm, -1, 5, 0.1)
    with pytest.raises(ValueError, match="melting temperature and melting range"):
        layers.operation.discharge(layers.template("pcm"), 5, 5, 0.1)


# Checks


def test_check_rejects_missing_foreign_and_unset_names():
    layer = layers.get("metal", "Aluminium")
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
    composition = layers.SETS["Finned tube default"]
    composed = layers.compose(**composition)
    assert isinstance(composed, pybamm.ParameterValues)
    names = set()
    for kind, name in composition.items():
        layer = layers.get(kind, name)
        layer.pop("citations")
        names |= set(layer)
        for parameter, value in layer.items():
            assert composed[parameter] == value
    assert set(composed.keys()) - {"citations"} == names


def test_compose_takes_layers_as_dicts():
    composition = layers.SETS["Raul2018"]
    as_dicts = {kind: layers.get(kind, name) for kind, name in composition.items()}
    by_name = layers.compose(**composition)
    composed = layers.compose(**as_dicts)
    for name in by_name.keys():
        assert composed[name] == by_name[name]


def test_compose_merges_citations_once():
    # The operation, PCM, flow path and storage element all cite Nallusamy2007
    composed = layers.compose_set("Nallusamy2007")
    assert composed["citations"] == ["Nallusamy2007", "CRC"]


def test_compose_rejects_unpopulated_layers():
    with pytest.raises(ValueError, match="no value"):
        layers.compose(pcm=layers.template("pcm"))


def test_composed_set_runs_a_model():
    composed = layers.compose_set("Finned tube default")
    model = finned_tube.SharpFrontModel()
    simulation = pybamm.Simulation(
        model, parameter_values=composed, var_pts={"y": 5, "z": 10}
    )
    simulation.solve([0, 60])


def test_swap_replaces_a_layer():
    composed = layers.compose_set("Finned tube default")
    layers.swap(composed, pcm="Paraffin (Nallusamy 2007)")
    pcm = layers.get("pcm", "Paraffin (Nallusamy 2007)")
    for name in layers.KINDS["pcm"].required:
        assert composed[name] == pcm[name]
    tube = layers.get("finned_tube_flow_path", "Finned tube default")
    assert composed["Tube radius [m]"] == tube["Tube radius [m]"]
    # The set gains the new layer's sources, once
    assert composed["citations"] == ["CRC", "Nallusamy2007"]
    layers.swap(composed, pcm="Paraffin (Nallusamy 2007)")
    assert composed["citations"] == ["CRC", "Nallusamy2007"]


def test_swap_rejects_a_kind_the_set_lacks():
    composed = layers.compose_set("Nallusamy2007")
    with pytest.raises(ValueError, match="holds no metal layer"):
        layers.swap(composed, metal="Aluminium")
    with pytest.raises(ValueError, match="no value"):
        layers.swap(composed, pcm=layers.template("pcm"))
