"""The finned-tube family: construction, behaviour and agreement with the reference models."""

from pathlib import Path

import numpy as np
import pybamm
import pytest
from conftest import COARSE_MESH, var_pts

import pytes

#: Outputs of heat_batteries at d391da0 (tests/data/make_reference.py)
REFERENCE = np.load(
    Path(__file__).parents[1] / "data" / "reference_heat_batteries_d391da0.npz"
)


def test_can_construct_sharp_front_model():
    model = pytes.SharpFrontModel()
    assert model.name == "Sharp front model"


def test_can_construct_mush_model():
    model = pytes.MushModel()
    assert model.name == "Mush model"


def test_submodels():
    assert list(pytes.SharpFrontModel().submodels) == [
        "fluid",
        "storage",
        "coupling",
        "device energy",
    ]
    assert list(pytes.MushModel().submodels) == [
        "fluid",
        "storage",
        "fins",
        "coupling",
        "fin-PCM coupling",
        "device energy",
    ]


def test_one_storage_submodel_for_every_medium():
    # The fins are enthalpy storage of a sensible material (DESIGN D5): they provide no
    # liquid fraction, so the PCM's is the only one
    submodels = pytes.MushModel().submodels
    assert isinstance(submodels["fins"], pytes.submodels.EnthalpyStorage)
    assert "Fin enthalpy [J.m-3]" in submodels["fins"].provides
    assert "Average liquid fraction" not in submodels["fins"].provides
    assert "Average liquid fraction" in submodels["storage"].provides


def solve(model_class, mesh, dT_m, t, solver=None):
    model = model_class()
    parameter_values = model.default_parameter_values
    parameter_values["PCM smoothing width [K]"] = dT_m
    sim = pybamm.Simulation(
        model,
        parameter_values=parameter_values,
        var_pts=var_pts(model, mesh) if mesh else None,
        solver=solver,
    )
    return sim.solve([0, t[-1]], t_interp=t)


@pytest.mark.parametrize("model_class", [pytes.SharpFrontModel, pytes.MushModel])
def test_discharge_freezes_pcm(model_class):
    # Default parameters start fully charged (liquid) with a cold inlet
    # Tighter than the default tolerances: near the end the outlet is within about 1e-5 K
    # of the inlet, below the default solver error (about 1e-4 K), and the power must
    # stay positive
    solver = pybamm.IDAKLUSolver(rtol=1e-8, atol=1e-10)
    solution = solve(
        model_class, COARSE_MESH, 0.5, np.linspace(0, 1800, 181), solver=solver
    )
    liquid_fraction = solution["Average liquid fraction"].entries
    # Up to the smoothing of the melting point (default smoothing width 0.5 K)
    assert liquid_fraction[0] == pytest.approx(1, abs=1e-3)
    assert liquid_fraction[-1] < 0.1
    assert np.all(np.diff(liquid_fraction) <= 1e-12)
    assert np.all(solution["Power [W]"].entries > 0)
    energy = solution["Total thermal energy [J]"].entries
    assert np.all(np.diff(energy) < 0)


# The reference ran with PyBaMM 26.7 and the same solver tolerances (rtol=1e-5): the
# models solve the same discrete equations (they agree to 3e-7 K at rtol=1e-9), so they
# differ by the solver error only
REFERENCE_CASES = [
    pytest.param(pytes.SharpFrontModel, "sharp_front_coarse_sharp", COARSE_MESH, 0.0),
    pytest.param(pytes.MushModel, "mush_coarse", COARSE_MESH, 0.5),
    pytest.param(pytes.SharpFrontModel, "sharp_front_default", None, 0.5),
    pytest.param(pytes.MushModel, "mush_default", None, 0.5, marks=pytest.mark.slow),
]


@pytest.mark.parametrize("model_class, key, mesh, dT_m", REFERENCE_CASES)
def test_matches_reference(model_class, key, mesh, dT_m):
    t = REFERENCE[f"{key}/t"]
    solution = solve(model_class, mesh, dT_m, t)

    def ref(name):
        return REFERENCE[f"{key}/{name}"]

    np.testing.assert_allclose(
        solution["Outlet temperature [K]"].entries,
        ref("Outlet temperature [K]"),
        rtol=0,
        atol=5e-3,
    )
    power_scale = np.max(np.abs(ref("Power [W]")))
    np.testing.assert_allclose(
        solution["Power [W]"].entries, ref("Power [W]"), rtol=0, atol=1e-4 * power_scale
    )
    np.testing.assert_allclose(
        solution["Discharged energy [J]"].entries,
        ref("Released energy [J]"),
        rtol=1e-4,
    )
    np.testing.assert_allclose(
        solution["Average liquid fraction"].entries,
        ref("Average liquid fraction"),
        rtol=0,
        atol=1e-5,
    )
    # The thermal energies have different references (0 K before, the lower temperature
    # limit now), so compare their changes
    E = solution["Total thermal energy [J]"].entries
    E_ref = ref("Thermal energy [J]")
    np.testing.assert_allclose(E - E[0], E_ref - E_ref[0], rtol=1e-4)
