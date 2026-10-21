"""The packed-bed family: construction, parameter sets and behaviour."""

import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes import conformance
from pytes.models.packed_bed import get_parameter_values


def test_submodels():
    assert list(pytes.PackedBedModel().submodels) == [
        "fluid",
        "storage",
        "coupling",
        "device energy",
        "per-area totals",
    ]


@pytest.fixture(scope="module")
def charge():
    """The default charge (Nallusamy 2007), two hours on the coarse mesh"""
    model = pytes.PackedBedModel()
    t = np.linspace(0, 7200, 121)
    return pybamm.Simulation(model, var_pts=var_pts(model)).solve(
        [0, t[-1]], t_interp=t
    )


def test_charge_melts_the_pcm(charge):
    # Charging takes heat from the fluid: negative power, rising energy and melt
    assert np.all(charge["Power [W]"].entries[1:] < 0)
    assert np.all(np.diff(charge["Total thermal energy [J]"].entries) > 0)
    liquid_fraction = charge["Average liquid fraction"].entries
    # 0 up to the tail of the smoothing of the melting point, 28 K below it
    assert liquid_fraction[0] == pytest.approx(0, abs=1e-4)
    assert liquid_fraction[-1] > 0.5
    T_out = charge["Outlet temperature [degC]"].entries
    assert T_out[0] == pytest.approx(32) and 65 < T_out[-1] < 70


def test_per_area_totals(charge):
    area = get_parameter_values()["Bed cross-sectional area [m2]"]
    for total, unit in [
        ("Power", "W"),
        ("Discharged energy", "J"),
        ("Storage thermal energy", "J"),
        ("Total thermal energy", "J"),
    ]:
        np.testing.assert_allclose(
            charge[f"{total} per unit area [{unit}.m-2]"].entries,
            charge[f"{total} [{unit}]"].entries / area,
            rtol=1e-12,
        )


def test_nallusamy_flow_is_about_2_litres_per_minute():
    values = get_parameter_values("Nallusamy2007")
    litres_per_minute = values["Mass flow rate [kg.s-1]"] / 1000 * 6e4
    assert litres_per_minute == pytest.approx(2, rel=0.01)


def test_raul_parameter_set_runs():
    model = pytes.PackedBedModel()
    solution = pybamm.Simulation(
        model,
        parameter_values=get_parameter_values("Raul2018"),
        var_pts=var_pts(model),
    ).solve([0, 600])
    conformance.check_energy_conservation(solution)


def test_unknown_parameter_set():
    with pytest.raises(ValueError, match="not recognised"):
        get_parameter_values("Nallusamy2008")
