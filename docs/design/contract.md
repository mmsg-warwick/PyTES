# PyTES model contract (Stage B)

Status: **Stage B** (closed 2026-10-16). Changes from here on are logged in `findings.md`;
the contract is frozen at v1.0 (Stage E, DESIGN §5). The executable form is
`src/pytes/conformance.py`, run over every model by `tests/conformance/`. **Where this page
and the tests disagree, the tests win.**

## 1. What a model is

- A `pytes.BaseModel` subclass (itself a `pybamm.BaseModel`). PyBaMM tools apply directly:
  `pybamm.Simulation`, solvers, `QuickPlot`, PyBOP.
- A **fixed composition** of submodels in `model.submodels` (an ordered dict), shown by
  `model.print_submodel_info()`. Users call models; advanced users may build their own from
  submodels with `pytes.ComposedModel` (same wiring checks; not admitted, DESIGN D1).
- It belongs to a family (today: `finned_tube` and `packed_bed`) and passes the conformance
  suite, with every combination of its options (`allowed_options`; today `"storage along
  flow path": "resolved" | "averaged"` in every model; `"heat transfer coefficient":
  "constant" | "Gnielinski"` in the finned tube, `"constant" | "Wakao-Kaguei"` in the
  packed bed, plus any correlation registered for the model's flow with
  `register_correlation`; and in the packed bed `"storage element": "resolved" | "lumped"
  | "lumped with Jeffreson"`). Unknown options or values raise `pytes.OptionError`.

## 2. Submodels

A submodel is a small `pybamm.BaseModel` (`pytes.submodels.BaseSubModel`). PyBaMM's own
`BaseSubModel` is not used: it assumes battery domains and options. In `build()` a submodel
sets its own `variables`, `rhs`, `algebraic`, `boundary_conditions`, `initial_conditions`
and `events`, and reads any variable set by another submodel as a
`pybamm.CoupledVariable` (through `self.coupled(name, domain)`), never by reaching into
that submodel. A storage submodel sets all its own boundary conditions; couplings provide
the value it applies (a heat flux into it, or a temperature).

Metadata, on every submodel, read from the code rather than declared separately:

| Attribute | Meaning |
|---|---|
| `requires` | Names of its coupled variables (PyBaMM's `coupled_variables`) |
| `provides` | Names of its `variables` |
| `parameters` | Names of the parameters in its equations, conditions, variables and state scales |
| `assumptions` | One sentence each, declared, for model cards (rendering deferred) |

On the model: `geometry_parameters`, the parameters of its default geometry (domain
lengths), and `print_submodel_info()`, which shows all of the above. Every parameter of a
model's default set belongs to a submodel or to the geometry, except declared hooks
(tested).

The model merges the submodels with `pybamm.BaseModel.update` and checks the wiring
(`WiringError` otherwise): each required name is provided by exactly one submodel; no
variable depends on itself through coupled variables; after resolution, each provided
variable is on the primary domain its coupled variable declares; no two submodels set
equations or conditions for the same variable. It then resolves every coupled variable
(`pytes.compat.resolve_coupled_variables`), so the finished model contains none and works
with a default `pybamm.Simulation`.

### Domains (DESIGN D12)

- `"flow path"`, coordinate `z`: along the flow, from the inlet; every family.
- `"storage depth"`, coordinate `y`: distance into the storage from the heat-exchange wall,
  **not along the flow** (finned tube; cylindrical around a tube).
- `"fin gap"`, coordinate `x`: across the gap between two resolved fins (mush model).
- `"capsule"`, coordinate `r`: from a capsule's centre (packed bed; spherical).

A storage resolved along the flow path has `"flow path"` as its last secondary domain; an
averaged one (`"storage along flow path": "averaged"`) does not. A lumped storage element
(`"storage element": "lumped"` or `"lumped with Jeffreson"`, packed bed) has no domain of its own: its variables are on
`"flow path"`, or on none when it is also averaged.

### Slots (DESIGN D5)

| Slot | Contract | Current submodels |
|---|---|---|
| Fluid | State: fluid specific enthalpy `"Heat transfer fluid specific enthalpy [J.kg-1]"` on domain `"flow path"`, coordinate `z`; its temperature is `T(h)` from the fluid-property object. Requires `"Heat transfer fluid heat gain per unit length [W.m-1]"` (per flow path) and the initial temperature. Provides the fluid enthalpy and temperature, the inlet/outlet temperatures and specific enthalpies (outlet temperature `T(h_out)`), the mass flow rate and its thermal energy. Its spatial method on `"flow path"` is `compat.fluid_spatial_method()`. | `AdvectedFluid` |
| Storage | Enthalpy method, one submodel for every medium (phase-change or sensible, D5); state list `[H, *material.internal_states]`. Geometry switch = coordinate system of its primary domain. Sets zero flux on its outer side and, on its inner side, applies `"<label> boundary heat flux [W.m-2]"` (into the storage) or `"<label> boundary temperature [K]"`; optionally a volumetric `"<label> heat source [W.m-3]"`. Provides its enthalpy, `dH/dt`, its conduction heating rate `div(k grad T)` (`"<label> conduction heating rate [W.m-3]"`), temperature, surface temperature and thermal energy, its conductivity `"<label> thermal conductivity [W.m-1.K-1]"`; and, for a phase-change material only, the liquid fraction. A lumped storage (issue #5) has one enthalpy per storage element, `dH/dt = (S / V) q` with `q` the boundary heat flux and `S / V` the element's surface over its volume, and provides the same variables, its conduction heating rate being `(S / V) q` and its surface temperature its temperature. | `EnthalpyStorage` (PCM, composite, fin metal, PCM capsule), `LumpedStorage` (lumped PCM capsule) |
| Coupling | Joins fluid to storage or storage to storage. Given the states on both sides: provides the heat gain per unit length (fluid side) and the storage's boundary heat flux or temperature, or a heat source. Every coupling is a ledger (D6): the heat crossing the interface is minus the integral of a storage side's conduction heating rate. The heat flux across a fluid-storage surface comes from a replaceable surface flux law (`SurfaceFluxLaw.heat_flux(fluid, fluid_state, T_s)`, `fluid_state` a `FluidState` with `h`, `T`, `mass_flow_rate` (device), `p` (reserved), positive into the storage); default `NewtonCooling`, `"Heat transfer coefficient [W.m-2.K-1]"` times `fluid_state.T - T_s`; a law's geometry goes to its constructor. Flow-dependent laws are `NusseltCorrelation`s (`Gnielinski`, `WakaoKaguei`, F-049), with no parameters of their own. The coupling also provides the law's own variables, `SurfaceFluxLaw.variables(fluid, fluid_state)` (none by default), and requires those the law reads, `SurfaceFluxLaw.coupled_variables` (none by default; F-051). `Jeffreson` corrects a Newton law for the conduction inside a lumped sphere, reading the storage's conductivity. | `WallCoupling`, `FinRootCoupling` (a `WallCoupling` with flux factor `d_m / d_c`), `FinStorageCoupling` (a storage between fins, phase change or not); formerly `LedgerWallCoupling` and `FinPCMCoupling`, which warn until 0.2.0 (F-054) |
| Device energy | Power, energies, initial state. | `DeviceEnergy` |

## 3. Variables (DESIGN D12)

**Required** (`pytes.variables.REQUIRED_VARIABLES`):

| Name | Notes |
|---|---|
| `Time [s]` | twins `[min]`, `[h]` generated |
| `Mass flow rate [kg.s-1]` | whole device; a control |
| `Inlet temperature [K]`, `Outlet temperature [K]` | outlet = value advected out of the last cell |
| `Inlet specific enthalpy [J.kg-1]`, `Outlet specific enthalpy [J.kg-1]` | zero at the reference temperature |
| `Power [W]` | `mdot (h_out - h_in)`, positive on discharge |
| `Discharged energy [J]` | time integral of power (a solver state) |
| `Charged energy [J]` | `-Discharged energy`, the net energy put in (F-055) |
| `Discharged throughput [J]`, `Charged throughput [J]` | time integrals of `max(P, 0)` and `max(-P, 0)` (solver states); they only grow, and their difference is the discharged energy (F-055) |
| `Storage thermal energy [J]` | storage only (PCM, fins) |
| `Heat transfer fluid thermal energy [J]` | fluid inventory |
| `Total thermal energy [J]` | storage + fluid inventory |
| `Heat loss power [W]` | positive for loss; zero today |
| `Heat transfer fluid specific enthalpy [J.kg-1]` | along `z`; the fluid state |
| `Heat transfer fluid temperature [K]` | along `z`; `T(h)` |
| `Heat transfer fluid velocity [m.s-1]` | along `z`; mean velocity in the flow area, `mdot_path / (A_flow rho(h))` (interstitial in a packed bed) (F-055) |
| `Inlet-outlet temperature difference [K]` | `T_in - T_out`; no twin (F-055) |
| `Volume flow rate [m3.s-1]` | whole device, at the inlet density, `mdot / rho(h_in)`; twin `[l.min-1]` (F-055) |
| `Pumped volume [m3]` | time integral of the volume flow rate (a solver state); twin `[l]` (F-055) |

**Optional, standard names:** `Average liquid fraction` (weighted by the PCM volume, fins
and fluid excluded).

**Reserved** (no model computes it yet; the first ones must use this name): `Pressure drop
[Pa]`.

**No state of charge** (DESIGN D13): models provide energies only. The energy between two
uniform states is `pytes.energy_between(model, T_a, T_b)` (§5).

**Also provided by every current model:** `Initial uniform temperature [K]`; `Heat
transfer coefficient [W.m-2.K-1]` (from the coupling's flux law: the parameter, or the
correlation's value), `Surface Reynolds number` and `Surface Prandtl number` (from the
family's flow geometry, with any coefficient; F-055), plus `Surface Nusselt number` with a
correlation (F-049), and `Effective heat transfer coefficient [W.m-2.K-1]` and `Surface
Biot number` with Jeffreson's correction (F-051). Every storage provides `<label> average
temperature [K]`, its volume-weighted average temperature (F-055), e.g. `Phase-change
material average temperature [K]` and, in the mush model, `Fin average temperature [K]`.

**Family-specific:** prefixed (`Fin temperature [K]`). The packed bed adds the device totals
per unit bed cross-section (`Power per unit area [W.m-2]`, `Discharged energy per unit area
[J.m-2]`, `Storage thermal energy per unit area [J.m-2]`, `Total thermal energy per unit
area [J.m-2]`) from the `PerAreaTotals` submodel. `Phase-change material ...` names are
the PCM storage's own (for the sharp-front model, the composite).

**Units** (DESIGN D12): submodels define every variable in SI units. When a model is built,
`pytes.variables.add_unit_twins` adds twins for every variable in `[K]` (`[degC]`), `[W]`
(`[kW]`), `[J]` (`[kWh]`), `[s]` (`[min]`, `[h]`), `[m3.s-1]` (`[l.min-1]`) and `[m3]`
(`[l]`); a twin written by hand is rejected. Temperature differences
(names containing "temperature difference") get no twin. `check_required_variables` checks
that every such variable has its twin and no difference has one; `check_unit_twins`
checks the values, to round-off (relative 1e-10).

**Conservation identity** (`check_energy_conservation`, round-off tolerance):
`Total thermal energy(t) - Total thermal energy(0) = -Discharged energy(t) - int(Heat loss power) dt`.

## 4. Parameters

**Device level** (`pytes.parameters.DeviceParameters`):

| Name | Role |
|---|---|
| `Reference temperature [K]` | every energy is zero at the uniform state at this temperature |
| `Initial temperature [K]` | initial state = uniform at this temperature, solid at `T_m` |
| `Inlet temperature [K]` | function of `Time [s]`; control |
| `Mass flow rate [kg.s-1]` | whole device; control |

**Materials:** `<prefix> ...` names, prefix `PCM` (phase change) or `Metal` (sensible):
`PCM solid phase conductivity [W.m-1.K-1]`, `PCM latent heat [J.kg-1]`, `PCM melting
temperature [K]` (the middle of the melting range), `PCM melting range [K]` (solidus to
liquidus, physical; 0 for a sharp melting point), `PCM smoothing width [K]` (numerical
rounding of the corners; 0 for exact corners), `Metal density [kg.m-3]`, etc.

**Fluid:** `Heat transfer fluid density [kg.m-3]`, `... specific heat capacity
[J.kg-1.K-1]`, `... conductivity [W.m-1.K-1]` and `... viscosity [Pa.s]` (all required in a
fluid layer; the last two are used only by the correlations).

**Surface flux law:** `Heat transfer coefficient [W.m-2.K-1]` (`NewtonCooling`, the
default). The correlations add no parameter (F-049).

**Family geometry** (DESIGN D1): names start with the geometric object, never a material
prefix. Finned tube: `Tube radius [m]`, `Tube length [m]`, `Number of tubes`, `Storage
depth [m]`, `Fin thickness [m]`, `Fin pitch [m]`. Packed bed: `Bed length [m]`, `Bed
cross-sectional area [m2]`, `Bed porosity`, `Capsule radius [m]`.

`pytes.parameters.validate_parameter_values` checks that the reference and initial
temperatures are positive and the parameters it is given (e.g. the melting range and the
smoothing width) are not negative.

## 5. Energy reference and initial state (DESIGN D13, D14)

- Every energy is zero at the uniform equilibrium state at `T_ref`. The fluid's enthalpy is
  zero there; storage energies subtract the material's `T2H(T_ref)`.
- A uniform state is set by its temperature alone: each material is at `T2H(T)` (for a
  sharp melting point, solid at `T_m`; with a melting range, partly liquid inside it). Each
  heat-holding submodel implements `uniform_energy(T)`; `DeviceEnergy.uniform_energy(T)`
  sums them.
- Initial state: uniform at `T_init`, exposed as `Initial uniform temperature [K]`. Other
  starts use `model.set_initial_conditions_from(solution)`.
- `pytes.energy_between(model, T_a, T_b, parameter_values=None, var_pts=None)`: the total
  thermal energy between the uniform states at `T_a` and `T_b`, discretised on the model's
  mesh, so it matches the model's `Total thermal energy [J]` exactly.
- The models have no events; cut-offs are experiment terminations (DESIGN D11).
- Checked (`check_initial_state`): at `T_init` equal to `T_ref`, between `T_ref` and `T_m`,
  at `T_m` and above it, the initial state is uniform at `T_init` and its total thermal
  energy is `energy_between(model, T_ref, T_init)`; run with and without a melting range.

## 6. Materials (DESIGN D7)

A material exposes `internal_states` (empty today), `changes_phase`, `H2T(H, states)`,
`T2H(T)`, `k(H, states)`, `H_scale` and `H_reference`; a phase-change material also
`liquid_fraction(H, states)`, `T_solidus`, `T_liquidus`, `H_solidus` and `H_liquidus`. In
the mushy zone `H` is linear in `T`: the latent heat plus the mean of the solid and liquid
heat capacities. `H2T`, `k` and the liquid fraction are smoothed at the solidus and liquidus
over the smoothing width (floored at 1e-9 K); `T2H` is exact. Sensible materials (`SensibleMaterial`,
the fin metal) go through the same storage submodel. Enthalpy is per unit volume, relative to 0 K internally. The check "T depends
on H alone" (`check_stateless_materials`) applies only when `internal_states` is empty.

## 7. Fluid-property object (DESIGN D8)

Properties at the fluid state `(h, p)`: `T(h, p)`, `c_p(h, p)`, `rho(h, p)`, `k(h, p)`,
`mu(h, p)`; and `h(T, p)` for the inlet and initial conditions. `p` is ignored by liquids.
Only `ConstantPropertyLiquid` exists; its enthalpy reference is `T_ref`. The heat transfer
coefficient is not a fluid property: it belongs to the coupling's surface flux law (§2).

## 8. Controls and experiments (DESIGN D9, D10)

`model.controls` maps control names to parameter symbols: `Inlet temperature [K]`,
`Mass flow rate [kg.s-1]`. Each step declares `controls`; the runner rejects a step that
does not drive exactly the model's controls. Power equations in steps use
`model.power(variables, replaced_controls)`, so they stay `mdot (h_out - h_in)`.
Step types (F-054): `Inlet(inlet_temperature, mass_flow_rate)` holds both controls;
`Power(power, inlet_temperature=... | mass_flow_rate=...)` holds the one given and
adjusts the other (`step.adjusted`), raising unless exactly one is given; `Rest(
inlet_temperature=None)` holds no flow, and the inlet temperature given or, by default, its
value at the end of the previous step (the initial temperature for a first step). The old
names `ConstantInputs` and `ConstantPower` warn until 0.2.0.

## 9. Conformance checks

`check_required_variables`, `check_submodels`, `check_controls`,
`check_stateless_materials`, `check_unit_twins`, `check_energy_conservation`,
`check_power_from_enthalpy`, `check_initial_state`; and the models have no events.
Parametrisation: `tests/conftest.py::MODELS` lists every admitted model.
