# Changelog

All notable changes to PyTES. Versions follow [semantic versioning](https://semver.org);
until 1.0 the model contract may change, and every change to it is also logged in
[`docs/design/findings.md`](docs/design/findings.md). Entries are written as fragments in
[`changelog.d/`](changelog.d) and assembled here at each release (see
[`CONTRIBUTING.md`](CONTRIBUTING.md#changelog-entries)).

<!-- towncrier release notes start -->

## [0.1.0a3] - 2026-10-24

### Breaking changes

- The option `"storage"` is renamed `"storage along flow path"`, with the same values: write `options={"storage along flow path": "averaged"}` for the averaged storage. The old name raises an error that gives the new one. ([#15](https://github.com/mmsg-warwick/PyTES/pull/15))
- Every model's results change: the fluid is advected at second order by default, and the default meshes are coarser (sharp front 20 by 20 instead of 40 by 40, packed bed 40 by 40 instead of 40 by 80, or 40 instead of 80 for a lumped capsule), for smaller errors in less time. To keep earlier results, pass `spatial_methods={**model.default_spatial_methods, "flow path": pytes.compat.fluid_spatial_method("first order")}` and the earlier `var_pts`. ([#16](https://github.com/mmsg-warwick/PyTES/pull/16))

### Model contract changes

- Every storage provides `"<label> thermal conductivity [W.m-1.K-1]"`, a model with Jeffreson's correction also provides `"Effective heat transfer coefficient [W.m-2.K-1]"` and `"Surface Biot number"`, and a surface flux law may list the variables it reads in `coupled_variables`, which its coupling requires. ([#15](https://github.com/mmsg-warwick/PyTES/pull/15))
- The step types are `Inlet`, `Power` and `Rest`, and the couplings `WallCoupling`, `FinRootCoupling` and `FinStorageCoupling` (default submodel name "Fin-storage coupling"). ([#20](https://github.com/mmsg-warwick/PyTES/pull/20))
- Nine variables join the required set: `Volume flow rate [m3.s-1]`, `Pumped volume [m3]`, `Inlet-outlet temperature difference [K]`, `Heat transfer fluid velocity [m.s-1]`, `Charged energy [J]`, `Discharged throughput [J]`, `Charged throughput [J]`, `Storage average temperature [K]` and `Storage cross-section average temperature [K]`; every storage provides `<label> average temperature [K]` and `<label> cross-section average temperature [K]`; and `[m3.s-1]` and `[m3]` get `[l.min-1]` and `[l]` unit twins. ([#36](https://github.com/mmsg-warwick/PyTES/pull/36))

### Deprecations

- `step.ConstantInputs` and `step.ConstantPower` are renamed `step.Inlet` and `step.Power`, and the couplings `LedgerWallCoupling` and `FinPCMCoupling` are renamed `WallCoupling` and `FinStorageCoupling`. The old names still work, with a `PyTESDeprecationWarning`, until PyTES 0.2.0. ([#20](https://github.com/mmsg-warwick/PyTES/pull/20))

### New features

- A documentation site at https://pytes.readthedocs.io, built with Sphinx: an API reference generated from the docstrings, the example notebooks, a getting-started page, the design documents, the changelog and the contribution guide. Build it locally with `uv run --group docs sphinx-build docs docs/_build/html`. ([#13](https://github.com/mmsg-warwick/PyTES/pull/13))
- A lumped capsule for the packed bed (issue #5): `options={"storage element": "lumped"}` gives each capsule a uniform temperature, much faster and accurate when the capsule's Biot number is small, and `"lumped with Jeffreson"` also corrects the heat transfer coefficient for the conduction inside the capsule (new submodels `LumpedStorage` and `LumpedGeometry`, and the flux law `Jeffreson`). ([#15](https://github.com/mmsg-warwick/PyTES/pull/15))
- A second-order, limited upwind scheme for the heat transfer fluid (issue #7), on uniform or non-uniform meshes: a temperature front stays much sharper on the same mesh, and energy is still conserved exactly. It is the default; `pytes.compat.fluid_spatial_method("first order")` selects PyBaMM's first-order upwinding. ([#16](https://github.com/mmsg-warwick/PyTES/pull/16))
- Renamed names now go through one registry, `pytes.deprecation`: an old class, function or option name keeps working for at least one release with a `PyTESDeprecationWarning` that gives the new name, then raises an error that gives it. ([#19](https://github.com/mmsg-warwick/PyTES/pull/19))
- A `step.Rest` experiment step: no flow, with the inlet temperature held where the previous step left it, or at a value you give. ([#20](https://github.com/mmsg-warwick/PyTES/pull/20))
- New outputs for comparison with measurements (issue #14): `Volume flow rate [m3.s-1]` (also in l/min), `Pumped volume [m3]` (also in litres), `Inlet-outlet temperature difference [K]`, `Heat transfer fluid velocity [m.s-1]`, `Charged energy [J]`, the throughputs `Discharged throughput [J]` and `Charged throughput [J]` (for round-trip efficiencies), the storage temperatures averaged over the whole storage and over each cross-section along the flow path (`Storage average temperature [K]`, `Storage cross-section average temperature [K]`, and each storage's own), and the surface Reynolds and Prandtl numbers with any heat transfer coefficient. ([#36](https://github.com/mmsg-warwick/PyTES/pull/36))


## [0.1.0a2] - 2026-10-22

### Breaking changes

- The default parameter values of both families are now compositions of parameter layers, with values from cited sources, so default results change. The finned-tube default is an illustrative one-tube battery with 0.02 kg/s of water and PCM 60; the packed-bed "Raul2018" set has the real bed cross-section and flow rate instead of a 1 m2 placeholder; and the PCM smoothing width is 0.01 K instead of 0.5 K. To keep earlier results, set the parameters you rely on explicitly. ([#9](https://github.com/mmsg-warwick/PyTES/pull/9))
- `"Heat transfer fluid viscosity [Pa.s]"` is now a required name of a heat transfer fluid layer, as the correlations use it. Add it to any fluid layer of your own. ([#11](https://github.com/mmsg-warwick/PyTES/pull/11))

### Model contract changes

- Additions to the model contract (F-049): every model outputs `"Heat transfer coefficient [W.m-2.K-1]"`, and with a correlation also `"Surface Reynolds number"`, `"Surface Prandtl number"` and `"Surface Nusselt number"`; the option `"heat transfer coefficient"` takes `"constant"` or a registered correlation; `"Heat transfer fluid viscosity [Pa.s]"` is a required name of a heat transfer fluid layer; and surface flux laws gain the `variables` hook. ([#11](https://github.com/mmsg-warwick/PyTES/pull/11))

### New features

- New `pytes.parameter_layers`, which composes parameter sets from layers (operation, coupling, heat transfer fluid, PCM, metal, and the family geometry as a flow path and a storage element), so that one part, such as the PCM or the fins, can be swapped with `swap` without touching the rest. It ships layers with cited sources (water, Hytherm 600, aluminium, steel, copper, the Nallusamy (2007) paraffin, A164, and the representative PCM 10N, PCM 30 and PCM 60); `operation.charge` and `operation.discharge` build an operation from a PCM, and `template` gives an empty layer to fill in. See the new example notebook `examples/parameter_layers.ipynb`. ([#9](https://github.com/mmsg-warwick/PyTES/pull/9))
- Flow-dependent heat transfer coefficients: the new option `"heat transfer coefficient"` computes the coefficient from the flow with a Nusselt correlation, `"Gnielinski"` in the finned-tube models and `"Wakao-Kaguei"` in the packed bed, instead of the constant `"Heat transfer coefficient [W.m-2.K-1]"` (still the default). Every model now outputs `"Heat transfer coefficient [W.m-2.K-1]"`, and with a correlation also the surface Reynolds, Prandtl and Nusselt numbers. Correlations of your own, a function `nusselt(Re, Pr)`, become option values with `pytes.submodels.register_correlation`, and `pytes.conformance.check_model` checks a model that uses one. See the new example notebook `examples/heat_transfer_coefficient.ipynb`. ([#11](https://github.com/mmsg-warwick/PyTES/pull/11))

### Bug fixes

- PyTES now requires PyBaMM 26.9 or later. It failed with earlier releases, which lack `pybamm.tree_map`. ([#2](https://github.com/mmsg-warwick/PyTES/pull/2))


## [0.1.0a1] - 2026-10-17

### Models

- Finned-tube family (`pytes.models.finned_tube`): `SharpFrontModel` (PCM and fins
  homogenised) and `MushModel` (fins and PCM resolved), reproducing the finned-tube code
  prototype to solver tolerance.
- Packed-bed family (`pytes.models.packed_bed`): `PackedBedModel`, a bed of spherical PCM
  capsules, ported from [encapsulated-LTES](https://github.com/mmsg-warwick/encapsulated-LTES), with the Nallusamy et al. (2007) experiments as the default parameters and the
  Raul et al. (2018) set.
- Option `"storage": "averaged"` on every model: one storage cross-section standing for the
  average along the flow path.
- Exact discrete energy conservation in every model, through ledger couplings.

### Toolkit

- Submodels (fluid, enthalpy storage, couplings with replaceable surface flux laws, device
  energy) and `pytes.ComposedModel` to build models from them.
- Materials with a physical melting range and a separate smoothing width; fluid-property
  objects.
- Experiment runner: `ConstantInputs` and `ConstantPower` steps, terminations and cycles.
- `pytes.energy_between`, standard plots (`pytes.plotting`), analytical benchmarks
  (`pytes.validation`: Schumann, spherical melting) and conformance checks
  (`pytes.conformance`).
- Variables in SI units, with generated °C, kW, kWh, minute and hour twins.

### Validation

- Agreement with the original finned-tube models; Schumann's solution for a sensible bed;
  the quasi-steady melting of a sphere; the Nallusamy et al. (2007) measurements (fluid
  temperatures within about 1 K).
