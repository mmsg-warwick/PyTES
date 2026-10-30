# PyTES

PyTES (Python Thermal Energy Storage) is a library of models and tools for thermal energy
storage (also known as heat batteries), built on [PyBaMM](https://pybamm.org). What PyBaMM
is to electrochemical batteries, PyTES aims to be to thermal energy storage: a set of
validated models that share one interface, so that designs compare like for like.

PyTES covers storage in which a heat transfer fluid flows through or around a separate
storage medium, such as a phase-change material (PCM) or a sensible solid. Every model is an
ordinary PyBaMM model, so PyBaMM's simulations, solvers and plots work on it directly.

```{note}
**Alpha.** The model contract may still change; every change is logged in the
[findings](design/findings.md).
```

- [**Getting started**](getting_started.md): install PyTES and run a first model.
- [**Examples**](examples/index.md): getting started tutorials, and notebooks for each
  capability.
- [**Models**](models/index.md): the model families, their geometry and their equations.
- [**Plot colours**](plot_colours.md): the PyTES colour cycles and colourmaps, and why.
- [**API reference**](api/index.rst): models, submodels, experiments and the toolkit.
- [**Design**](design/index.md): the decisions behind PyTES and the model contract.

```{toctree}
:hidden:
:maxdepth: 2

getting_started
examples/index
models/index
plot_colours
api/index
design/index
contributing
changelog
```
