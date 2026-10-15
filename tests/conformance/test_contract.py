"""The contract every model must meet (DESIGN D3, D7 to D14). See docs/design/contract.md."""

import numpy as np
import pybamm
import pytest
from conftest import COARSE_MESH, var_pts

from pytes import conformance


def solve(model, mesh, dT_m=0, t_end=1800, melting_range=0):
    parameter_values = model.default_parameter_values
    parameter_values["PCM smoothing width [K]"] = dT_m
    parameter_values["PCM melting range [K]"] = melting_range
    sim = pybamm.Simulation(
        model, var_pts=var_pts(model, mesh), parameter_values=parameter_values
    )
    return sim.solve([0, t_end], t_interp=np.linspace(0, t_end, 181))


@pytest.fixture(scope="module")
def solutions():
    """One discharge per model on the coarse mesh, shared by the checks below"""
    cache = {}

    def get(model_class):
        if model_class not in cache:
            cache[model_class] = solve(model_class(), COARSE_MESH)
        return cache[model_class]

    return get


def test_required_variables(model_class):
    conformance.check_required_variables(model_class())


def test_submodels(model_class):
    conformance.check_submodels(model_class())


def test_controls(model_class):
    conformance.check_controls(model_class())


def test_stateless_materials(model_class):
    conformance.check_stateless_materials(model_class())


def test_no_events(model_class):
    # Cut-offs are experiment terminations (DESIGN D11)
    assert model_class().events == []


# The discretisation conserves energy exactly, on any mesh, so the balance only differs
# by round-off
@pytest.mark.parametrize(
    "mesh, dT_m, melting_range",
    [
        (COARSE_MESH, 0, 0),
        ({"x": 3, "y": 3, "z": 4}, 0, 0),
        (COARSE_MESH, 0.5, 0),
        (COARSE_MESH, 0, 2),
        (COARSE_MESH, 0.5, 2),
    ],
)
def test_energy_conservation(model_class, mesh, dT_m, melting_range):
    conformance.check_energy_conservation(
        solve(model_class(), mesh, dT_m, melting_range=melting_range)
    )


def test_power_from_enthalpy(model_class, solutions):
    conformance.check_power_from_enthalpy(solutions(model_class))


def test_celsius_twins(model_class, solutions):
    conformance.check_celsius_twins(solutions(model_class))


@pytest.mark.parametrize("melting_range", [0, 2])
def test_initial_state(model_class, melting_range):
    model = model_class()
    parameter_values = model.default_parameter_values
    parameter_values["PCM melting range [K]"] = melting_range
    conformance.check_initial_state(model, parameter_values, var_pts(model))
