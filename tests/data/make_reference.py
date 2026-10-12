"""Reference outputs of heat_batteries @ d391da0, for the Stage A comparison."""

import sys
import time

import heat_batteries as hb
import numpy as np
import pybamm
from heat_batteries import step as s

out = {}
VARS = [
    "Outlet temperature [K]",
    "Power [W]",
    "Released energy [J]",
    "Thermal energy [J]",
    "Average liquid fraction",
]


def mesh(model, pts):
    return {getattr(model, k): n for k, n in pts.items() if hasattr(model, k)}


def plain(key, cls, pts, dT_m, t_end):
    m = cls(operating_mode=None)
    pv = m.default_parameter_values
    pv["PCM melting range [K]"] = dT_m
    t = np.linspace(0, t_end, 121)
    tic = time.time()
    sol = pybamm.Simulation(
        m, parameter_values=pv, var_pts=mesh(m, pts) if pts else None
    ).solve([0, t_end], t_interp=t)
    print(key, f"{time.time() - tic:.1f}s", file=sys.stderr)
    out[f"{key}/t"] = sol.t
    for v in VARS:
        out[f"{key}/{v}"] = sol[v].entries
    out[f"{key}/Heat transfer fluid temperature [K]"] = sol[
        "Heat transfer fluid temperature [K]"
    ].entries[:, -1]


COARSE = {"x": 5, "y": 6, "z": 10}
plain("sharp_front_default", hb.HBSharpFrontModel, None, 0.5, 7200)
plain("sharp_front_coarse_sharp", hb.HBSharpFrontModel, COARSE, 0.0, 3600)
plain("mush_coarse", hb.HBMushModel, COARSE, 0.5, 3600)
plain("mush_default", hb.HBMushModel, None, 0.5, 3600)

Q0, T_COLD = 20 / 6e4 / 14, 273.15 + 10
m = hb.HBSharpFrontModel(operating_mode=None)
steps = [
    s.ConstantInputs(T_COLD, Q0, duration=60, period=10),
    s.ConstantPowerFlowRate(15e3, T_COLD, duration=300, period=10),
    s.ConstantPowerInletTemperature(20e3, Q0, duration=300, period=10),
]
sol = hb.run_experiment(m, hb.Experiment(steps), var_pts=mesh(m, {"y": 4, "z": 5}))
out["experiment/t"] = sol.t
for v in VARS + ["Inlet temperature [K]", "Inlet flow rate [m3.s-1]"]:
    out[f"experiment/{v}"] = sol[v].entries
np.savez_compressed(sys.argv[1], **out)
print("saved", len(out), "arrays", file=sys.stderr)
