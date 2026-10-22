"""Model options (DESIGN D3) and the averaged storage (DESIGN D4)."""

import numpy as np
import pybamm
import pytest
from conftest import MODEL_CLASSES, var_pts

import pytes


@pytest.fixture(params=MODEL_CLASSES, ids=lambda cls: cls.__name__)
def cls(request):
    return request.param


def test_defaults_are_filled_in(cls):
    defaults = {
        "storage along flow path": "resolved",
        "heat transfer coefficient": "constant",
    }
    assert cls().options == defaults
    averaged = cls(options={"storage along flow path": "averaged"}).options
    assert averaged == {**defaults, "storage along flow path": "averaged"}


@pytest.mark.parametrize(
    "options, match",
    [
        ({"thermal": "lumped"}, "option 'thermal' not recognised"),
        (
            {"storage along flow path": "lumped"},
            "value 'lumped' of option 'storage along flow path' not recognised",
        ),
        # Renamed (F-050): the error gives the new name
        (
            {"storage": "averaged"},
            "option 'storage' was renamed to 'storage along flow path'",
        ),
    ],
)
def test_unknown_options_raise(cls, options, match):
    with pytest.raises(pytes.OptionError, match=match):
        cls(options=options)


def test_averaged_storage_has_no_flow_path_domain(cls):
    def domains(model):
        H = model.submodels["storage"].H
        return [domain for level in H.domains.values() for domain in level]

    assert "flow path" not in domains(
        cls(options={"storage along flow path": "averaged"})
    )
    assert "flow path" in domains(cls())


def test_resolved_provides_every_averaged_variable(cls):
    # Within a family, the higher fidelity provides every variable of the lower one
    resolved = set(cls().variables)
    averaged = set(cls(options={"storage along flow path": "averaged"}).variables)
    assert averaged <= resolved


def stored_energy(cls, storage, flow_factor):
    model = cls(options={"storage along flow path": storage})
    parameter_values = model.default_parameter_values
    parameter_values["Mass flow rate [kg.s-1]"] *= flow_factor
    t = np.linspace(0, 1800, 61)
    solution = pybamm.Simulation(
        model, parameter_values=parameter_values, var_pts=var_pts(model)
    ).solve([0, t[-1]], t_interp=t)
    return solution["Total thermal energy [J]"].entries


def test_averaged_matches_resolved_for_a_uniform_fluid(cls):
    # At high flow the fluid temperature is uniform along the flow path, which is the
    # averaged storage's assumption: the two agree, and they disagree more as the flow
    # falls and a temperature front forms
    differences = []
    for flow_factor in (100, 1):
        resolved = stored_energy(cls, "resolved", flow_factor)
        averaged = stored_energy(cls, "averaged", flow_factor)
        change = np.max(np.abs(resolved - resolved[0]))
        differences.append(np.max(np.abs(resolved - averaged)) / change)
    assert differences[0] < 1e-3
    assert differences[1] > 10 * differences[0]
