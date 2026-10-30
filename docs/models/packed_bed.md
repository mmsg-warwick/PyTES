# Packed bed

A packed-bed heat battery is a column filled with capsules of phase-change material (PCM),
with the heat transfer fluid flowing through the voids between them. The large surface of
the capsules makes heat transfer easy, and the capsules are simple to make and replace. The
family has one model, {class}`~pytes.PackedBedModel`, with options for the capsules.

## Geometry

```{figure} diagrams/packed_bed.svg
:class: pytes-diagram dark-light
:width: 440px
:alt: A column of spherical capsules with the fluid flowing upwards through the voids; one height of the bed is marked, where one capsule stands for all those there.

The packed bed. At each height, every capsule is the same, so one capsule stands for all
those at that height.
```

| Symbol | Parameter | Meaning |
|---|---|---|
| $Z$ | `"Bed length [m]"` | length of the bed along the flow |
| $A$ | `"Bed cross-sectional area [m2]"` | area of the bed cross-section |
| $\varepsilon$ | `"Bed porosity"` | volume fraction of the bed taken by the fluid |
| $R$ | `"Capsule radius [m]"` | outer radius of a capsule |

The positions are $z$, along the bed from the inlet, and $r$, the distance from the centre
of a capsule, from 0 to $R$. The bed holds $(1 - \varepsilon) / (\tfrac{4}{3} \pi R^3)$
capsules per unit volume, with $a = 3 (1 - \varepsilon) / R$ of capsule surface per unit
volume.

The bed is a single flow path: the fluid flows through the voids, a flow area
$A_\mathrm{flow} = \varepsilon A$, carrying the whole mass flow rate $\dot m$ (see
[the fluid](index.md#the-heat-transfer-fluid)). The model neglects the capsule shell (its
thermal mass and resistance), conduction between capsules and along the bed in the PCM,
dispersion in the fluid along the bed, and heat losses to the surroundings.

## Equations

```{figure} diagrams/capsule.svg
:class: pytes-diagram dark-light
:width: 360px
:alt: A spherical capsule surrounded by fluid, with a liquid shell around a solid core and heat flowing in through its surface.

One capsule, melting from its surface inwards. Heat enters through the surface and is
conducted radially.
```

At each height $z$, heat is conducted radially in a capsule:

$$
\frac{\partial H}{\partial t} = \frac{1}{r^2} \frac{\partial}{\partial r}
\left( r^2 k \frac{\partial T}{\partial r} \right), \qquad 0 < r < R,
$$

$$
\frac{\partial T}{\partial r} \bigg|_{r = 0} = 0, \qquad
k \frac{\partial T}{\partial r} \bigg|_{r = R} = h_c \left( T_f - T_s \right),
$$

with $T_s = T|_{r = R}$, the temperature at the capsule surface. The fluid gains the heat
that leaves the capsules at that height, $q' = a A\, h_c (T_s - T_f)$ per unit length of
bed.

## Lumped capsules

With `options={"storage element": "lumped"}`, each capsule has a uniform temperature: one
enthalpy per capsule, heated through its surface,

$$
\frac{\mathrm{d} H}{\mathrm{d} t} = \frac{3}{R}\, h_c \left( T_f - T \right).
$$

This is much cheaper, and accurate when conduction inside a capsule is fast compared with
heat transfer at its surface, that is when the capsule's Biot number, $\mathrm{Bi} = h_c R / k$,
is small. `"lumped with Jeffreson"` puts part of the neglected internal resistance back,
through an effective coefficient $h_\mathrm{eff} = h_c / (1 + \mathrm{Bi} / 5)$
({class}`~pytes.submodels.Jeffreson`), with $k$ the conductivity at the capsule's enthalpy.
The correction is exact for slow changes in a sensible sphere, and an approximation while
the PCM melts or freezes.

## Options

| Option | Values |
|---|---|
| `"storage along flow path"` | `"resolved"` (default), `"averaged"`: see [resolved or averaged](index.md#resolved-or-averaged-along-the-flow-path) |
| `"storage element"` | `"resolved"` (default), `"lumped"`, `"lumped with Jeffreson"` |
| `"heat transfer coefficient"` | `"constant"` (default), `"Wakao-Kaguei"`: $\mathrm{Nu} = 2 + 1.1\, \mathrm{Re}^{0.6} \mathrm{Pr}^{1/3}$ ({class}`~pytes.submodels.WakaoKaguei`), with $\ell = 2 R$ and the superficial velocity in $\mathrm{Re}$ |

The options combine: an averaged bed of lumped capsules is one well-mixed capsule for the
whole bed. In this family, the cross-section averages along the bed (such as
`"Storage cross-section average temperature [K]"`) are the volume averages over a capsule.
The model also gives the device totals per unit cross-sectional area of the bed, such as
`"Power per unit area [W.m-2]"`. The averaged bed is the reduced model of the
[encapsulated-LTES](https://github.com/mmsg-warwick/encapsulated-LTES) repository.

## Parameter sets

The default parameter values are the experiments of
[Nallusamy et al. (2007)](https://doi.org/10.1016/j.renene.2006.04.015): a 47 l tank of
paraffin capsules, charged with water at 70 °C. A second set, `"Raul2018"`, gives the
experiments of [Raul et al. (2018)](https://doi.org/10.1016/j.applthermaleng.2018.07.123),
with a heat transfer oil at 180 °C. See {mod}`pytes.parameter_layers`.

## Examples

- [Tutorial 3: packed-bed models](../examples/getting_started/tutorial_3_packed_bed_models.ipynb)
- [Packed-bed model](../examples/packed_bed_models.ipynb), against the measurements of
  Nallusamy et al. (2007)
- [Lumped capsule](../examples/lumped_capsule.ipynb)
- [Validation](../examples/validation.ipynb), against Schumann's analytical solution
