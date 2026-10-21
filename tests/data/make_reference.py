"""
Generate ``reference_regression.npz``: outputs of PyTES on its default parameter set, against
which ``tests/models/test_finned_tube.py`` and ``tests/experiments/test_reference.py``
check that later changes do not move the results (DESIGN findings, F-048).

Run from the repository root, and commit the new file with the change that moves the
results, saying why in its message::

    uv run python tests/data/make_reference.py

The slowest case, the mush model on its default mesh, takes about a minute.
"""

import sys
from pathlib import Path

import numpy as np
import pybamm

import pytes
from pytes.experiments import Experiment, run_experiment
from pytes.experiments import step as s

sys.path.insert(0, str(Path(__file__).parents[1]))
from conftest import COARSE_MESH, var_pts  # noqa: E402

PATH = Path(__file__).parent / "reference_regression.npz"

#: Name, model, mesh (None for the default) and smoothing width (None for the default)
CASES = [
    ("sharp_front_coarse_sharp", pytes.SharpFrontModel, COARSE_MESH, 0.0),
    ("mush_coarse", pytes.MushModel, COARSE_MESH, None),
    ("sharp_front_default", pytes.SharpFrontModel, None, None),
    ("mush_default", pytes.MushModel, None, None),
]
T = np.linspace(0, 3600, 121)
VARIABLES = [
    "Outlet temperature [K]",
    "Power [W]",
    "Discharged energy [J]",
    "Total thermal energy [J]",
    "Average liquid fraction",
]

#: The experiment: a rest, a power held by the inlet temperature, then by the flow rate
MDOT = 0.02  # [kg.s-1], the default
T_COLD = 273.15 + 10
EXPERIMENT_STEPS = [
    s.ConstantInputs(T_COLD, MDOT, duration=60, period=10),
    s.ConstantPower(900, inlet_temperature=T_COLD, duration=300, period=10),
    s.ConstantPower(1200, mass_flow_rate=MDOT, duration=300, period=10),
]
EXPERIMENT_VARIABLES = [
    "Outlet temperature [K]",
    "Inlet temperature [K]",
    "Power [W]",
    "Mass flow rate [kg.s-1]",
]


def solve_case(model_class, mesh, smoothing_width, t):
    """The default discharge of a finned-tube model, as the reference tests solve it"""
    model = model_class()
    parameter_values = model.default_parameter_values
    if smoothing_width is not None:
        parameter_values["PCM smoothing width [K]"] = smoothing_width
    simulation = pybamm.Simulation(
        model,
        parameter_values=parameter_values,
        var_pts=var_pts(model, mesh) if mesh else None,
    )
    return simulation.solve([0, t[-1]], t_interp=t)


def run_reference_experiment():
    model = pytes.SharpFrontModel()
    return run_experiment(
        model, Experiment(EXPERIMENT_STEPS), var_pts={model.y: 4, model.z: 5}
    )


def main():
    data = {}
    for key, model_class, mesh, smoothing_width in CASES:
        print(f"Solving {key}", flush=True)
        solution = solve_case(model_class, mesh, smoothing_width, T)
        data[f"{key}/t"] = T
        for name in VARIABLES:
            data[f"{key}/{name}"] = solution[name].entries
    print("Running the experiment", flush=True)
    solution = run_reference_experiment()
    data["experiment/t"] = solution.t
    for name in EXPERIMENT_VARIABLES:
        data[f"experiment/{name}"] = solution[name].entries
    data["pytes version"] = np.array(pytes.__version__)
    data["pybamm version"] = np.array(pybamm.__version__)
    np.savez_compressed(PATH, **data)
    print(f"Written {PATH}")


if __name__ == "__main__":
    main()
