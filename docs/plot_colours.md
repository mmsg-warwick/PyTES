# Plot colours

PyTES has its own colours for plots: two colour cycles, for lines on light and on dark
backgrounds, and two colourmaps, for fields such as a temperature over time and distance.
All of them lead with the PyTES orange and stay readable for people with colour-vision
deficiency (colour blindness).

They are available now but are **not yet the default**: a plot uses matplotlib's colours
(or PyBaMM's, in {class}`pybamm.QuickPlot`) until you ask for these. See
[Why they are not the default yet](#why-they-are-not-the-default-yet).

## Using them

```python
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

import pytes.plotting  # registers the colourmaps with matplotlib

plt.style.use("pytes.thermal")  # the colour cycle for every figure from now on

with plt.style.context(["dark_background", "pytes.thermal_dark"]):
    ...  # a figure for a dark background

ax.pcolormesh(t, z, T, cmap="pytes.ember")
ax.pcolormesh(t, z, T, cmap="pytes.thaw", norm=TwoSlopeNorm(vcenter=T_melt))
```

The colours are also {data}`pytes.plotting.THERMAL` and
{data}`pytes.plotting.THERMAL_DARK`, for example to pass to
`pybamm.QuickPlot(solution, colors=list(pytes.plotting.THERMAL))`. Each colourmap has a
reversed version, `"pytes.ember_r"` and `"pytes.thaw_r"`. The
[Plot colours](examples/plot_colours.ipynb) notebook shows all four on a packed bed
charge. The styles need matplotlib 3.7 or later, which the `plot` extra installs.

## Colour cycles

**PyTES Thermal**, for light backgrounds (style `"pytes.thermal"`). Each colour is shown
with its contrast against white:

<div class="pytes-swatches" role="img" aria-label="The 7 colours, in order">
<div class="pytes-swatch"><span style="background:#E8590C"></span><code>#E8590C</code><span>1. ember, 3.6:1</span></div>
<div class="pytes-swatch"><span style="background:#1F4E9C"></span><code>#1F4E9C</code><span>2. deep blue, 8.0:1</span></div>
<div class="pytes-swatch"><span style="background:#14A08A"></span><code>#14A08A</code><span>3. teal, 3.3:1</span></div>
<div class="pytes-swatch"><span style="background:#F0A930"></span><code>#F0A930</code><span>4. amber, 2.0:1</span></div>
<div class="pytes-swatch"><span style="background:#A23B72"></span><code>#A23B72</code><span>5. berry, 6.2:1</span></div>
<div class="pytes-swatch"><span style="background:#88C7F0"></span><code>#88C7F0</code><span>6. powder, 1.8:1</span></div>
<div class="pytes-swatch"><span style="background:#36312E"></span><code>#36312E</code><span>7. charcoal, 12.8:1</span></div>
</div>

**PyTES Thermal (dark)**, for dark backgrounds (style `"pytes.thermal_dark"`), with its
contrast against the documentation's dark background:

<div class="pytes-swatches on-dark" role="img" aria-label="The 7 colours, in order">
<div class="pytes-swatch"><span style="background:#F76707"></span><code>#F76707</code><span>1. ember, 5.8:1</span></div>
<div class="pytes-swatch"><span style="background:#6785F9"></span><code>#6785F9</code><span>2. blue, 5.3:1</span></div>
<div class="pytes-swatch"><span style="background:#04B68B"></span><code>#04B68B</code><span>3. teal, 6.8:1</span></div>
<div class="pytes-swatch"><span style="background:#FFC66C"></span><code>#FFC66C</code><span>4. amber, 11.5:1</span></div>
<div class="pytes-swatch"><span style="background:#B06C99"></span><code>#B06C99</code><span>5. mauve, 4.6:1</span></div>
<div class="pytes-swatch"><span style="background:#B2D5F8"></span><code>#B2D5F8</code><span>6. powder, 11.7:1</span></div>
<div class="pytes-swatch"><span style="background:#D9D0C7"></span><code>#D9D0C7</code><span>7. warm grey, 11.7:1</span></div>
</div>

### Why these colours

**Hot first, then cold.** The cycle starts with the PyTES orange and a deep blue, so a plot
of two lines, such as charge against discharge or inlet against outlet, reads as hot
against cold. Blue against orange is also the pair of colours that every kind of
colour-vision deficiency keeps apart.

**Readable with colour-vision deficiency.** About 1 man in 12 and 1 woman in 200 has some
form of colour-vision deficiency, mostly red-green. The colours were chosen by simulating
the three kinds of dichromacy (protanopia, deuteranopia and tritanopia, at full severity,
following Machado et al., 2009) and measuring how far apart each pair of colours stays,
in CIEDE2000, the standard measure of perceived colour difference. A palette scores the
distance of its closest pair, in the worst of the four visions (typical vision included).
Above about 10, colours are easy to tell apart; below 5, lines merge.

| Palette | Closest pair, all 7 colours | Closest pair, first 4 |
|---|---|---|
| **PyTES Thermal** | **10.1** | **12.4** |
| Okabe–Ito, with the PyTES orange first | 9.9 | 9.9 |
| Paul Tol's "vibrant", orange first | 8.6 | 8.6 |
| Open Color shades (the logo's palette) | 7.7 | 14.6 |
| matplotlib's default, `tab10` | 1.3 | 1.3 |

Okabe–Ito and Tol's schemes are the best-known colour-blind-safe palettes; PyTES Thermal
is as robust while keeping the PyTES orange and a more modern look. In `tab10`, the second
and third colours, orange and green, look almost the same to a protanope.

**Known limits.** The closest pair is berry and deep blue, for protan vision: every lighter
or pinker berry tried came closer to the teal for deutan vision instead. Powder blue has
only 1.8:1 contrast on white, so it suits fills and reference lines better than thin data
lines. With more than about six lines, add line styles or markers as well as colours.

**The dark twin** keeps the same hues in the same order, each made lighter for a dark
background while keeping most of its saturation, so that it looks like the same palette
rather than a pastel one. Charcoal becomes a light warm grey. Its closest pair is 13.3,
and every colour has at least 4.6:1 contrast on the documentation's dark background
(5.5:1 on black).

## Colourmaps

**ember**, sequential (`"pytes.ember"`), for a quantity from low to high:

<div class="pytes-colourmap" style="background:linear-gradient(90deg, #35130E, #491711, #5D1A12, #731E12, #892211, #A02910, #B6340D, #CB410B, #DF510C, #F0620F, #FC781F, #FD8F3E, #FDA559, #FDBA75, #FECE94, #FEE0B4, #FFEFD6)" role="img" aria-label="The ember colourmap"></div>
<div class="pytes-colourmap-ends"><span>low</span><span>high</span></div>

**thaw**, diverging (`"pytes.thaw"`), for a quantity above and below a reference:

<div class="pytes-colourmap" style="background:linear-gradient(90deg, #11198C, #164393, #285FB9, #2575F6, #5B94F9, #8AB0FB, #B5CBFD, #D8DEF2, #F2EDEB, #F4D3BA, #FBB280, #FD8B46, #EE6011, #C74109, #9F2604, #741A0A, #4C160E)" role="img" aria-label="The thaw colourmap"></div>
<div class="pytes-colourmap-ends"><span>below the reference</span><span>above the reference</span></div>

### Why perceptually uniform

A colourmap turns numbers into colours, and the eye reads changes in colour as changes in
the numbers. In a *perceptually uniform* colourmap, equal steps in the data look like equal
steps in colour, and lightness changes steadily from one end to the other. Rainbow maps
such as `jet` do neither: their lightness rises and falls, which draws edges in the data
that are not there and hides real ones, and they lose their order for colour-blind readers
and in greyscale print.

Both PyTES colourmaps are built in CAM02-UCS, the colour space in which matplotlib's
viridis and inferno were designed. Lightness changes linearly, hue and saturation follow
smooth curves through anchor colours, and the result is resampled so that neighbouring
colours are the same perceptual distance apart everywhere along the map.

### ember

Ember runs from a dark brown close to the ink of the PyTES wordmark, through the PyTES
orange, to cream. Its lightness rises monotonically, the perceptual step between
neighbouring colours varies by 0.013 %, and the map passes through the PyTES orange itself.
No published colourmap is both uniform and orange throughout:

| Colourmap | Lightness | Step size varies by | Closest to the PyTES orange |
|---|---|---|---|
| **ember** | rises steadily | **0.013 %** | **0.2** |
| inferno (matplotlib) | rises steadily | 1.1 % | 3.5 |
| solar (cmocean) | rises steadily | 0.0 % | 13.6 |
| lajolla (Crameri) | rises steadily | 14 % | 9.6 |
| YlOrBr (matplotlib) | rises steadily | 22 % | 3.4 |
| jet (matplotlib) | rises and falls | 43 % | 5.3 |

The last column is the CAM02-UCS distance from the map to the PyTES orange. Inferno is as
uniform as ember, but its dark half is black and purple.

### thaw

Thaw is diverging: dark navy, through the deep blue of the colour cycle, to a near-white
centre, then through the PyTES orange to a dark red-brown. It is meant for a field
centred on a reference value, such as the phase-change temperature, so that the pale band
marks the melting front, with colder fluid in blue and hotter in orange. Centre it with
matplotlib's {class}`~matplotlib.colors.TwoSlopeNorm`, as above.

Its lightness falls steadily from the centre to both ends, and colours equally far from
the centre match in lightness to within 2.4 CAM02-UCS units, so neither side looks
stronger. The step size varies by 2.8 %, as the blue half is 5 % shorter: blue reaches the
edge of the colours a screen can show. Beyond the pale centre, where the two sides meet, colours equally far either side stay
at least 19.6 units apart for every kind of colour-vision deficiency, so the two sides are
never confused. Among published maps, cmocean's `balance` is as uniform but runs from blue
to red, Crameri's `vik` has the right hues but lightness that does not change steadily, and
matplotlib's `coolwarm`, `RdBu` and `PuOr` vary in step size by 19 % to 23 %.

The colourmaps need no dark twin: a colourmap fills its axes, whatever the background.

## Why they are not the default yet

PyTES models are PyBaMM models, and most of their plots come from PyBaMM's
{class}`pybamm.QuickPlot` (and so `Simulation.plot`), which today uses its own colours
whatever matplotlib's colour cycle is. Making the PyTES colours the default would mean
changing matplotlib's global settings when PyTES is imported, which would also restyle
every other figure in the session. Instead, PyTES will make them the default for its own
models once PyBaMM lets a package set the default style of its models' plots. Your own
matplotlib settings will still take precedence. Progress is tracked in
[issue #43](https://github.com/mmsg-warwick/PyTES/issues/43).

## Reproducing the colours

The colourmap values are in `src/pytes/colourmaps/`, generated by
[`docs/design/colours/make_colourmaps.py`](https://github.com/mmsg-warwick/PyTES/blob/main/docs/design/colours/make_colourmaps.py),
which documents each step. The decisions are recorded in
[DESIGN D15](design/DESIGN.md#d15-kpis-and-standard-plots-live-in-the-toolkit).
