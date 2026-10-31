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


def _capsule_surface_per_length():
    p = get_parameter_values()
    eps, R = p["Bed porosity"], p["Capsule radius [m]"]
    return 3 * (1 - eps) / R * p["Bed cross-sectional area [m2]"]


def test_fluid_takes_the_flux_law_heat():
    # The heat the fluid gives up (the ledger, DESIGN D6) is the surface flux law's flux
    # over the capsule surface, also while the capsule surface melts: the default PCM melts
    # at a sharp point and its conductivity drops from 0.4 to 0.15 W.m-1.K-1 (F-056)
    model = pytes.PackedBedModel()
    t = np.linspace(0, 1800, 61)
    solution = pybamm.Simulation(
        model, var_pts=var_pts(model, {"r": 20, "z": 10})
    ).solve([0, t[-1]], t_interp=t)
    flux = solution["Phase-change material boundary heat flux [W.m-2]"].entries
    gain = solution["Heat transfer fluid heat gain per unit length [W.m-1]"].entries
    expected = -flux * _capsule_surface_per_length()
    np.testing.assert_allclose(
        gain, expected, rtol=1e-6, atol=1e-6 * np.abs(gain).max()
    )


def test_charge_heats_the_fluid_monotonically():
    # With a constant inlet temperature, the fluid at every height only warms. A storage
    # that took less than the flux law's heat while its surface melted made the fluid
    # overshoot, then cool by 1 K to 2 K (F-056)
    model = pytes.PackedBedModel()
    t = np.linspace(0, 160 * 60, 321)
    solution = pybamm.Simulation(model).solve([0, t[-1]], t_interp=t)
    fluid = solution["Heat transfer fluid temperature [K]"]
    length = get_parameter_values()["Bed length [m]"]
    for fraction in [0.25, 0.5, 0.75, 1]:
        T = fluid(t=t, z=fraction * length)
        assert np.max(np.maximum.accumulate(T) - T) < 0.1, fraction


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


LUMPED = {"storage element": "lumped"}


def test_lumped_capsule_has_no_capsule_domain():
    model = pytes.PackedBedModel(options=LUMPED)
    assert isinstance(model.submodels["storage"], pytes.submodels.LumpedStorage)
    assert not hasattr(model, "r")
    assert "capsule" not in model.default_geometry
    assert model.submodels["storage"].H.domain == ["flow path"]


def test_resolved_provides_every_lumped_variable():
    # Within a family, the higher fidelity provides every variable of the lower one
    lumped = set(pytes.PackedBedModel(options=LUMPED).variables)
    assert lumped <= set(pytes.PackedBedModel().variables)


def stored_energy(options, conductivity):
    """Stored energy over a two-hour charge, with capsules of the given conductivity"""
    model = pytes.PackedBedModel(options=options)
    parameter_values = model.default_parameter_values
    for phase in ("solid", "liquid"):
        parameter_values[f"PCM {phase} phase conductivity [W.m-1.K-1]"] = conductivity
    t = np.linspace(0, 7200, 61)
    solution = pybamm.Simulation(
        model,
        parameter_values=parameter_values,
        var_pts=var_pts(model, {"r": 10, "z": 40}),
    ).solve([0, t[-1]], t_interp=t)
    return solution["Storage thermal energy [J]"].entries


@pytest.fixture(scope="module")
def lumping_errors():
    """
    Largest difference in stored energy from the resolved capsule, over the change in
    stored energy, by lumped capsule and capsule conductivity
    """
    errors = {}
    for k in (10, 100):
        resolved = stored_energy({}, k)
        change = np.max(np.abs(resolved - resolved[0]))
        for element in ("lumped", "lumped with Jeffreson"):
            lumped = stored_energy({"storage element": element}, k)
            errors[element, k] = np.max(np.abs(lumped - resolved)) / change
    return errors


def test_lumped_converges_to_resolved_as_the_biot_number_falls(lumping_errors):
    # Bi = h R / k is 0.275 and 0.0275 with h = 100 W.m-2.K-1 and R = 27.5 mm: the
    # error is about proportional to it
    assert lumping_errors["lumped", 100] < 2e-3
    assert lumping_errors["lumped", 10] / lumping_errors["lumped", 100] > 5


def test_jeffreson_brings_the_lumped_capsule_closer(lumping_errors):
    for k in (10, 100):
        assert (
            lumping_errors["lumped with Jeffreson", k]
            < 0.6 * lumping_errors["lumped", k]
        )
