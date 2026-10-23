"""Tests for experiments: steps, terminations and the runner."""

import warnings

import numpy as np
import pybamm
import pytest

import pytes
from pytes.experiments import Experiment, run_experiment
from pytes.experiments import step as s

Q0 = 0.02  # mass flow rate [kg.s-1], the default
T_COLD = 273.15 + 10
T_HOT = 273.15 + 80
MESH = {"x": 3, "y": 4, "z": 5}


def mesh(model):
    return {getattr(model, k): n for k, n in MESH.items() if hasattr(model, k)}


def run(steps, model=None):
    model = model or pytes.SharpFrontModel()
    return run_experiment(model, Experiment(steps), var_pts=mesh(model))


def all_steps(solution):
    return [step for cycle in solution.cycles for step in cycle.steps]


def test_constant_inputs_match_plain_solve():
    model = pytes.SharpFrontModel()
    plain = pybamm.Simulation(model, var_pts=mesh(model)).solve(
        [0, 600], t_interp=np.linspace(0, 600, 61)
    )
    solution = run([s.Inlet(T_COLD, Q0, duration=600, period=10)], model)
    np.testing.assert_allclose(
        solution["Outlet temperature [K]"](t=plain.t),
        plain["Outlet temperature [K]"].entries,
        atol=5e-3,
    )


@pytest.mark.parametrize(
    "inlet_temperature", [T_COLD, np.array([[0, T_COLD], [300, T_COLD + 5]])]
)
def test_constant_power_adjusting_flow_rate_as_first_step(inlet_temperature):
    # The first step starts from guesses for the controls, which must not make the
    # power independent of the flow rate
    solution = run([s.Power(900, inlet_temperature=inlet_temperature, duration=300)])
    np.testing.assert_allclose(solution["Power [W]"].entries, 900, rtol=1e-4)


@pytest.mark.parametrize(
    "step",
    [
        s.Power(1200, mass_flow_rate=Q0, duration=300),
        s.Power(900, inlet_temperature=T_COLD, duration=300),
    ],
)
def test_constant_power(step):
    solution = run([s.Inlet(T_COLD, Q0, duration=60), step])
    power = all_steps(solution)[1]["Power [W]"].entries
    target = step.targets["Power [W]"].value
    np.testing.assert_allclose(power, target, rtol=1e-4)


def test_charging_has_negative_power():
    model = pytes.SharpFrontModel()
    pv = model.default_parameter_values
    pv["Initial temperature [K]"] = T_COLD
    solution = run_experiment(
        model,
        Experiment([s.Inlet(T_HOT, Q0, duration=300)]),
        parameter_values=pv,
        var_pts=mesh(model),
    )
    assert np.all(solution["Power [W]"].entries[1:] < 0)


def test_termination_ends_step_and_next_step_continues():
    threshold = 273.15 + 45
    solution = run(
        [
            s.Power(
                1200,
                mass_flow_rate=Q0,
                termination=s.outlet_temperature_below(threshold),
            ),
            s.Inlet(T_COLD, Q0 / 2, duration=120),
        ]
    )
    first, second = all_steps(solution)
    assert "[experiment]" in first.termination
    assert first["Outlet temperature [K]"].entries[-1] == pytest.approx(threshold)
    assert first.t[-1] < 24 * 3600
    # The next step starts where the first one ended
    assert second.t[0] == pytest.approx(first.t[-1])
    for name in ["Outlet temperature [K]", "Phase-change material enthalpy [J.m-3]"]:
        np.testing.assert_allclose(
            second[name].entries[..., 0], first[name].entries[..., -1], rtol=1e-6
        )
    assert second.termination == "final time"
    assert solution.t[-1] == pytest.approx(first.t[-1] + 120)


def test_mass_flow_rate_limit():
    # Holding the power by the flow rate needs more and more flow as the outlet cools
    solution = run(
        [
            s.Power(
                1800,
                inlet_temperature=T_COLD,
                termination=s.mass_flow_rate_above(2 * Q0),
            )
        ]
    )
    flow = solution["Mass flow rate [kg.s-1]"].entries
    assert flow[-1] == pytest.approx(2 * Q0)
    assert "[experiment]" in solution.termination


@pytest.mark.parametrize("model_class", [pytes.SharpFrontModel, pytes.MushModel])
def test_energy_conservation_over_experiment(model_class):
    solution = run(
        [
            s.Power(1200, mass_flow_rate=Q0, duration=300),
            s.Power(900, inlet_temperature=T_COLD, duration=300),
            s.Inlet(T_HOT, Q0, duration=300),
            s.Rest(duration=120),
        ],
        model_class(),
    )
    E = solution["Total thermal energy [J]"].entries
    released = solution["Discharged energy [J]"].entries
    scale = np.max(np.abs(released))
    np.testing.assert_allclose(E[0] - E, released, rtol=0, atol=1e-9 * scale)


def test_time_series_input_is_followed_and_held():
    series = np.array([[0, Q0], [60, Q0 / 2], [120, 0]])
    solution = run(
        [
            s.Inlet(T_COLD, Q0, duration=60),
            s.Inlet(T_COLD, series, duration=180, period=10),
        ]
    )
    step = all_steps(solution)[1]
    t = step.t - step.t[0]
    expected = np.interp(t, series[:, 0], series[:, 1])  # holds 0 after 120 s
    np.testing.assert_allclose(
        step["Mass flow rate [kg.s-1]"].entries, expected, atol=1e-6 * Q0
    )
    # No flow, no power
    assert step["Power [W]"].entries[-1] == pytest.approx(0, abs=1e-6)


def test_function_of_time_input():
    solution = run([s.Inlet(lambda t: T_COLD + t / 60, Q0, duration=120, period=10)])
    np.testing.assert_allclose(
        solution["Inlet temperature [K]"].entries, T_COLD + solution.t / 60, atol=1e-6
    )


def test_steps_with_constant_values_share_a_branch():
    experiment = Experiment(
        [
            s.Inlet(T_COLD, Q0),
            s.Inlet(T_HOT, Q0 / 2),
            s.Power(1200, mass_flow_rate=Q0),
            s.Power(600, mass_flow_rate=Q0 / 2),
            s.Power(600, inlet_temperature=T_COLD),
            # Different structure: a time series, or a different termination
            s.Inlet(T_COLD, np.array([[0, Q0], [60, 0]])),
            s.Inlet(T_COLD, Q0, termination=s.outlet_temperature_below(300)),
        ]
    )
    assert len(experiment.steps) == 7
    assert len(experiment.unique_steps) == 5


def test_cycles():
    cycle = (
        s.Inlet(T_HOT, Q0, duration=120),
        s.Inlet(T_COLD, Q0, duration=120),
    )
    solution = run([cycle] * 3)
    assert len(solution.cycles) == 3
    assert all(len(c.steps) == 2 for c in solution.cycles)
    assert solution.t[-1] == pytest.approx(720)


def test_step_already_terminated_is_skipped():
    # The outlet starts at the initial temperature (70 degC), already above 30 degC
    with pytest.warns(UserWarning, match="Skipping step"):
        solution = run(
            [
                s.Inlet(T_COLD, Q0, duration=60),
                s.Inlet(T_COLD, Q0, termination=s.outlet_temperature_above(303.15)),
                s.Inlet(T_COLD, Q0, duration=60),
            ]
        )
    assert len(all_steps(solution)) == 2
    assert solution.t[-1] == pytest.approx(120)


def test_input_model_is_not_modified():
    model = pytes.SharpFrontModel()
    events = [e.name for e in model.events]
    run([s.Inlet(T_COLD, Q0, duration=60)], model)
    assert [e.name for e in model.events] == events
    assert len(model.algebraic) == 0


@pytest.mark.parametrize(
    "value, error",
    [
        (np.array([1.0, 2.0]), ValueError),
        (np.array([[1, Q0], [2, Q0]]), ValueError),
        ("fast", TypeError),
    ],
)
def test_invalid_targets(value, error):
    with pytest.raises(error):
        s.Inlet(T_COLD, value)


@pytest.mark.parametrize(
    "controls",
    [{}, {"inlet_temperature": T_COLD, "mass_flow_rate": Q0}],
    ids=["neither", "both"],
)
def test_constant_power_adjusts_exactly_one_control(controls):
    with pytest.raises(ValueError, match="exactly one"):
        s.Power(600, **controls)


def test_constant_power_adjusts_the_control_left_free():
    assert s.Power(600, inlet_temperature=T_COLD).adjusted == s.MASS_FLOW_RATE
    assert s.Power(600, mass_flow_rate=Q0).adjusted == s.INLET_TEMPERATURE


def test_invalid_experiment():
    with pytest.raises(TypeError):
        Experiment(["Discharge at 1 W for 1 hour"])


def test_no_warnings_from_time_series_branches():
    # Inactive time-series branches must not trigger extrapolation warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", pybamm.SolverWarning)
        run(
            [
                s.Inlet(T_COLD, np.array([[0, Q0], [60, Q0 / 2]])),
                s.Inlet(T_COLD, Q0, duration=300),
            ]
        )


def test_solver_failure_stops_experiment_with_partial_solution():
    # Holding 1.8 kW by the flow rate once the battery has cooled to the inlet
    # temperature needs unbounded flow (no flow limit is given), so the solver fails
    with pytest.warns(UserWarning, match="mass_flow_rate_above"):
        solution = run(
            [
                s.Inlet(T_COLD, Q0, duration=600),
                s.Power(1800, inlet_temperature=T_COLD, duration=3600),
                s.Inlet(T_COLD, Q0, duration=60),
            ]
        )
    assert solution.t[-1] == pytest.approx(600)
    assert len(all_steps(solution)) == 1


@pytest.mark.parametrize(
    "power_step",
    [
        s.Power(600, mass_flow_rate=Q0, duration=120),
        s.Power(600, inlet_temperature=T_COLD, duration=120),
    ],
)
def test_power_step_after_rest_with_no_flow(power_step):
    # The controls start from the rest step's values (no flow), which must not make the
    # power equation independent of the control it adjusts
    solution = run([s.Rest(inlet_temperature=T_COLD, duration=60), power_step])
    np.testing.assert_allclose(
        all_steps(solution)[1]["Power [W]"].entries, 600, rtol=1e-4
    )


def test_rest_holds_the_previous_inlet_temperature():
    solution = run([s.Inlet(T_HOT - 5, Q0, duration=60), s.Rest(duration=60)])
    rest = all_steps(solution)[1]
    np.testing.assert_allclose(rest["Mass flow rate [kg.s-1]"].entries, 0, atol=1e-12)
    np.testing.assert_allclose(rest["Inlet temperature [K]"].entries, T_HOT - 5)
    np.testing.assert_allclose(rest["Power [W]"].entries, 0, atol=1e-9)


def test_rest_first_holds_the_initial_temperature():
    model = pytes.SharpFrontModel()
    solution = run([s.Rest(duration=60)], model)
    T_init = model.default_parameter_values["Initial temperature [K]"]
    np.testing.assert_allclose(solution["Inlet temperature [K]"].entries, T_init)


def test_rest_with_an_inlet_temperature():
    rest = s.Rest(inlet_temperature=np.array([[0, T_COLD], [60, T_HOT]]), duration=60)
    assert not rest.holds_previous_inlet_temperature
    solution = run([s.Inlet(T_HOT, Q0, duration=60), rest])
    T_in = all_steps(solution)[1]["Inlet temperature [K]"].entries
    assert T_in[0] == pytest.approx(T_COLD) and T_in[-1] == pytest.approx(T_HOT)


def test_custom_termination():
    # Ends the step when the outlet has cooled by 5 K from 70 degC
    def cooled(variables):
        return variables["Outlet temperature [K]"] - (273.15 + 65)

    termination = s.Termination("Outlet cooled by 5 K", cooled)
    assert repr(termination) == "Termination('Outlet cooled by 5 K')"
    assert termination.key.startswith("Outlet cooled by 5 K@")
    solution = run([s.Inlet(T_COLD, Q0, duration=3600, termination=[termination])])
    assert solution["Outlet temperature [degC]"].entries[-1] == pytest.approx(
        65, abs=0.1
    )
    assert solution.t[-1] < 3600


def ramp(start, slope):
    """Inlet temperature [K] rising (or falling) linearly from ``start`` [degC]"""
    return lambda t: 273.15 + start + slope * t


T_70 = 273.15 + 70


@pytest.mark.parametrize(
    "termination, variable, threshold, inlet, initial",
    [
        # The inlet ramps down from 25 degC, or up
        (
            s.inlet_temperature_below(273.15 + 20),
            "Inlet temperature [K]",
            293.15,
            ramp(25, -1 / 60),
            T_70,
        ),
        (
            s.inlet_temperature_above(273.15 + 30),
            "Inlet temperature [K]",
            303.15,
            ramp(25, 1 / 60),
            T_70,
        ),
        # A discharge from liquid freezes the PCM; a charge from solid melts it
        (
            s.average_liquid_fraction_below(0.5),
            "Average liquid fraction",
            0.5,
            T_COLD,
            T_70,
        ),
        (
            s.average_liquid_fraction_above(0.9),
            "Average liquid fraction",
            0.9,
            T_HOT,
            T_COLD,
        ),
    ],
)
def test_threshold_terminations(termination, variable, threshold, inlet, initial):
    # Each ends the step where its variable crosses the threshold
    model = pytes.SharpFrontModel()
    parameter_values = model.default_parameter_values
    parameter_values["Initial temperature [K]"] = initial
    step = s.Inlet(inlet, Q0, duration=6 * 3600, termination=termination)
    solution = run_experiment(
        model,
        Experiment([step]),
        parameter_values=parameter_values,
        var_pts=mesh(model),
    )
    assert solution.t[-1] < 6 * 3600
    assert solution[variable].entries[-1] == pytest.approx(threshold, rel=1e-3)


def test_failure_hints():
    from pytes.experiments.experiment import _failure_hint

    assert "mass_flow_rate_above" in _failure_hint(
        s.Power(1e3, inlet_temperature=T_COLD)
    )
    assert "inlet_temperature_below" in _failure_hint(s.Power(1e3, mass_flow_rate=Q0))
    assert _failure_hint(s.Inlet(T_COLD, Q0)) == ""


def test_experiment_where_no_step_can_run():
    # The only step is over before it starts: the outlet is already above 40 degC
    with pytest.warns(UserWarning), pytest.raises(pybamm.SolverError, match="No step"):
        run(
            [
                s.Inlet(
                    T_COLD,
                    Q0,
                    termination=s.outlet_temperature_above(273.15 + 40),
                )
            ]
        )
