"""The experiment runner reproduces the reference runner (heat_batteries at d391da0)."""

from pathlib import Path

import numpy as np

import pytes
from pytes.experiments import Experiment, run_experiment, step_description
from pytes.experiments import step as s

REFERENCE = np.load(
    Path(__file__).parents[1] / "data" / "reference_heat_batteries_d391da0.npz"
)
MDOT = 1000 * 20 / 6e4  # [kg.s-1]
T_COLD = 273.15 + 10


def test_matches_reference_experiment():
    model = pytes.SharpFrontModel()
    steps = [
        s.ConstantInputs(T_COLD, MDOT, duration=60, period=10),
        s.ConstantPower(15e3, inlet_temperature=T_COLD, duration=300, period=10),
        s.ConstantPower(20e3, mass_flow_rate=MDOT, duration=300, period=10),
    ]
    solution = run_experiment(
        model, Experiment(steps), var_pts={model.y: 4, model.z: 5}
    )
    np.testing.assert_allclose(solution.t, REFERENCE["experiment/t"])
    for name in ["Outlet temperature [K]", "Inlet temperature [K]", "Power [W]"]:
        expected = REFERENCE[f"experiment/{name}"]
        np.testing.assert_allclose(
            solution[name].entries, expected, rtol=0, atol=1e-6 * np.max(abs(expected))
        )
    # The reference flow rate was per pipe, in m3.s-1, with water at 1000 kg.m-3
    np.testing.assert_allclose(
        solution["Mass flow rate [kg.s-1]"].entries,
        REFERENCE["experiment/Inlet flow rate [m3.s-1]"] * 1000 * 14,
        rtol=1e-6,
    )
    descriptions = [step_description(st) for c in solution.cycles for st in c.steps]
    assert descriptions == [st.description for st in steps]


def test_steps_must_drive_the_model_controls():
    class OneControlStep(s.ConstantInputs):
        controls = ("Inlet temperature [K]",)

    model = pytes.SharpFrontModel()
    experiment = Experiment([OneControlStep(T_COLD, MDOT, duration=60)])
    try:
        run_experiment(model, experiment)
    except ValueError as error:
        assert "controls" in str(error)
    else:
        raise AssertionError("A step not driving every control was accepted")
