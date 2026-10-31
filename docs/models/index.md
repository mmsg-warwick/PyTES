# Models

PyTES models heat batteries in which a heat transfer fluid flows through or around a
separate storage medium. The models come in families, one per geometry:

| Family | Models | Storage |
|---|---|---|
| [Finned tube](finned_tube.md) | {class}`~pytes.SharpFrontModel`, {class}`~pytes.MushModel` | a block of PCM with metal fins, crossed by tubes |
| [Packed bed](packed_bed.md) | {class}`~pytes.PackedBedModel` | a bed of spherical PCM capsules |

This page describes what every model shares: how it is built, the equations of the fluid,
the storage and the coupling between them, and the power and energies. The family pages
describe the geometry and the equations specific to each family.

```{toctree}
:maxdepth: 1

finned_tube
packed_bed
```

## How a model is built

Every model is a fixed composition of submodels, chosen by its options:

- the **fluid**, the heat transfer fluid flowing along the flow path;
- the **storage**, heat conduction in the storage medium;
- the **coupling**, the heat exchanged between the two at their common surface;
- the **device energy**, the power, the energies and the initial state of the whole device.

A family may add submodels: the mush model resolves the fins as a second storage, with a
coupling between the fins and the PCM. `model.submodels` lists the submodels of a model, and
`model.print_submodel_info()` gives the variables each one needs and provides, its
parameters and its assumptions.

The equations below are in SI units, as are the models. Every model describes one flow
path (one tube, or the whole bed) and multiplies the device totals by the number of flow
paths, $N$.

## The heat transfer fluid

The state of the fluid is its specific enthalpy $h_f(z, t)$, carried along the flow path
($0 < z < Z$) and heated by the storage:

$$
A_\mathrm{flow}\, \rho\, \frac{\partial h_f}{\partial t}
+ \frac{\dot m}{N} \frac{\partial h_f}{\partial z} = q',
\qquad h_f(0, t) = h(T_\mathrm{in}(t)),
$$

where $A_\mathrm{flow}$ is the flow area of one path, $\dot m$ the mass flow rate through the
whole device, and $q'$ the heat the fluid gains per unit length of the path, from the
coupling. The outlet temperature is $T_\mathrm{out} = T(h_f(Z, t))$. The fluid properties
come from a fluid-property object as functions of the enthalpy; for the liquids in PyTES
today, the density $\rho$ and the specific heat capacity $c_p$ are constant and
$h(T) = c_p (T - T_\mathrm{ref})$. Conduction and dispersion along the flow are neglected.

## The storage: the enthalpy method

Heat is conducted in the storage by the enthalpy method. The state is the enthalpy per unit
volume $H$, which includes the latent heat, and

$$
\frac{\partial H}{\partial t} = \nabla \cdot \left( k \nabla T \right),
$$

in the coordinates of the storage (cylindrical around a tube, spherical in a capsule,
Cartesian between two fins). The temperature $T(H)$ and the conductivity $k$ come from the
material. A phase-change material melts between its solidus $T_\mathrm{sol}$ and its
liquidus $T_\mathrm{liq}$, a melting range $\Delta T_m$ centred on the melting temperature
$T_m$:

$$
H(T) =
\begin{cases}
\rho c_s\, T, & T \le T_\mathrm{sol}, \\
H_\mathrm{sol} + \left( \dfrac{\rho L}{\Delta T_m} + \overline{\rho c} \right)
(T - T_\mathrm{sol}), & T_\mathrm{sol} < T < T_\mathrm{liq}, \\
H_\mathrm{liq} + \rho c_l\, (T - T_\mathrm{liq}), & T \ge T_\mathrm{liq},
\end{cases}
$$

with $\rho c_s$ and $\rho c_l$ the volumetric heat capacities of the solid and the liquid,
$\overline{\rho c}$ their mean, and $\rho L$ the latent heat per unit volume. With
$\Delta T_m = 0$ the material has a sharp melting point: the temperature stays at $T_m$
while the enthalpy crosses the latent heat. The liquid fraction is
$\phi = (H - H_\mathrm{sol}) / (H_\mathrm{liq} - H_\mathrm{sol})$, clipped to $[0, 1]$.
For speed, the corners of $T(H)$ at the solidus and the liquidus are rounded over a small
smoothing width, which may be set to zero. A sensible material, such as the metal of the
fins, has $H = \rho c\, T$.

Convection in the liquid PCM and the change of volume on melting are neglected.

## The coupling: heat at the surface

At the surface between the fluid and the storage, the heat flux into the storage is given
by a surface flux law, by default Newton's law of cooling,

$$
q = h_c \left( T_f - T_s \right),
$$

with $T_f$ the fluid temperature, $T_s$ the storage temperature at the surface, and $h_c$
the heat transfer coefficient. The coefficient is chosen with the option
`"heat transfer coefficient"`: `"constant"` (the default) takes it from the parameter
`"Heat transfer coefficient [W.m-2.K-1]"`; a correlation, such as `"Gnielinski"` for the
finned tubes or `"Wakao-Kaguei"` for the packed bed, computes it from a Nusselt number,
$h_c = \mathrm{Nu}\, k_f / \ell$, with $k_f$ the conductivity of the fluid and $\ell$ the
length of the correlation (the tube or the capsule diameter).

The heat the fluid gains, $q'$, is taken from the storage's own discrete energy balance:
the heat that left the storage through its boundary. This is what makes energy conserved
exactly by the discretised model, whatever the flux law or the material.

## Resolved or averaged along the flow path

```{figure} diagrams/resolved_averaged.svg
:class: pytes-diagram dark-light
:width: 640px
:alt: Resolved: a storage cross-section at each position along the flow path, each exchanging heat with the local fluid. Averaged: one storage cross-section exchanging heat with the fluid averaged along the path.

The option `"storage along flow path"`: a storage cross-section at every position along the
flow (resolved), or one that stands for their average (averaged).
```

By default the storage is **resolved**: there is a storage cross-section at every position
$z$, exchanging heat with the fluid there. With
`options={"storage along flow path": "averaged"}`, one storage cross-section stands for the
average along the flow path. It exchanges heat with the fluid averaged along the path,
$\bar h_f = \frac{1}{Z} \int_0^Z h_f \, \mathrm{d}z$, at the temperature
$\bar T_f = T(\bar h_f)$, and the heat it gives up is spread uniformly along the path:
$q'$ is the same at every $z$. This removes one dimension from the storage, so the averaged
models are much faster. They store and deliver the same energy, but cannot represent a
thermal front moving along the flow path ([Tutorial 2](../examples/getting_started/tutorial_2_finned_tube_models.ipynb)).

## Power and energy

The power of the device is defined from the enthalpy of the fluid, positive on discharge:

$$
P = \dot m \left( h_\mathrm{out} - h_\mathrm{in} \right),
\qquad E_\mathrm{discharged}(t) = \int_0^t P \, \mathrm{d}t'.
$$

The total thermal energy $E$ is the energy of the storage and the fluid in the whole device,
zero at the uniform state at the reference temperature. Without heat losses (none of the
models have them yet), $E(t) - E(0) = -E_\mathrm{discharged}(t)$, and the discretised
models meet this to round-off: the [conformance suite](../design/contract.md) checks it
for every model.

The models have no state of charge: the energy a device holds depends on the temperatures
it works between, a choice of the user. {func}`pytes.energy_between` gives the energy
between two uniform temperatures.

The device starts uniform at `"Initial temperature [K]"`, each material at its equilibrium
state there: solid at the melting temperature for a sharp melting point, partly liquid
within a melting range. To start from another state, use
`model.set_initial_conditions_from(solution)`.
