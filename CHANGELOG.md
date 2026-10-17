# Changelog

All notable changes to PyTES. Versions follow [semantic versioning](https://semver.org);
until 1.0 the model contract may change, and every change to it is also logged in
[`docs/design/findings.md`](docs/design/findings.md). Entries are written as fragments in
[`changelog.d/`](changelog.d) and assembled here at each release (see
[`CONTRIBUTING.md`](CONTRIBUTING.md#changelog-entries)).

<!-- towncrier release notes start -->

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
