# Getting started

## Installation

```bash
pip install --pre pytes-thermal            # models and toolkit
pip install --pre "pytes-thermal[plot]"    # plus the standard plots (matplotlib)
```

The package is `pytes-thermal` on PyPI and is imported as `pytes`. `--pre` is needed while
PyTES only has alpha releases. PyTES supports every Python version PyBaMM supports.

## A first simulation

A PyTES model is a PyBaMM model, so it runs in a {class}`pybamm.Simulation`:

```python
import pybamm
import pytes

model = pytes.PackedBedModel()  # or pytes.SharpFrontModel(), pytes.MushModel()
solution = pybamm.Simulation(model).solve([0, 3600])
print(solution["Outlet temperature [degC]"].entries[-1])
```

The model comes with its default parameter values, geometry, mesh and solver, as PyBaMM
models do (`model.default_parameter_values` and the other `default_*` properties). Pass
your own to `pybamm.Simulation` to change them.

## Models

| Family | Models | Storage |
|---|---|---|
| Finned tube | {class}`~pytes.SharpFrontModel`, {class}`~pytes.MushModel` | PCM around tubes with metal fins (homogenised or resolved) |
| Packed bed | {class}`~pytes.PackedBedModel` | a bed of spherical PCM capsules |

Every model takes `options={"storage along flow path": "averaged"}` for a faster variant
with one storage cross-section standing for the average along the flow, and the packed bed
takes `options={"storage element": "lumped"}` for capsules at a uniform temperature
([Lumped capsule](examples/lumped_capsule.ipynb)). Each model is a fixed composition of
submodels (a fluid, a storage and a coupling, plus the device-level energy), listed in
`model.submodels`; `model.print_submodel_info()` describes them.

## Conventions

All models share their outputs, so results compare across families:

- Every quantity is defined in SI units, and the temperatures, powers, energies and times
  also have twins in °C, kW, kWh, minutes and hours (`"Outlet temperature [degC]"` next to
  `"Outlet temperature [K]"`).
- Power is positive on discharge, and is defined from the enthalpy of the heat transfer
  fluid, $\dot m (h_\mathrm{out} - h_\mathrm{in})$.
- Energy is conserved exactly by the discretised model, a property the conformance suite
  checks for every model.

The full list of outputs and their definitions is in the [model contract](design/contract.md).

## Next steps

- Work through the [getting started tutorials](examples/getting_started/index.md): six
  short notebooks on running models, the two families, parameter values, plotting and
  experiments.
- Operate a battery through charge, rest and discharge steps with
  {func}`pytes.experiments.run_experiment` ([Running experiments](examples/experiments.ipynb)).
- Build parameter sets from layers and swap a PCM
  ([Parameter layers](examples/parameter_layers.ipynb)).
- Compare designs across families ([Design study](examples/design_study.ipynb)).
