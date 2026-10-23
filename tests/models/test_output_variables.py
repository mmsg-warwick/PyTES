"""Output variables for comparison with measurements (issue #14, F-055)."""

import numpy as np
import pybamm
import pytest
from conftest import MODEL_CLASSES, var_pts

import pytes
from pytes.experiments import Experiment, run_experiment
from pytes.experiments import step as s


@pytest.fixture(scope="module", params=MODEL_CLASSES, ids=lambda c: c.__name__)
def solution(request):
    """Ten minutes of each model's default operation, on the coarse mesh"""
    model = request.param()
    t = np.linspace(0, 600, 61)
    sol = pybamm.Simulation(model, var_pts=var_pts(model)).solve([0, 600], t_interp=t)
    return model, sol


def test_flow_variables(solution):
    model, sol = solution
    pv = model.default_parameter_values
    rho = pv["Heat transfer fluid density [kg.m-3]"]
    mdot = pv["Mass flow rate [kg.s-1]"]
    t = sol["Time [s]"].entries
    np.testing.assert_allclose(sol["Volume flow rate [m3.s-1]"].entries, mdot / rho)
    np.testing.assert_allclose(sol["Pumped volume [m3]"].entries, mdot / rho * t)
    np.testing.assert_allclose(
        sol["Inlet-outlet temperature difference [K]"].entries,
        sol["Inlet temperature [K]"].entries - sol["Outlet temperature [K]"].entries,
    )


def test_velocity_is_the_mean_velocity_in_the_flow_area(solution):
    model, sol = solution
    param = model.param
    path = model.submodels["fluid"].flow_path
    pv = model.default_parameter_values
    expected = pv.evaluate(param.mdot / path.n_paths / (path.area * param.fluid.rho(0)))
    np.testing.assert_allclose(
        sol["Heat transfer fluid velocity [m.s-1]"].entries, expected
    )


def test_average_storage_temperature(solution):
    model, sol = solution
    T_init = model.default_parameter_values["Initial temperature [K]"]
    for submodel in model.submodels.values():
        if not isinstance(submodel, pytes.submodels.EnthalpyStorage):
            continue
        label = submodel.label
        average = sol[f"{label} average temperature [K]"].entries
        field = sol[f"{label} temperature [K]"].entries
        assert average[0] == pytest.approx(T_init)
        axes = tuple(range(field.ndim - 1))
        assert np.all(average >= field.min(axis=axes) - 1e-9)
        assert np.all(average <= field.max(axis=axes) + 1e-9)


def test_reynolds_and_prandtl_numbers_with_a_constant_coefficient():
    # The same flow geometry as the family's correlation, for reporting only
    for cls, correlation in [
        (pytes.SharpFrontModel, "Gnielinski"),
        (pytes.PackedBedModel, "Wakao-Kaguei"),
    ]:
        constant = cls().variables
        with_correlation = cls(options={"heat transfer coefficient": correlation})
        pv = cls().default_parameter_values
        for name in ("Surface Reynolds number", "Surface Prandtl number"):
            assert pv.evaluate(constant[name]) == pytest.approx(
                pv.evaluate(with_correlation.variables[name])
            )


def test_throughputs_over_a_charge_and_a_discharge():
    model = pytes.SharpFrontModel()
    experiment = Experiment(
        [
            s.Power(600, mass_flow_rate=0.02, duration=600),
            s.Power(-600, mass_flow_rate=0.02, duration=600),
        ]
    )
    sol = run_experiment(model, experiment, var_pts=var_pts(model))
    discharged = sol["Discharged energy [J]"].entries
    out = sol["Discharged throughput [J]"].entries
    put_in = sol["Charged throughput [J]"].entries
    np.testing.assert_allclose(sol["Charged energy [J]"].entries, -discharged)
    np.testing.assert_allclose(out - put_in, discharged, atol=1e-6 * np.max(out))
    assert np.all(np.diff(out) >= -1e-6) and np.all(np.diff(put_in) >= -1e-6)
    # 600 W for 600 s each way
    assert out[-1] == pytest.approx(3.6e5, rel=1e-3)
    assert put_in[-1] == pytest.approx(3.6e5, rel=1e-3)


def test_volume_flow_rate_follows_the_controls():
    # The flow rate adjusted by a power step is the experiment's own unknown
    model = pytes.SharpFrontModel()
    experiment = Experiment([s.Power(900, inlet_temperature=283.15, duration=300)])
    sol = run_experiment(model, experiment, var_pts=var_pts(model))
    rho = model.default_parameter_values["Heat transfer fluid density [kg.m-3]"]
    np.testing.assert_allclose(
        sol["Volume flow rate [m3.s-1]"].entries,
        sol["Mass flow rate [kg.s-1]"].entries / rho,
    )
    assert np.ptp(sol["Mass flow rate [kg.s-1]"].entries) > 0
