"""The experiment runner reproduces its stored results (DESIGN findings, F-048)."""

from pathlib import Path

import numpy as np

import pytes
from pytes.experiments import Experiment, run_experiment, step_description
from pytes.experiments import step as s

#: Outputs of PyTES on the default set, from tests/data/make_reference.py. Before F-048
#: they matched the runner of the finned-tube code prototype (F-027)
REFERENCE = np.load(Path(__file__).parents[1] / "data" / "reference_regression.npz")
MDOT = 0.02  # [kg.s-1], the default
T_COLD = 273.15 + 10


def test_matches_reference_experiment():
    model = pytes.SharpFrontModel()
    steps = [
        s.Inlet(T_COLD, MDOT, duration=60, period=10),
        s.Power(900, inlet_temperature=T_COLD, duration=300, period=10),
        s.Power(1200, mass_flow_rate=MDOT, duration=300, period=10),
    ]
    solution = run_experiment(
        model, Experiment(steps), var_pts={model.y: 4, model.z: 5}
    )
    np.testing.assert_allclose(solution.t, REFERENCE["experiment/t"])
    names = [
        "Outlet temperature [K]",
        "Inlet temperature [K]",
        "Power [W]",
        "Mass flow rate [kg.s-1]",
    ]
    for name in names:
        expected = REFERENCE[f"experiment/{name}"]
        np.testing.assert_allclose(
            solution[name].entries, expected, rtol=0, atol=1e-6 * np.max(abs(expected))
        )
    descriptions = [step_description(st) for c in solution.cycles for st in c.steps]
    assert descriptions == [st.description for st in steps]


def test_steps_must_drive_the_model_controls():
    class OneControlStep(s.Inlet):
        controls = ("Inlet temperature [K]",)

    model = pytes.SharpFrontModel()
    experiment = Experiment([OneControlStep(T_COLD, MDOT, duration=60)])
    try:
        run_experiment(model, experiment)
    except ValueError as error:
        assert "controls" in str(error)
    else:
        raise AssertionError("A step not driving every control was accepted")
