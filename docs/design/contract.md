# PyTES model contract (draft, Stage A)

Status: **draft**. Nothing here is stable before the end of Stage B (DESIGN §5). The
executable form is `src/pytes/conformance.py`, run over every model by
`tests/conformance/`. **Where this page and the tests disagree, the tests win.**

## 1. What a model is

- A `pytes.BaseModel` subclass (itself a `pybamm.BaseModel`). PyBaMM tools apply directly:
  `pybamm.Simulation`, solvers, `QuickPlot`, PyBOP.
- A **fixed composition** of submodels in `model.submodels` (an ordered dict). Users call
  models; they do not assemble submodels.
- It belongs to a family (today: `finned_pipe`) and passes the conformance suite.

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
| Fluid | State: fluid temperature on domain `"pipe"`, coordinate `z`. Requires `"Heat transfer fluid heat gain per unit length [W.m-1]"` (per flow path) and the initial temperature. Provides the inlet/outlet temperatures and specific enthalpies, the mass flow rate and its thermal energy. Its spatial method on `"pipe"` is `compat.fluid_spatial_method()`. | `AdvectedFluid` |
| Storage | Enthalpy method, state list `[H, *material.internal_states]`. Geometry switch = coordinate system of its primary domain. Sets zero flux on its outer side and, on its inner side, applies `"<label> boundary heat flux [W.m-2]"` (into the storage) or `"<label> boundary temperature [K]"`. Provides its enthalpy, `dH/dt`, temperature, surface temperature, liquid fraction and thermal energy. | `EnthalpyStorage`; `SensibleConduction` (fins, also a volumetric `"<label> heat source [W.m-3]"`) |
| Coupling | Given fluid and storage surface state: provides the heat gain per unit length and the storage's boundary heat flux or temperature. Heat taken from the receiving side's discrete balance where possible (ledger, D6). HTC from the fluid-property object. | `LedgerWallCoupling`, `FinRootCoupling`, `FinPCMCoupling` |
| Device energy | Power, energies, SOC, capacity, initial state. | `DeviceEnergy` |

## 3. Variables (DESIGN D12)

**Required** (`pytes.variables.REQUIRED_VARIABLES`):

| Name | Notes |
|---|---|
| `Time [s]` | also `[min]`, `[h]` |
| `Mass flow rate [kg.s-1]` | whole device; a control |
| `Inlet temperature [K]`, `Outlet temperature [K]` | outlet = value advected out of the last cell |
| `Inlet specific enthalpy [J.kg-1]`, `Outlet specific enthalpy [J.kg-1]` | zero at the lower temperature limit |
| `Power [W]` | `mdot (h_out - h_in)`, positive on discharge |
| `Discharged energy [J]` | time integral of power (a solver state) |
| `Storage thermal energy [J]` | storage only (PCM, fins) |
| `Total thermal energy [J]` | storage + fluid inventory |
| `Heat loss power [W]` | positive for loss; zero today |
| `State of charge` | `Total thermal energy / Thermal capacity` |
| `Heat transfer fluid temperature [K]` | along `z` |

**Optional, standard names:** `Average liquid fraction` (weighted by the PCM volume, fins
and fluid excluded), `Mean storage temperature [K]`, `Pressure drop [Pa]`,
`Storage state of charge`.

**Also provided by every current model:** `Power [kW]`, `Discharged energy [kWh]`,
`Thermal capacity [J]`, `Initial uniform temperature [K]`, `Initial uniform liquid
fraction`, `Heat transfer fluid thermal energy [J]`.

**Family-specific:** prefixed (`Fin temperature [K]`). `Phase-change material ...` names are
the PCM storage's own (for the sharp-front model, the composite).

**Units:** temperatures in K only; every `[K]` variable gets a `[degC]` twin from
`pytes.variables.add_temperature_variables`. Temperature differences get K-only names
(DESIGN D12). None exists yet; open: how to name them so that `check_required_variables`
does not demand a twin (e.g. a `[K difference]` unit tag).

**Conservation identity** (`check_energy_conservation`, round-off tolerance):
`Total thermal energy(t) - Total thermal energy(0) = -Discharged energy(t) - int(Heat loss power) dt`.

## 4. Parameters

**Device level** (`pytes.parameters.DeviceParameters`):

| Name | Role |
|---|---|
| `Lower temperature limit [K]`, `Upper temperature limit [K]` | window: capacity, SOC 0 and 1, energy zero |
| `Initial state of charge` | initial state = the uniform state with this SOC (`initial_state="state of charge"`, default) |
| `Initial temperature [K]` | initial state = uniform at this temperature, solid at `T_m` (`initial_state="temperature"`) |
| `Inlet temperature [K]` | function of `Time [s]`; control |
| `Mass flow rate [kg.s-1]` | whole device; control |
| `Cut-off temperature [K]` | `operating_mode` event only |

**Materials:** `<prefix> ...` names, prefix `PCM` (phase change) or `Metal` (sensible):
`PCM solid phase conductivity [W.m-1.K-1]`, `PCM latent heat [J.kg-1]`, `PCM melting
temperature [K]`, `PCM melting range [K]`, `Metal density [kg.m-3]`, etc.

**Fluid:** `Heat transfer fluid density [kg.m-3]`, `... specific heat capacity
[J.kg-1.K-1]`, `... conductivity [W.m-1.K-1]` (unused; kept for axial diffusion),
`... viscosity [Pa.s]` (declared, unused), `Heat transfer coefficient [W.m-2.K-1]`.

**Family geometry:** unprefixed for now (`Pipe radius [m]`, `Number of pipes`, ...).
Namespacing is open (DESIGN §4).

`pytes.parameters.validate_parameter_values` checks `T_high > T_low` and that the melting
range lies inside the window.

## 5. Energy reference, capacity, SOC, initial state (DESIGN D13, D14)

- Every energy is zero at the uniform state at `T_low`. The fluid's enthalpy is zero there;
  storage energies subtract the material's equilibrium enthalpy at `T_low`.
- Uniform states are parametrised by `(T, phi)`: solid below `T_m`, liquid above, any
  liquid fraction at `T_m`. Each heat-holding submodel implements `uniform_energy(T, phi)`.
- Capacity: `uniform energy(T_high, 1)`, symbolic; never entered by hand.
- Initial state, chosen by the model argument `initial_state`. `"state of charge"`
  (default): invert the piecewise-linear `uniform energy` at `SOC * capacity`.
  `"temperature"`: `(T_init, phi)` with `phi = 1` if `T_init > T_m`, else 0. Either way each
  submodel starts at the resulting `(T, phi)`, exposed as `Initial uniform temperature [K]`
  and `Initial uniform liquid fraction`.
- Checked: SOC is exactly 0, 1 and an intermediate value at `t = 0` for those initial SOCs.
  By temperature: `T_low` and `T_high` give SOC exactly 0 and 1, and a sensible temperature
  inside the window gives the same state as its SOC (`check_initial_temperature`).

## 6. Materials (DESIGN D7)

A material exposes `internal_states` (empty today), `H2T(H, states)`, `T2H(T)`,
`equilibrium_enthalpy(T, phi)`, `k(H, states)`, `liquid_fraction(H, states)`, `H_scale` and
`H_reference`. Enthalpy is per unit volume, relative to 0 K internally. The check "T depends
on H alone" (`check_stateless_materials`) applies only when `internal_states` is empty.

## 7. Fluid-property object (DESIGN D8)

`h(T, p)`, `T(h, p)`, `c_p(T, p)`, `rho(T, p)`, `k(T, p)`, `mu(T, p)`,
`heat_transfer_coefficient(T, mass_flow_rate, geometry)`. Only `ConstantPropertyLiquid`
exists; its enthalpy reference is `T_low`.

## 8. Controls and experiments (DESIGN D9, D10)

`model.controls` maps control names to parameter symbols: `Inlet temperature [K]`,
`Mass flow rate [kg.s-1]`. Each step declares `controls`; the runner rejects a step that
does not drive exactly the model's controls. Power equations in steps use
`model.power(variables, replaced_controls)`, so they stay `mdot (h_out - h_in)`.

## 9. Conformance checks

`check_required_variables`, `check_submodels`, `check_controls`,
`check_stateless_materials`, `check_celsius_twins`, `check_energy_conservation`,
`check_power_from_enthalpy`, `check_soc_end_points`, `check_operating_modes`.
Parametrisation: `tests/conftest.py::MODELS` lists every admitted model.
