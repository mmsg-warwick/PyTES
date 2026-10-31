# Finned tube

A finned-tube heat battery is a block of phase-change material (PCM) crossed by $N$
parallel tubes that carry the heat transfer fluid. Thin metal fins, annular discs around
each tube, carry the heat into the PCM, which conducts poorly on its own. The family has
two models: the {class}`~pytes.SharpFrontModel`, which homogenises the fins and the PCM,
and the {class}`~pytes.MushModel`, which resolves them separately. Both are derived, by
homogenisation, in [Luckins and Brosa Planella (2025)](https://doi.org/10.1098/rspa.2025.0660).

## Geometry

```{figure} diagrams/finned_tube.svg
:class: pytes-diagram dark-light
:width: 720px
:alt: A block of PCM crossed by parallel tubes, with fins across the tubes; and a section across the tubes, with the storage around one tube marked.

The device, along and across the tubes. All the tubes are the same, so the models describe
one tube and the storage around it.
```

The models describe one tube and multiply the device totals by the number of tubes. The
storage around a tube reaches out to a radius $R_f + D$, about half the distance to the
next tube, where no heat crosses by symmetry. In the models, it is an annulus around the
tube.

```{figure} diagrams/finned_tube_unit.svg
:class: pytes-diagram dark-light
:width: 600px
:alt: Half a section along one tube: the fluid in the tube, the tube wall, and above it the PCM with fins of thickness d_c every d_m, out to a distance D from the wall.

The storage around one tube, in half a section along it: the fluid flows along the tube
($z$), and the fins and the PCM extend from the tube wall ($y = R_f$) to $y = R_f + D$.
```

| Symbol | Parameter | Meaning |
|---|---|---|
| $N$ | `"Number of tubes"` | tubes in the device, in parallel |
| $Z$ | `"Tube length [m]"` | length of the flow path |
| $R_f$ | `"Tube radius [m]"` | inner radius of a tube |
| $D$ | `"Storage depth [m]"` | extent of the storage from the tube wall |
| $d_c$ | `"Fin thickness [m]"` | thickness of a fin |
| $d_m$ | `"Fin pitch [m]"` | distance between the centres of consecutive fins |
| $\delta$ | $d_c / d_m$ | volume fraction of the fins |

The positions are $z$, along the tube from the inlet; $y$, the distance from the tube axis,
from $R_f$ to $R_f + D$; and, in the mush model only, $x$, the distance from the centreline
of a fin, across the gap to the next one.

The fluid flows in a tube of flow area $A_\mathrm{flow} = \pi R_f^2$, carrying $\dot m / N$
(see [the fluid](index.md#the-heat-transfer-fluid)). Both models neglect conduction along
the tube in the storage, the thermal mass and resistance of the tube wall (other than the
heat transfer coefficient), and heat losses to the surroundings.

## Sharp-front model

```{figure} diagrams/sharp_front.svg
:class: pytes-diagram dark-light
:width: 640px
:alt: The homogenised storage above the fluid, with conduction in y at each z, a heat flux at the tube wall and no flux at the outer edge.

The sharp-front model: the PCM and the fins as one material, conducting heat radially at
each position along the tube.
```

The PCM and the fins are homogenised into one composite material: its heat capacities are
volume averages, $\rho c = \delta\, \rho c_\mathrm{metal} + (1 - \delta)\, \rho c_\mathrm{PCM}$,
its latent heat is $(1 - \delta)\, \rho L_\mathrm{PCM}$, as only the PCM melts, and its
conductivity is $k = \delta\, k_\mathrm{metal} + (1 - \delta)\, k_\mathrm{PCM}$, the
parallel arrangement, for heat flowing along the fins. At each position $z$, heat is
conducted radially:

$$
\frac{\partial H}{\partial t} = \frac{1}{y} \frac{\partial}{\partial y}
\left( y\, k \frac{\partial T}{\partial y} \right), \qquad R_f < y < R_f + D,
$$

$$
-k \frac{\partial T}{\partial y} \bigg|_{y = R_f} = h_c \left( T_f - T_s \right),
\qquad \frac{\partial T}{\partial y} \bigg|_{y = R_f + D} = 0,
$$

with $T_s = T|_{y = R_f}$. The fluid gains the heat that crosses the wall,
$q' = 2 \pi R_f\, h_c (T_s - T_f)$ per unit length of tube. With a sharp melting point and
no smoothing, the melting front is sharp, hence the name.

## Mush model

```{figure} diagrams/mush.svg
:class: pytes-diagram dark-light
:width: 520px
:alt: A fin and the PCM in the half-gap beside it: heat flows from the fluid into the fin root, along the fin, and from the fin into the PCM.

The mush model, at one position along the tube: heat flows from the fluid into the root of
a fin, along the fin ($y$), and from the fin into the PCM on either side ($x$). By symmetry,
half a fin and half a gap are modelled.
```

The mush model ([Luckins and Brosa Planella, 2025](https://doi.org/10.1098/rspa.2025.0660))
resolves the fins and the PCM separately, at each position $z$ along the tube. Heat flows
from the fluid into the root of each fin, radially along the fin, and from the fin into the
PCM between it and the next fin. The PCM uses the properties of the PCM on
its own. By symmetry, half the gap is modelled, from the face of the fin
($x = d_c / 2$) to the midplane ($x = d_m / 2$).

In the PCM, heat is conducted across the gap only, at each $y$:

$$
\frac{\partial H}{\partial t} = \frac{\partial}{\partial x}
\left( k \frac{\partial T}{\partial x} \right), \qquad
T \big|_{x = d_c / 2} = T_\mathrm{fin}, \qquad
\frac{\partial T}{\partial x} \bigg|_{x = d_m / 2} = 0.
$$

In the fins, heat is conducted radially, and the fin gains the heat the PCM on both sides
gives up through its faces:

$$
\frac{\partial H_\mathrm{fin}}{\partial t} = \frac{1}{y} \frac{\partial}{\partial y}
\left( y\, k_\mathrm{metal} \frac{\partial T_\mathrm{fin}}{\partial y} \right)
+ \frac{2}{d_c}\, k \frac{\partial T}{\partial x} \bigg|_{x = d_c / 2},
\qquad R_f < y < R_f + D.
$$

The heat the fluid exchanges over one fin pitch of wall enters through the fin root alone,
so the flux into the root is $d_m / d_c$ times the flux at the wall, and no heat crosses the
tip:

$$
-k_\mathrm{metal} \frac{\partial T_\mathrm{fin}}{\partial y} \bigg|_{y = R_f}
= \frac{d_m}{d_c}\, h_c \left( T_f - T_\mathrm{fin} \big|_{y = R_f} \right),
\qquad \frac{\partial T_\mathrm{fin}}{\partial y} \bigg|_{y = R_f + D} = 0.
$$

The fluid again gains $q' = 2 \pi R_f\, h_c (T_\mathrm{fin}|_{y = R_f} - T_f)$ per unit
length of tube. The PCM does not touch the tube wall, and no heat flows through it radially
or along the tube.

The mush model is three-dimensional ($x$, $y$, $z$), and much slower than the sharp-front
model. With thin, closely spaced fins the two agree closely
([Tutorial 2](../examples/getting_started/tutorial_2_finned_tube_models.ipynb)); the mush
model is the one to use when the fins are thicker or further apart, or when the temperature
between the fins matters.

## Options

| Option | Values |
|---|---|
| `"storage along flow path"` | `"resolved"` (default), `"averaged"`: see [resolved or averaged](index.md#resolved-or-averaged-along-the-flow-path) |
| `"heat transfer coefficient"` | `"constant"` (default), `"Gnielinski"`: fully developed flow in a smooth tube ({class}`~pytes.submodels.Gnielinski`), with $\ell = 2 R_f$ |

The averaged sharp-front model is one-dimensional ($y$), and the averaged mush model
two-dimensional ($x$, $y$).

## Examples

- [Tutorial 2: finned-tube models](../examples/getting_started/tutorial_2_finned_tube_models.ipynb)
- [Finned-tube models and their submodels](../examples/finned_tube_models.ipynb)
- [Heat transfer coefficient](../examples/heat_transfer_coefficient.ipynb)

## References

- E. K. Luckins and F. Brosa Planella, Homogenized models for composite phase-change
  materials, *Proceedings of the Royal Society A* **481**, 20250660 (2025),
  [doi:10.1098/rspa.2025.0660](https://doi.org/10.1098/rspa.2025.0660).
