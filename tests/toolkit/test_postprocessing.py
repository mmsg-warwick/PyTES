"""Tests for post-processing and parameter validation (DESIGN D13 to D15)."""

import pytest
from conftest import COARSE_MESH, var_pts

import pytes
from pytes.parameters import validate_parameter_values

T_1, T_2, T_3 = 273.15 + 20, 273.15 + 58, 273.15 + 70


def test_energy_between_is_a_difference(model_class):
    model = model_class()
    mesh = var_pts(model)

    def energy(T_a, T_b):
        return pytes.energy_between(model, T_a, T_b, var_pts=mesh)

    assert energy(T_1, T_1) == 0
    assert energy(T_1, T_3) > 0
    assert energy(T_3, T_1) == pytest.approx(-energy(T_1, T_3), rel=1e-12)
    # Through the melting temperature (solid there) and back out
    assert energy(T_1, T_2) + energy(T_2, T_3) == pytest.approx(
        energy(T_1, T_3), rel=1e-12
    )


def test_energy_between_does_not_depend_on_the_mesh(model_class):
    # Uniform states integrate exactly on any mesh
    model = model_class()
    coarse = pytes.energy_between(model, T_1, T_3, var_pts=var_pts(model))
    finer = pytes.energy_between(
        model,
        T_1,
        T_3,
        var_pts=var_pts(model, {k: 2 * n for k, n in COARSE_MESH.items()}),
    )
    assert coarse == pytest.approx(finer, rel=1e-12)


def test_energy_between_needs_device_energy():
    model = pytes.SharpFrontModel()
    del model.submodels["device energy"]
    with pytest.raises(ValueError, match="no DeviceEnergy"):
        pytes.energy_between(model, T_1, T_3)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Reference temperature [K]", -1),
        ("Initial temperature [K]", 0),
        ("PCM melting range [K]", -0.1),
    ],
)
def test_validate_parameter_values(name, value):
    parameter_values = pytes.SharpFrontModel().default_parameter_values
    validate_parameter_values(parameter_values, "PCM melting range [K]")
    parameter_values[name] = value
    with pytest.raises(ValueError, match="must"):
        validate_parameter_values(parameter_values, "PCM melting range [K]")
