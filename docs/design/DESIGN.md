# PyTES design document

Status legend: **Decided** (do not reopen unless asked), **Deferred** (not built now, but the
listed hook must exist), **Open** (to be settled during the stage indicated).
Each decision carries its rationale. A decision without its reason gets "improved away".

## 1. Purpose and positioning

PyTES is a library of models and auxiliary tools for heat batteries, built on PyBaMM.
Audience: practitioners (design studies) and researchers, who both use the provided models.
Anyone needing a custom model either builds one from PyTES submodels (D3), for example to
develop a new submodel locally, or builds it with PyBaMM directly. Either way they may opt into
PyTES's materials, experiments and conformance tests, which are importable tools.

Two public layers:
- **Models (strict):** curated, admitted by passing the conformance suite and the
  maintainer's review (D1).
- **Toolkit (permissive):** materials, experiments, KPIs, plots, conformance tests.

Origin: the finned-tube code prototype (composite finned-tube family, then called finned
pipe: sharp-front and mush models) and a separate packed-bed repo,
[encapsulated-LTES](https://github.com/mmsg-warwick/encapsulated-LTES) (encapsulated family, enthalpy method, resolved radial conduction in
the capsule, constant film coefficient, temperature as fluid state). Both are by the
maintainer and are PyBaMM models with the same physics (enthalpy method, upwinded fluid),
but they share neither code nor the conservation approach: the material classes are separate
copies that differ (F-003), and only the finned tube conserves energy exactly (F-004). They
are starting points, not something to preserve as they are.

## 2. Decided

### D1. Curated catalogue with an admission standard
Rationale: cross-compatibility is the product. A model is admitted when it (a) passes the
conformance suite, (b) uses the shared parameter layering and materials library, (c) has at
least one validation case, (d) sits in a declared family, and (e) the maintainer has reviewed
it. Passing the suite is necessary, not sufficient.
- **Parameter layering:** a parameter set is composed of independent layers (operation:
  reference and initial temperatures and controls; coupling; HTF; PCM; other materials such
  as the fin metal; family geometry), so that e.g. a PCM can be swapped without touching
  the rest. The family geometry is in two layers (maintainer, 2026-10-18): the *flow path*,
  which sets the size of the device (number, radius and length of the tubes; length and
  cross-section of the bed), and the *storage element*, the repeating unit, whose names are
  all per unit length or per tube (fin thickness, fin pitch and storage depth, i.e. the fin
  height; capsule radius and porosity). So a standard fin or capsule design is chosen once
  and the device is sized around it. Operation is apart from the hardware, so that one
  device can be run under several operations (charge, discharge). The tube radius stays in
  the flow path, although a fin design fits one tube size; a compatibility check between
  the two can come later. An operation only makes sense relative to the PCM, so besides
  the registered operations of the named sets, `operation.charge` and `operation.discharge`
  build one from a PCM layer's melting range, margins and a mass flow rate, all given by the
  user; their energy reference is the colder end (the initial state of a charge, the inlet
  of a discharge). Every layer states its sources: a layer with cited values links each
  source's DOI in its docstring, and one without says that its values are illustrative, an
  estimate or representative (tested). The maintainer types in every value, to trace its
  source; `template(kind)` gives an empty layer to fill in. Each material and fluid layer has its
  own name prefix so layers merge without clashes. `pytes.parameter_layers` (issue #3)
  defines the kinds and the names each holds, and composes layers into a plain
  `pybamm.ParameterValues`; named sets list one layer per kind. The families' default
  parameter values are the named sets "Finned tube default", "Nallusamy2007" and
  "Raul2018" (maintainer, 2026-10-21, F-048): their values were checked against the
  literature and replace the earlier flat sets, and `swap` adds a new layer's sources to the
  set's `"citations"`. Docstrings cite sources as reStructuredText links to their DOI;
  bibliography roles (sphinxcontrib-bibtex, as PyBaMM uses) can follow with the
  documentation site (#4). Decided with it
  (maintainer, 2026-10-18): `"Heat transfer coefficient [W.m-2.K-1]"` is in its own
  *coupling* layer, which will hold the parameters of other surface flux laws (the
  correlations of #6 have none: F-049);
  `"PCM smoothing width [K]"` stays in the PCM layer, although it is numerical; one `Metal`
  layer per device, with a prefix argument added when a second metal appears.
- **Parameter names** (maintainer, 2026-10-16): material and fluid properties start with
  their layer's prefix (`PCM ...`, `Metal ...`, `Heat transfer fluid ...`); geometry starts
  with the geometric object (`Tube ...`, `Fin ...`, `Bed ...`, `Capsule ...`, `Storage
  ...`), never with a material prefix. Geometry names are distinct across families without
  a family prefix, and stay family-specific (D4).
- **Validation case:** an analytical benchmark (Stefan, Schumann) or a comparison with
  measurements. Experimental data is often unavailable, so an analytical case suffices.

### D2. Scope is defined by structure, not a technology list
"HTF passes through or around a separate storage medium." In scope: finned or tubed PCM
blocks (including PCM tanks with an immersed coil), encapsulated PCM beds, and sensible-only
storage such as packed beds. Out of scope: stratified tanks (the HTF is the storage medium),
thermochemical storage, system-level models (heat pump, building), and a general framework
for arbitrary physics (composing PyTES submodels through the submodel interface is in, D3). The structural rule makes these "no"s easy to justify.
- **PCM slurries** (microencapsulated or emulsified PCM suspended in the carrier fluid): as
  storage, out (no separate medium, like a stratified tank). As the HTF of an in-scope device,
  in: a slurry is a fluid-property object whose `h(T)` has a latent bump (D8). Nothing to build
  now.
- **Direct contact** (immiscible HTF bubbling through the PCM, no wall): out for now. It fits
  the three slots only through an empirical volumetric coefficient; its physics (droplet
  dynamics, channelling on solidification) is in the flow, which no slot captures. If it
  returns, it is a new family, not a variant of an existing one.

### D3. Submodel structure, visible and inspectable
Models are fixed compositions **for a given set of options**. `model.submodels` lists them.
Each submodel exposes the variables it requires and provides and the parameters it uses,
all read from its code (F-028, F-045), and declares its assumptions; the model exposes the
parameters of its geometry (domain lengths). So wiring can be checked automatically and
model cards can be generated later. Submodels are
testable in isolation.
- **Options** (PyBaMM style): a model's `options` dict selects among submodels, e.g. the
  fluid (dynamic or quasi-steady, D5) or the film coefficient. `operating_mode` and
  `initial_state` are removed (D11, D14). This is the preferred route for variants.
  *Introduced with the first real variant* (maintainer, 2026-10-14), which is
  `"storage along flow path": "resolved" | "averaged"` (D4; maintainer, 2026-10-15; named
  `"storage"` until 2026-10-22, F-050). Each model declares
  `allowed_options`, the first value of each being the default; unknown options or values
  raise `pytes.OptionError`, and `check_options` rejects incompatible combinations. Values
  are lower case unless they are names (e.g. `"heat transfer coefficient": "Gnielinski"`).
  An option is named after what it varies, not after a slot (maintainer, 2026-10-22,
  F-050): `"storage"` was also the name of a slot in `model.submodels`. A renamed option is
  an entry of the rename registry (D17), so that its old name warns or raises with the new
  one.
- **No silent swaps.** An option combination that is incompatible raises an error naming the
  conflict; a model never replaces a submodel the user did not ask for. Rationale: PyBaMM's
  options grew complicated and it swapped submodels silently to keep combinations working,
  which hid what was being solved. Every admitted combination passes the conformance suite.
- **Public composition API** (advanced users): `model.print_submodel_info()` displays the
  submodels (class, requires, provides, assumptions), and `pytes.ComposedModel(submodels,
  param, defaults_from=..., geometry=..., ...)` builds a model from submodels, from scratch
  or by replacing slots of an existing model (whose submodels are reused, not modified). It
  runs the same wiring checks as the built-in models, and raises if the geometry, submesh
  types or spatial methods miss a domain. Rationale: it lets people develop their
  own submodels locally against the real interface. A composed model is not admitted (D1)
  until it goes through the admission standard.

### D4. Two-tier compatibility
- **Within a family** (one topology, several fidelities): same parameter set, nested
  outputs, same experiments; one-to-one comparison.
  - *Parameters:* the most detailed model in the family defines the family's parameter set.
    Every lower-fidelity model runs on that set, leaving some parameters unused and deriving
    what it needs from them (e.g. the sharp-front composite properties from the fin and PCM
    properties). A reduced model that needs a parameter it cannot derive (e.g. a fitted
    effective coefficient) is a logged exception.
  - *Outputs:* a higher-fidelity model provides every variable of the simpler models in its
    family and may add more (e.g. the mush model's fin variables).
  - *Averaged storage* (maintainer, 2026-10-15): every model has the option
    `"storage along flow path": "averaged"`, in which one storage cross-section (a
    capsule, an annulus, a fin-PCM unit) stands for the average along the flow path and
    exchanges heat with the fluid averaged along it. Averaging is a fidelity choice that applies across families,
    so it is an option, not a model class per family (it replaces the planned
    `AverageCapsuleModel`, F-019). In the mush model the fin-PCM unit is averaged, with
    the fins and the PCM still separate submodels.
  - *Lumped storage element* (maintainer, 2026-10-22, issue #5, F-051): the option
    `"storage element": "resolved" | "lumped"`, separate from `"storage along flow path"`
    as it is about the variation inside one storage element, not along the flow; the two
    combine (a lumped, averaged capsule is one well-mixed capsule for the whole bed). Only
    the packed bed has it for now. A lumped storage (`LumpedStorage`, on a
    `LumpedGeometry`) has a uniform temperature in each element and provides the same
    variables as `EnthalpyStorage`, so the couplings, the device energy and the ledger
    work unchanged. The internal resistance it neglects can be put back in the flux law
    (D6): `"lumped with Jeffreson"` wraps whichever coefficient `"heat transfer
    coefficient"` gives. It is a value of `"storage element"`, not a separate option
    (maintainer, 2026-10-23): it only applies to a lumped element (with a resolved one it
    would count that resistance twice), so as a value it admits no invalid combination.
  - *Averaged coupling* (maintainer, 2026-10-15): one flux from the fluid averaged along
    the flow path, taken uniformly from the fluid, as in the maintainer's published reduced
    model. Rationale: reproduces the published model. Known artefact: early in a charge the
    fluid near the outlet can be driven outside its inlet and initial temperatures (the
    default bed's outlet dips to 27 °C from 32 °C); energy stays exact. Recorded
    alternative, if ever needed: the local flux `q(z) = h (T_f(z) - T_s)` against the
    averaged storage surface, the storage receiving its mean and the fluid the exact ledger
    total plus `-S (q(z) - mean q)`, with `S` the storage surface per unit length of flow
    path; a prototype removed the dip and kept conservation exact (F-041).
- **Across families:** same device-level interface: the contract's required outputs,
  experiments, and a small shared device description (reference and initial temperature, HTF,
  controls: mass flow rate and inlet temperature). Geometry parameters stay in
  family-specific namespaces.
  - *Per device:* the shared interface is always whole-device, in J and W, so experiments,
    power controls and measurements mean the same in every family. Families may add
    normalised twins as extra outputs (e.g. per unit bed cross-section [J.m-2], per tube),
    so the bed needs a cross-section parameter (F-002). The bed provides them with the
    `PerAreaTotals` submodel ("Power per unit area [W.m-2]" and so on).

### D5. Three slots: fluid, storage, coupling
- **Fluid** is written once. Geometry-neutral form, with `q'` the heat exchanged per unit
  length of flow path:
  `A_flow * rho * dh/dt + mdot * dh/dz = q'`.
  Porosity enters only through `A_flow`. Axial dispersion is an optional extra term (zero for
  tubes). The contract must not define the fluid slot as "an advection PDE", because a
  quasi-steady fluid (`mdot * dh/dz = q'`) is a planned option (refrigerant, high-flow water).
  - *State is the specific enthalpy* `h` (maintainer, 2026-10-14). The temperature is
    `T(h)` from the fluid-property object. It is an internal state, and enthalpy handles
    temperature-dependent properties (e.g. `c_p(T)`) and a two-phase refrigerant, where `T`
    is flat across the phase change, without a change of state variable. `h_out` is then
    the advected value itself and `T_out = T(h_out)`.
  - *Dynamic form is for incompressible liquids.* Strictly the transient term is `rho u`,
    not `rho h`, and `mdot` uniform along `z` needs constant density; both are exact for a
    liquid at constant density. Compressible or two-phase fluids use the quasi-steady form,
    where `mdot` is uniform by mass conservation. A fully dynamic two-phase fluid is out
    unless needed.
- **Storage** is the enthalpy method with one submodel and a geometry switch (annular
  fin-PCM, planar gap, sphere). It differs only by a geometric factor in the conduction term.
  A model that resolves several media (the mush model: PCM and fins) has one storage
  submodel per medium, all of this one kind; a sensible medium (fin metal, Schumann bed) is
  the same submodel with a material without latent heat (maintainer, 2026-10-14). Every
  storage state is therefore an enthalpy, like the fluid's.
- **Coupling** is where families differ. Couplings join the fluid to the storage and, where
  a model resolves several media, storage to storage (the mush model: fluid to fin root, fin to
  PCM). Contract: given the states on both sides, a coupling provides `q'` to the fluid (if
  one side is the fluid) and a boundary heat flux or temperature to each storage side
  (`"<label> boundary heat flux [W.m-2]"` or `"<label> boundary temperature [K]"`). The
  storage owns its boundary conditions and reads these (F-028). Flow-dependent HTC lives
  here, fed by the fluid-property object (D6, F-049).

### D6. Ledger-style exact energy conservation
The heat crossing an interface is one discrete quantity, counted once on each side with
opposite signs, and taken from a storage side's discrete energy balance (integral of `dH/dt`),
never from a separately discretised flux. This applies to **every** coupling, fluid-storage
and storage-storage (maintainer, 2026-10-14). Rationale: PyBaMM imposes a Neumann condition on
the gradient, so the flux the finite volumes use is `k_face / k_surface` times the one
requested, and with a temperature (Dirichlet) condition it is whatever the scheme computes;
the ledger is exact in both cases, for any conductivity. In a bed, the film resistance works
as at the finned-tube wall: the flux uses the boundary value of `T(H)`, with no extra unknown
(F-014).
- **General surface flux law.** Because the ledger makes conservation independent of how the
  boundary flux is computed, the flux law is a replaceable part of the coupling: a function
  of the states on both sides at the interface (e.g. `T_f`, `T_s`) and of properties from the
  fluid-property object and materials, positive into the storage. Newton's law of cooling,
  `h (T_f - T_s)` with `h` from the fluid-property object, is the default. Others (series
  wall or contact resistance, a nonlinear or radiative law) need no change to the
  conservation logic. Built-in laws, and Nusselt correlations registered by users, are
  chosen through `options` (D3); any other custom law is passed to the coupling through the
  composition API. Interface (maintainer, 2026-10-16):
  `heat_flux(fluid, fluid_state, T_s)`, with `fluid_state` a `FluidState` (`h`, `T`,
  `mass_flow_rate` of the whole device, `p` reserved) so that new fields never break existing
  laws; geometry a law needs (e.g. a hydraulic diameter) goes to its constructor, from the
  family.
- **Flow-dependent coefficients** (issue #6, F-049): Newton's law with `h = Nu k / L` from a
  Nusselt correlation (`NusseltCorrelation`, with `Re` from `|mdot|` per flow path and `mu`,
  `c_p`, `k` from the fluid-property object). Chosen by the option
  `"heat transfer coefficient"`, `"constant"` by default so results do not change:
  `"Gnielinski"` in the finned tube (laminar 3.66 below `Re` 2300, VDI interpolation to
  `Re` 10^4), `"Wakao-Kaguei"` in the packed bed (`Nu = 2 + 1.1 Re^0.6 Pr^(1/3)`,
  superficial velocity, capsule diameter). The correlation's constants belong to it, so it
  adds no parameter; its geometry comes from the family. The coupling provides the law's
  variables: `"Heat transfer coefficient [W.m-2.K-1]"` for every Newton law, plus
  `"Surface Reynolds number"`, `"Surface Prandtl number"` and `"Surface Nusselt number"`
  for a correlation.
- **Registered correlations** (maintainer, 2026-10-22, F-049): option values stay names
  (D3), backed by a registry of correlations per flow geometry (`CORRELATIONS`, with
  `"tube"` and `"packed bed"`). A correlation is only its `Nu(Re, Pr)`: the family's base
  class (`TubeCorrelation`, `PackedBedCorrelation`) supplies the geometry.
  `register_correlation(name, nusselt, flow)` adds one, a function or a subclass, and the
  models of that flow accept its name; PyTES adds its own the same way, and users locally,
  in their session. Built-in correlations cannot be replaced, a name is registered once
  unless `replace=True`, and `"constant"` is reserved. `pytes.conformance.check_model`
  runs the contract on a model that uses one. Rejected: a law object as an option value
  (options stay strings, so they print, compare and are enumerated by the conformance
  suite); a `flux_law=` model argument (a second route for variants); one generic
  `"correlation"` value (a second correlation per family would need a new option). Laws
  other than a Nusselt correlation still go through the composition API.
- **Laws that read the storage** (maintainer, 2026-10-22, F-051): a law may need a
  variable of another submodel, e.g. Jeffreson's correction for a lumped sphere,
  `h_eff = h / (1 + Bi / 5)` with `Bi = h R / k`, needs the storage conductivity. The law
  reads it as a `pybamm.CoupledVariable` listed in `SurfaceFluxLaw.coupled_variables`, and
  the coupling declares those as its own requirements, so the wiring checks and the
  resolution see them. The `heat_flux` interface is unchanged. Every storage provides
  `"<label> thermal conductivity [W.m-1.K-1]"` for this.
- **Upstream:** face boundary values (PyBaMM #5094, which the maintainer plans to implement)
  would let a flux be imposed directly. The ledger stays exact either way; it may then become
  an option if the direct flux is measurably faster. It is not to be retired for its own
  sake.

### D7. Storage state list is open; internal states have their own submodel
The storage submodel's state list is `[H, *internal states]` (today `[H]`). Rationale: kinetic
undercooling and hysteresis then arrive without touching the storage (maintainer,
2026-10-14). The responsibilities are split:
- **Material:** the constitutive relation only. It declares the names of the internal states
  its relation needs and maps `(H, states) -> T`, `k` and liquid fraction. No time
  derivatives. Pure and composite materials are the zero-extra-states case.
- **Kinetics submodel** (one per storage medium that needs it, in the storage slot): owns the
  internal state variables, their equations and initial values; reads `T` and `H` from the
  storage and provides the states on the same domain. Chosen through `options` (D3), e.g.
  `{"phase change kinetics": "supercooling"}`, so any PCM combines with any kinetics.
- **Storage:** reads the states its material declares as coupled variables and knows
  nothing about kinetics. A material needing a state that no submodel provides fails the
  wiring check.
- **Energy:** `H` stays the only energy-bearing state, so conservation (D6) is unaffected.

The conformance check "T is a function of H alone" applies only to materials declaring no
internal states.

**Melting range is physical; smoothing is separate** (maintainer, 2026-10-14). The material
has a physical melting range, with `H(T)` linear between solidus and liquidus (a data-sheet
value users will fit), and a separate small numerical smoothing width for the corners
(speed-up of 2 to 3 times for about 0.05 K at 0.5 K). The parameters are
`"PCM melting range [K]"` (physical, solidus to liquidus around the melting temperature;
a property of each PCM layer, e.g. 0, a sharp melting point, for the packed-bed PCMs and 2 K
for PCM 60) and `"PCM smoothing width [K]"` (numerical; 0.01 K in the registered PCM layers
since 2026-10-21, F-048, and 0.5 K before).
Either or both may be 0 (F-035). In the mushy zone the enthalpy carries the latent heat plus
the mean of the solid and liquid heat capacities.

### D8. Fluid-property object is the only door to fluid properties
Provides thermophysical properties only: `T(h, p)`, `rho`, `c_p`, `k` and `mu`, as functions
of the state `(h, p)`, plus `h(T, p)` for the inlet and initial conditions (maintainer,
2026-10-14). Rationale: the fluid state is the specific enthalpy (D5), and for a refrigerant
`(h, p)` is the natural input of property tables (e.g. CoolProp's `HmassP`) while `T` loses the
quality, being flat across the two-phase dome. `p` is ignored by liquids and kept as the hook.
Power is `mdot * (h_out - h_in)`. For a constant-`cp` liquid this equals `mdot * cp * dT`, so
today nothing changes numerically, but the definition stays valid for a refrigerant.
- **The heat transfer coefficient is not a fluid property.** A correlation needs the fluid's
  properties but also the family geometry (hydraulic or capsule diameter, porosity) and
  `mdot`. It belongs to the surface flux law of the coupling (D6), which takes properties
  from this object; the constant `"Heat transfer coefficient [W.m-2.K-1]"` is the default
  law's parameter.
- **Compressible fluids:** `(h, p)` makes the properties ready for any equation of state. What
  compressibility additionally needs is in the fluid equations, not here: mass conservation
  (`mdot` varying along `z` in a dynamic form), the transient term `rho u = rho h - p`, and a
  pressure field `p(z)` from a pressure-drop model. Today `p` is not modelled; when it is, it
  is a variable of the fluid submodel passed to these functions.

### D9. Controls are declared by the model
Each model advertises its control set (today: inlet temperature and mass flow rate). Each
experiment step type declares which controls it drives, and a step must fix **all** of the
model's controls; the runner rejects a mismatch, naming both sets. Rationale: refrigerant HTF
will need different controls.
- **Canonical controls** (maintainer, 2026-10-14): a model declares the minimal set that fixes
  what enters, never alternative descriptions of the same quantity. For a refrigerant that is
  mass flow rate, pressure and inlet enthalpy; superheat, quality or saturation temperature
  are conveniences of the step types, which convert them to inlet enthalpy (e.g.
  `h_in = h(T_sat(p) + 5 K, p)` for 5 K of superheat). For a liquid, inlet temperature fixes
  the inlet enthalpy uniquely and stays the control.

### D10. PyTES carries its own experiment runner
Built on PyBaMM's unified experiment mode (one model, controls as solver unknowns, step
index selecting the branch), free of battery assumptions so it stays upstreamable. Step
types, named after what they hold as PyBaMM's are (maintainer, 2026-10-23, issue #18,
F-054; formerly `ConstantInputs` and `ConstantPower`): `Inlet` (the inlet temperature and
the mass flow rate), `Power` and `Rest` (no flow; the inlet temperature is held where the
previous step left it, or at a given value); values may be constants, time series or
functions of time. Terminations: outlet or inlet temperature, mass flow rate, liquid fraction, custom, plus a maximum duration per step (a time-series step defaults to the length of its
series). Cycles group steps and can repeat. Returns an ordinary `pybamm.Solution` with
`.cycles` and `.steps`. Point probes `T(t, z, ...)` are PyBaMM's own
`solution[name](t=..., z=...)`; no PyTES code.
- **`Power` adjusts the control left free** (maintainer, 2026-10-14):
  `Power(P, mass_flow_rate=...)` adjusts the inlet temperature,
  `Power(P, inlet_temperature=...)` adjusts the mass flow rate; giving both or
  neither raises. Rationale: the names `ConstantPowerInletTemperature` and
  `ConstantPowerFlowRate` read as what is held, but named what is adjusted. The rule extends
  to refrigerant controls (D9).
Upstream contributions are welcome later but are not assumed.

### D11. Operating mode is defined by heat flow into or out of the storage
Charge means heat flows into the storage. Discharge means heat flows out. This holds when a
refrigerant makes the unit a condenser (charge) or an evaporator (discharge).
The model equations are the same for both: whether the unit charges or discharges follows
from the inputs (inlet state against storage state), and the sign of the power says which.
- **No cut-off in the model** (maintainer, 2026-10-14). `operating_mode` and the parameter
  `"Cut-off temperature [K]"` are removed: cut-offs live only in the experiment's
  terminations (D10, D14). Rationale: the option only ever added an event, and two places to
  stop a simulation can disagree; a default discharge event also made a charge from an empty
  state fail at once. A plain `pybamm.Simulation` user runs a one-step experiment or appends
  a `pybamm.Event`.
- **The cut-off quantity belongs to the fluid:** the terminations offered are on outlet
  temperature for a liquid; on outlet enthalpy or quality for a refrigerant, whose
  temperature is flat in the two-phase region. Nothing to build now.

### D12. Variable conventions
- **Tiers.**
  - *Required for every model:* time, mass flow rate, inlet and outlet temperature, inlet and
    outlet specific enthalpy, power, discharged energy, storage thermal energy, total thermal
    energy, heat loss power, fluid specific enthalpy and fluid temperature along the flow
    path (the enthalpy is the state, D5); and, for comparison with measurements (issue #14,
    F-055), the volume flow rate, the pumped volume, the inlet-outlet temperature
    difference, the fluid velocity, the charged energy, the two throughputs, and the
    storage temperatures averaged over the whole storage and over each cross-section of the
    flow path (`Storage average temperature [K]`, `Storage cross-section average
    temperature [K]`), volume-weighted over all the storage (maintainer, 2026-10-24).
    Rationale: one name in every family, and a quantity that compares models that split the
    storage differently (the mush model's fins and PCM against the sharp front's composite).
    In a packed bed the cross-section average is the capsule's volume average.
  - *Every storage:* its own volume-weighted averages, `<label> average temperature [K]` and
    `<label> cross-section average temperature [K]` (F-055, defining what F-043 had dropped
    as undefined).
  - *Optional, standard name when present:* average liquid fraction, pressure drop, outlet
    fluid state (quality, superheat; later).
  - *Family-specific:* namespaced with a prefix ("Capsule ...", "Fin ...") so they cannot
    collide with the shared set.
- **One standard name for the flow path** across families: domain `"flow path"`,
  coordinate `z` (maintainer, 2026-10-15; was `"pipe"`, which does not fit a bed).
- **Storage domains** (maintainer, 2026-10-15), named by geometry, not by a figure, so that
  they also fit a future Cartesian channel: `"storage depth"` (coordinate `y`), the distance
  into the storage from the heat-exchange wall (not along the flow); `"fin gap"`
  (coordinate `x`), across the gap between two resolved fins; `"capsule"` (coordinate `r`),
  from a capsule's centre. Were `"PCM vertical"` and `"PCM horizontal"`.
- **SI canonical** (maintainer, 2026-10-16, extending "K canonical"). Models define every
  quantity in SI units: K, W, J, kg.s-1, and so on. For reading, one shared helper
  (`pytes.variables.add_unit_twins`, run when a model is built) generates unit twins as model
  variables: `[K]` → `[degC]`, `[W]` → `[kW]`, `[J]` → `[kWh]`, `[s]` → `[min]` and `[h]`,
  `[m3.s-1]` → `[l.min-1]` and `[m3]` → `[l]` (F-055). Twins are never written by
  hand; a model that does is rejected. Rationale: one place for every conversion, no
  computational cost (PyBaMM evaluates a variable only when it is requested; measured), and
  the twins work everywhere, `QuickPlot` included. `[degC]` departs from PyBaMM's `[C]`
  deliberately: `[C]` is also the coulomb, and TES users have no reason to know PyBaMM's
  habit. Differences are K-only and get no twin: any name containing "temperature
  difference" (e.g. `"Inlet-outlet temperature difference [K]"`) (maintainer, 2026-10-14).
  Time is in seconds by default; `Time [min]` and `Time [h]` are generated twins.
- **Power positive on discharge.** Charging gives negative power.
- **Heat loss power** is a required variable, positive for loss, identically zero for now
  (no casing yet). Conservation identity, which is the conformance check:
  `change in total energy = -int(power) dt - int(heat loss) dt`.
- **Discharged energy** is the net time integral of power, and charged energy its opposite.
  The throughputs are separate variables (maintainer, 2026-10-24, F-055): the energy out
  while discharging and the energy in while charging, whose ratio over a cycle is its
  round-trip efficiency.
- **Two energies.** *Storage thermal energy* (PCM or capsule material, plus fins where
  present). *Total thermal energy* (storage plus fluid inventory), which is the one in the
  conservation identity.

### D13. No state of charge in the models (maintainer, 2026-10-14)
Models provide energies, not a SOC. Rationale (after discussion with a field expert): a SOC
between 0 and 1 needs a "full" energy, and a TES device has no natural maximum; the upper end
is a convention (an upper temperature) imposed on the user. Its inverse is ill-posed too: many
states share one energy (hot and cold regions, a supercooled liquid and a partly solid
mixture), so "start at SOC x" is not a state. Energy is well defined, and the conservation
identity needs only differences.
- **Energy between two states** is toolkit post-processing (D15):
  `pytes.energy_between(model, T_a, T_b)`, the total thermal energy between
  the uniform states at `T_a` and `T_b`, derived symbolically from materials and geometry,
  never a hand-entered nominal value. A user-defined SOC (energy or exergy based) can be built
  on it later, as just another variable.
- **Average liquid fraction** is an optional diagnostic: weighted by PCM volume, with fins,
  capsule shells and fluid excluded (F-010), in every family.
- Superseded: the energy-based SOC on a declared temperature window (Stage A, F-024, F-025).

### D14. Energy reference and initial state are temperatures; terminations belong to the experiment
- **Energy reference:** `"Reference temperature [K]"`, a device-level parameter (default
  10 °C). Every energy is zero at the uniform state at that temperature (solid at the melting
  temperature), in every family; no model has its own enthalpy zero. Energy differences do
  not depend on it.
- **Initial state:** uniform at `"Initial temperature [K]"`, solid at the melting
  temperature (maintainer, 2026-10-14). Temperature, not enthalpy: at equilibrium every medium
  (PCM, metal, fluid) shares one temperature but each has its own enthalpy, so an enthalpy is
  not one number for the device; a temperature is also what is measured. Non-uniform or
  mid-melt starts use PyBaMM's `model.set_initial_conditions_from(solution)`. An
  `"Initial liquid fraction"` (used at exactly `T_m`) is added only if a use case appears.
  Internal states (D7) get their initial values from the kinetics submodel.
- **Terminations** (e.g. outlet below a threshold) are application-specific and belong to the
  experiment (D10, D11); the models have no events.
- **Conversion helpers:** materials provide `T2H`/`H2T`, the fluid `h(T)`/`T(h)`; at device
  level, `energy_between`.
- **Parameter validation** (toolkit): physical ranges (e.g. melting range positive).
- **Conformance:** every energy is zero at the uniform state at the reference temperature,
  and the initial temperature is honoured.
- Superseded: the temperature window and initial state by SOC (F-024), and the
  `initial_state` option (F-029).

### D15. KPIs and standard plots live in the toolkit
KPIs are post-processing on a `Solution`, not model outputs. The KPI set is chosen after the
alpha has users, since it does not constrain the models. Default quick-plot variables: inlet
and outlet temperature, power, discharged energy, fluid temperature profile snapshots
(`pytes.plotting`, in the `plot` extra: `plot_summary`, `plot_power_against_energy`,
`plot_fluid_profiles`). Power
versus discharged energy is the key comparison plot.

### D16. Relationship with PyBaMM
- Workarounds only in `compat`, each tagged with the upstream issue and removal condition.
- Support PyBaMM releases from the last 3 months (CalVer). CI against the latest release is
  blocking, against `main` non-blocking.
- Support every Python version PyBaMM supports (maintainer, 2026-10-16; today 3.10 to
  3.15), tested in CI, all blocking. Platforms (maintainer, 2026-10-17): Linux is the
  reference, with every Python version, coverage, notebooks and PyBaMM `main`; macOS and
  Windows run the tests on the oldest and newest Python version. A version whose dependencies do not install yet runs
  non-blocking until they do (3.15 did, until `pybammsolvers` 0.11.1 shipped its wheels).
- Testing layout (maintainer, 2026-10-16): tests grouped by what they test (`conformance/`,
  `models/`, `submodels/`, `experiments/`, `toolkit/`, `validation/`), with a `slow` marker
  for cost, not split into unit and integration (the suite runs in about 25 s, and the
  conformance suite is clearest as one folder). The example notebooks run in CI with
  `nbmake`. Coverage (all tests, slow ones included) goes to Codecov.
- **Fluid advection scheme** (maintainer, 2026-10-23, issue #7, F-052): second order by
  default, `compat.LimitedFiniteVolume` (MUSCL with the van Albada limiter, applied to
  gradients so that it works on non-uniform meshes), with the inflow and outflow faces
  first order so that the outlet value and the exact energy balance are unchanged. It is
  numerics, chosen through `spatial_methods` (`compat.fluid_spatial_method("first order")`
  for PyBaMM's own upwinding), not a model option. Rationale: on the models it costs about
  the same per cell and is far more accurate, so the default meshes along the flow path
  were reduced to balance their error against the other directions (sharp front 20 by 20,
  packed bed 40 by 40; mush unchanged). It moves to PyBaMM's finite volumes when they offer
  it.
- Known upstream items: `pybamm.upwind` inflow uses a ghost node (`2*T_bc - T_1`) and can draw
  in fluid colder than the inlet (#5860, filed by the maintainer 2026-10-07; workaround in
  `compat`); first-order upwinding is diffusive
  (matters most for packed-bed thermoclines; PyTES uses its own second-order scheme until
  PyBaMM has one, below); face boundary values (#5094, assigned to the
  maintainer); `pybamm.Simulation` does not resolve coupled variables
  by default (`resolve_coupled_variables=True`, or `discretisation_kwargs` in `Simulation`;
  workaround in `compat`, F-028); `pybamm.Solution` takes no new attributes since 26.10
  (workaround in `compat`); downstream packages cannot add citation databases.
- No upstream issue filed yet for the coupled-variable resolution, `Solution` metadata or
  citations (maintainer's call when to file; drafts with MWEs in the gitignored
  `docs/upstream/`).
- `pybamm.QuickPlot` hard-codes its default line colours, although its docstring says it
  follows matplotlib's colour cycle; the maintainer will fix it upstream (2026-10-16). No
  PyTES workaround; pass `colors=` meanwhile.

### D17. Housekeeping
Name PyTES, BSD-3 licence, tooling `uv` + `ruff` + pre-commit, pytest with a `slow` marker.
Settled at the end of Stage B (maintainer, 2026-10-15):
- **Repository layout:** one package, one subpackage per family (`pytes.models.finned_tube`,
  `pytes.models.packed_bed`).
- **Conformance parametrisation:** importable checks in `pytes.conformance`, run by
  `tests/conformance/` over every admitted model with every combination of its options
  (`tests/conftest.py::MODELS`).
- **Options:** shape as in D3 (F-041).
- **Changelog** (maintainer, 2026-10-16): towncrier fragments in `changelog.d/`
  (`<PR>.<type>.md`; types breaking, contract, deprecated, feature, improvement, fix; a PR
  may add several; `contract`, for any change to the model contract with its finding, added
  by the maintainer on 2026-10-22), assembled
  into `CHANGELOG.md` at release; CI requires a fragment on pull requests unless labelled
  `no changelog`. Rationale: no conflicts between pull requests and no forgotten entries,
  the two problems of a hand-edited changelog. `CONTRIBUTING.md` adapted from PyBaMM's
  (itself from PINTS); licence BSD 3-Clause, "the PyTES developers".
- **Documentation site** (issue #4, 2026-10-22): Sphinx on Read the Docs, set up as
  PyBaMM's, so that `intersphinx` links to PyBaMM's classes. The API reference comes from the
  NumPy docstrings (autodoc and napoleon), with each object documented once, under the name
  users import it by (`pytes.SharpFrontModel`, `pytes.submodels.EnthalpyStorage`). The
  example notebooks stay in `examples/` and are rendered with myst-nb from their committed
  outputs, never executed (CI runs them; myst-nb needs no pandoc). The changelog and
  `CONTRIBUTING.md` stay at the root for GitHub, and their pages are generated at each
  build with links into the site. A `docs` dependency group; CI and Read the Docs build with
  warnings as errors. Bibliography roles (sphinxcontrib-bibtex) can follow (D1).
- **Releases** (maintainer, 2026-10-17): versions in `pyproject.toml` and `CITATION.cff`;
  a GitHub release `v<version>` runs `release.yml` (build, check, attach) and Zenodo mints
  its DOI. PyPI publishing is wired (trusted publishing) but off until the repository
  variable `PUBLISH_TO_PYPI` is set; the source distribution lists its contents. The PyPI
  name is `pytes-thermal` (maintainer, 2026-10-17): `pytes` is an empty project held since
  about 2010 to protect `pytest` from typosquatting. The import name stays `pytes`.
- **Renames and deprecation** (maintainer, 2026-10-23, issue #17, F-053): every rename of
  a public name is one entry of `pytes.deprecation.RENAMES` (old and new name, finding,
  release that renamed it, release that removes the alias). While the alias is active the
  old name works and warns with `PyTESDeprecationWarning`, pointing to the user's line; once
  retired it raises an error giving the new name, and the entry stays. Covered: classes and
  functions (the old module sets `__getattr__ = module_getattr(__name__)`) and option names.
  Policy before 1.0: an alias lives for at least one release and is removed in the next
  minor release; a rename without an alias (as F-050) needs the maintainer's agreement. The
  tests enforce it: each entry warns or raises, a test fails once the version reaches an
  active alias's removal release (then set `alias=False`), PyTES's own tests turn the
  warning into an error, and the example notebooks and user documentation must not use old
  names. Rationale: one place to rename, consistent messages, and no alias that outlives
  its deadline. The policy after 1.0 is part of Stage E.

## 3. Deferred, with the hook that must exist now

| Item | Hook required now |
|---|---|
| Refrigerant HTF (PCM unit as condenser/evaporator) | Power from enthalpy; fluid-property object; controls declared by model; fluid slot not defined as an advection PDE; outlet state concept; operating mode by heat flow |
| Kinetic undercooling, hysteresis, subcooling | Storage state list; material maps `(H, states) -> T` and declares state names; states evolved by a kinetics submodel (D7); conservation tests unchanged; "T = f(H)" test only for stateless materials |
| Axial dispersion in the fluid (maintainer, 2026-10-15) | The fluid equation keeps an optional axial term (D5); `"Heat transfer fluid conductivity [W.m-1.K-1]"` is kept for it |
| Capsule shell (packed bed) | Resistance only: a series-resistance surface flux law (D6), no new state. Thermal mass too: the shell as a second `EnthalpyStorage` of a sensible material on a spherical shell domain, coupled to the fluid and to the PCM like the fins in the mush model; needs `EnthalpyStorage` boundary conditions from couplings on both sides (today the outer side is zero flux). `"Capsule radius [m]"` is the outer radius, so `"Capsule shell thickness [m]"` (default 0) adds without renames |
| Casing and heat losses | Heat loss power variable (zero); total energy includes everything that holds heat in the model |
| Lumped storage element in the finned tube | The `"storage element"` option (D4), `LumpedGeometry` and `LumpedStorage`, which are not specific to capsules; the surface-to-volume ratio and the internal-resistance correction of an annulus come from the family |
| 0D lumped models, reduced-order models | Shared contract; same outputs and parameters within a family |
| SOC definitions (energy or exergy based), as toolkit post-processing (D13) | Reference temperature is a parameter; `energy_between`; ambient temperature to be added for exergy |
| Measured DSC enthalpy curves | Material classes expose `H2T`, `T2H`, `k(H)`, liquid fraction |
| Temperature-dependent properties (maintainer, 2026-10-18) | Models read properties only through the fluid-property object (functions of `(h, p)`) and the material classes (`k(H)`, `H2T`), never as bare parameters. Until then, each parameter layer's docstring records the temperature at which its constant values were taken from the source |
| Pipe networks, channelling | Single flow path is assumed in D5; revisit if needed |
| Serpentine tube layouts, long term (issue #40; maintainer, 2026-10-25) | Nothing in the contract assumes that a storage has a single active boundary: storage between two passes is heated from both sides, as is the capsule shell. Exact conservation then needs each face's discrete flux (PyBaMM #5094, tracked in #39). The passes are in series, so D5's single flow path holds. The number of passes and the layout fix the model's structure, so they are set when the model is built, not as parameter values (see §4, options or composition) |
| Model card rendering | Keep the submodel metadata complete now; render later |
| Packaged sensitivity and fitting tools | Keep as notebooks until a second use proves them |
| Upstream experiment generalisation, #5094 follow-up | `compat` isolation; runner free of battery assumptions |
| KPI set | Variable tiers (D12) |
| Deprecating option values (issue #17) | A new `kind` in the rename registry (D17), checked in `process_options` next to option names; no value has been renamed yet |
| Deprecating variable and parameter names (issue #17) | A new `kind` in the rename registry (D17). PyBaMM looks both up itself (`FuzzyDict`, whose renames are hard-coded battery cases, and solutions use `dict.get`), so it needs a rename hook upstream, or a `compat` shim |

## 4. Open

Nothing open at the end of Stage B (2026-10-16). New questions are added here as they
arise.

- **Options or composition** (maintainer, 2026-10-23): how many variants a model should
  offer as options, rather than leave to composition from submodels (`ComposedModel`, D3).
  Options are enumerated and checked by the conformance suite, but each one multiplies the
  combinations; the lumped capsule's correction was folded into one option value for that
  reason. To decide before more options are added.

## 5. Stage plan

| Stage | Contents |
|---|---|
| **A. Skeleton** | Submodel refactor of the finned-tube code prototype; draft contract (a page or two); conformance tests ported from the existing 72 |
| **B. Bed port** | Bring the encapsulated family in under the contract; merge material classes; Schumann (sensible limit) and spherical Stefan benchmarks; log every mismatch. **Closed 2026-10-16**: all acceptance criteria met (F-039 to F-041), §4 Open emptied (F-042 to F-046) |
| **C. v0.1 alpha** | Both families, experiment runner, standard plots, cross-family design-study notebook, CI and packaging. (The PyBOP example is dropped: maintainer, 2026-10-16.) **Closed 2026-10-22**: 0.1.0a1 (2026-10-17) and 0.1.0a2 (2026-10-22) released, CI running (F-047) |
| **D. Gap filling** | Lumped capsule (done: D4, F-051), flow-dependent HTC (done early: D6, F-049), advection scheme improvements tied to upstream (a second-order scheme, the default: D16, F-052) **Closed 2026-10-23**: all three done (PRs #11, #15, #16) |
| **E. v1.0** | Contract freeze, deprecation policy after 1.0 (the mechanism and the alpha policy are in D17), one experimental validation per family, docs, admission guide |

Do not call any API stable before the end of Stage B. Time-box stages. If A overruns, cut
scope in C rather than extend.

### Stage A brief: refactor the finned-tube code prototype into submodels
**Goal:** both existing models become fixed compositions of fluid, storage and coupling
submodels, with `model.submodels` populated and the draft contract written.
**In scope:** the working copy in this repo; the draft `docs/design/contract.md`; porting the
existing tests into `tests/conformance/` and `tests/submodels/`.
**Acceptance criteria:**
- The existing 72 tests pass, and results match the reference models.
- Exact energy conservation holds (global identity from D12).
- Power is computed from fluid enthalpy through the fluid-property object.
- Capacity and SOC are derived from the window parameters; SOC is 0 and 1 at the uniform window
  states. *(Done in Stage A, then superseded by D13 and D14 on 2026-10-14.)*
- Storage declares a state list; materials map `(H, states) -> T`.
- Submodels declare required and provided variables, checked automatically.
- Celsius twins are generated by a shared helper.
- Any workaround is in `compat`, tagged.
**Do not touch:** `reference/`; the experiment runner's behaviour (adapt only what the
controls-declared-by-model change requires).
**First task:** side-by-side diff of the two reference repos (see Stage B), seeding
`findings.md` before any refactoring. Report before proceeding.

### Stage B brief: port the encapsulated bed
**Goal:** the packed-bed family passes the same conformance suite as the finned-tube family.
**Acceptance criteria:**
- Conformance suite passes unmodified for both families, or each exception is a logged
  finding with a verdict.
- Material classes are merged (one copy).
- Sensible limit: the PCM bed model with a pure sensible material reproduces the Schumann
  solution within a stated tolerance.
- Spherical Stefan benchmark passes for the capsule storage.
- A shared fluid submodel is used by both families.
- Liquid fraction weighting is consistent with the finned-tube definition (D13).
**Expected friction, in order of likelihood:** power and fluid-state definition; film
coefficient source; exactness of energy conservation across the coupling; controls (flow rate
affecting physics); fluid porosity and capacity terms; domain layout; naming.

## 6. Validation strategy

Analytical and invariant checks first, experimental data at v1.0 (analytical solutions in
`pytes.validation`; benchmarks in `tests/validation/`): energy conservation
(exact), Schumann solution (sensible bed), Stefan problem (planar and spherical),
reference-model comparison for the finned tube, cross-fidelity comparison within a family,
energy-reference checks.
