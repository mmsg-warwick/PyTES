# PyTES model contract (draft, Stage A)

Status: **draft**. Nothing here is stable before the end of Stage B (DESIGN §5). The
executable form is `src/pytes/conformance.py`, run over every model by
`tests/conformance/`. **Where this page and the tests disagree, the tests win.**

## 1. What a model is

- A `pytes.BaseModel` subclass (itself a `pybamm.BaseModel`). PyBaMM tools apply directly:
  `pybamm.Simulation`, solvers, `QuickPlot`, PyBOP.
- A **fixed composition** of submodels in `model.submodels` (an ordered dict), shown by
  `model.print_submodel_info()`. Users call models; advanced users may build their own from
  submodels with `pytes.ComposedModel` (same wiring checks; not admitted, DESIGN D1).
- It belongs to a family (today: `finned_tube` and `packed_bed`) and passes the conformance suite.

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
| `assumptions` | One sentence each, for model cards (rendering deferred) |

The model merges the submodels with `pybamm.BaseModel.update` and checks the wiring
(`WiringError` otherwise): each required name is provided by exactly one submodel; no
variable depends on itself through coupled variables; after resolution, each provided
variable is on the primary domain its coupled variable declares; no two submodels set
equations or conditions for the same variable. It then resolves every coupled variable
(`pytes.compat.resolve_coupled_variables`), so the finished model contains none and works
with a default `pybamm.Simulation`. Parameters are not yet listed per submodel (open).

### Slots (DESIGN D5)

| Slot | Contract | Current submodels |
|---|---|---|
| Fluid | State: fluid specific enthalpy `"Heat transfer fluid specific enthalpy [J.kg-1]"` on domain `"flow path"`, coordinate `z`; its temperature is `T(h)` from the fluid-property object. Requires `"Heat transfer fluid heat gain per unit length [W.m-1]"` (per flow path) and the initial temperature. Provides the fluid enthalpy and temperature, the inlet/outlet temperatures and specific enthalpies (outlet temperature `T(h_out)`), the mass flow rate and its thermal energy. Its spatial method on `"flow path"` is `compat.fluid_spatial_method()`. | `AdvectedFluid` |
| Storage | Enthalpy method, one submodel for every medium (phase-change or sensible, D5); state list `[H, *material.internal_states]`. Geometry switch = coordinate system of its primary domain. Sets zero flux on its outer side and, on its inner side, applies `"<label> boundary heat flux [W.m-2]"` (into the storage) or `"<label> boundary temperature [K]"`; optionally a volumetric `"<label> heat source [W.m-3]"`. Provides its enthalpy, `dH/dt`, its conduction heating rate `div(k grad T)` (`"<label> conduction heating rate [W.m-3]"`), temperature, surface temperature and thermal energy; and, for a phase-change material only, the liquid fraction. | `EnthalpyStorage` (PCM, composite, fin metal, PCM capsule) |
| Coupling | Joins fluid to storage or storage to storage. Given the states on both sides: provides the heat gain per unit length (fluid side) and the storage's boundary heat flux or temperature, or a heat source. Every coupling is a ledger (D6): the heat crossing the interface is minus the integral of a storage side's conduction heating rate. The heat flux across a fluid-storage surface comes from a replaceable surface flux law (`SurfaceFluxLaw.heat_flux(fluid, h_f, T_f, T_s)`, positive into the storage); default `NewtonCooling`, `"Heat transfer coefficient [W.m-2.K-1]"` times `T_f - T_s`. | `LedgerWallCoupling`, `FinRootCoupling` (a `LedgerWallCoupling` with flux factor `d_m / d_c`), `FinPCMCoupling` |
| Device energy | Power, energies, initial state. | `DeviceEnergy` |

## 3. Variables (DESIGN D12)

**Required** (`pytes.variables.REQUIRED_VARIABLES`):

| Name | Notes |
|---|---|
| `Time [s]` | also `[min]`, `[h]` |
| `Mass flow rate [kg.s-1]` | whole device; a control |
| `Inlet temperature [K]`, `Outlet temperature [K]` | outlet = value advected out of the last cell |
| `Inlet specific enthalpy [J.kg-1]`, `Outlet specific enthalpy [J.kg-1]` | zero at the reference temperature |
| `Power [W]` | `mdot (h_out - h_in)`, positive on discharge |
| `Discharged energy [J]` | time integral of power (a solver state) |
| `Storage thermal energy [J]` | storage only (PCM, fins) |
| `Total thermal energy [J]` | storage + fluid inventory |
| `Heat loss power [W]` | positive for loss; zero today |
| `Heat transfer fluid specific enthalpy [J.kg-1]` | along `z`; the fluid state |
| `Heat transfer fluid temperature [K]` | along `z`; `T(h)` |

**Optional, standard names:** `Average liquid fraction` (weighted by the PCM volume, fins
and fluid excluded), `Mean storage temperature [K]`, `Pressure drop [Pa]`.

**No state of charge** (DESIGN D13): models provide energies only. The energy between two
uniform states is `pytes.energy_between(model, T_a, T_b)` (§5).

**Also provided by every current model:** `Power [kW]`, `Discharged energy [kWh]`,
`Initial uniform temperature [K]`, `Heat transfer fluid thermal energy [J]`.

**Family-specific:** prefixed (`Fin temperature [K]`). The packed bed adds the device totals
per unit bed cross-section (`Power per unit area [W.m-2]`, `Discharged energy per unit area
[J.m-2]`, `Storage thermal energy per unit area [J.m-2]`, `Total thermal energy per unit
area [J.m-2]`) from the `PerAreaTotals` submodel. `Phase-change material ...` names are
the PCM storage's own (for the sharp-front model, the composite).

**Units:** temperatures in K only; every `[K]` variable gets a `[degC]` twin from
`pytes.variables.add_temperature_variables`. Temperature differences are K-only (DESIGN
D12): their names contain "temperature difference" (e.g. `Inlet-outlet temperature
difference [K]`), they are added with `add_temperature_difference_variables` (which
`add_temperature_variables` refuses to stand in for), and `check_required_variables` fails
if one has a `[degC]` twin. No current model provides one.

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
[J.kg-1.K-1]`, `... conductivity [W.m-1.K-1]` (unused; kept for axial diffusion),
`... viscosity [Pa.s]` (declared, unused).

**Surface flux law:** `Heat transfer coefficient [W.m-2.K-1]` (`NewtonCooling`, the
default).

**Family geometry:** unprefixed for now (`Tube radius [m]`, `Number of tubes`, ...).
Namespacing is open (DESIGN §4).

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
Step types: `ConstantInputs(inlet_temperature, mass_flow_rate)` holds both controls;
`ConstantPower(power, inlet_temperature=... | mass_flow_rate=...)` holds the one given and
adjusts the other (`step.adjusted`), raising unless exactly one is given.

## 9. Conformance checks

`check_required_variables`, `check_submodels`, `check_controls`,
`check_stateless_materials`, `check_celsius_twins`, `check_energy_conservation`,
`check_power_from_enthalpy`, `check_initial_state`; and the models have no events.
Parametrisation: `tests/conftest.py::MODELS` lists every admitted model.
