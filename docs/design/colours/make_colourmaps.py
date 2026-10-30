#
# Generate the PyTES colourmaps
#
"""
Generate the PyTES colourmaps (DESIGN D15) as 256 sRGB triplets in [0, 1] each, into
``src/pytes/colourmaps/``, from where :mod:`pytes.plotting` registers them with matplotlib:

- ``ember.csv``, sequential: from a dark brown near the "TES" ink of the wordmark
  (#3A1A0A), through the brand orange (#E8590C), to cream.
- ``thaw.csv``, diverging: from dark navy, through the deep blue of the colour cycle
  (#1F4E9C), to a near-white centre, then through the brand orange to dark red-brown. Meant
  to be centred on a reference value such as the phase-change temperature.

The values are kept as floats, as matplotlib keeps its own maps: rounding to 8-bit hex adds
noise of the size of the steps between neighbouring colours.

Both are built in CAM02-UCS, the colour space of viridis and inferno. Each path (a whole map
for ember, each half for thaw) is built the same way:

1. Lightness J' runs linearly between its ends. Hue and chroma are monotone cubic (PCHIP)
   curves of J' through keys, one of them an anchor colour at its own lightness.
2. Chroma is capped at 97 % of the largest value in the sRGB gamut, then smoothed, so the
   path never leaves the gamut.
3. The path is resampled at equal arc length, so neighbouring colours are the same
   perceptual distance apart along it.

Measured on the results:

- ember: lightness rises monotonically, the step size varies by under 0.1 %, lightness
  stays within 5 J' of a straight line, and the map passes within 0.22 CAM02-UCS units of
  the brand orange.
- thaw: lightness falls monotonically from the centre (J' 95) to both ends (J' 20), and
  colours at the same distance from the centre differ in lightness by at most 2.4 J'. The
  step size varies by 2.8 %, as the blue half is 5 % shorter than the orange half (blue
  reaches the edge of the sRGB gamut). It passes within 0.2 units of both anchors.

Run from the repository root (colorspacious is not a PyTES dependency)::

    uv run --with colorspacious python docs/design/colours/make_colourmaps.py
"""

from pathlib import Path

import numpy as np
from colorspacious import cspace_convert
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d

BRAND_ORANGE = "#E8590C"
DEEP_BLUE = "#1F4E9C"
N_COLOURS = 256


def hex_to_rgb(colour):
    return np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)]) / 255


def lightness_chroma_hue(colour):
    J, a, b = cspace_convert(hex_to_rgb(colour), "sRGB1", "CAM02-UCS")
    return J, np.hypot(a, b), np.degrees(np.arctan2(b, a))


def in_gamut(jab):
    rgb = cspace_convert(jab, "CAM02-UCS", "sRGB1")
    return np.all((rgb >= -1e-4) & (rgb <= 1 + 1e-4))


def max_chroma(lightness, hue):
    """Largest chroma in the sRGB gamut at this lightness and hue, by bisection."""
    low, high = 0.0, 80.0
    direction = np.array([np.cos(np.radians(hue)), np.sin(np.radians(hue))])
    for _ in range(30):
        mid = (low + high) / 2
        if in_gamut(np.r_[lightness, mid * direction]):
            low = mid
        else:
            high = mid
    return low


def path(J_start, J_end, hue_keys, chroma_keys, n):
    """
    ``n`` colours, as J'a'b', from lightness ``J_start`` to ``J_end`` at equal arc length.

    ``hue_keys`` and ``chroma_keys`` are (J', value) pairs, hue in degrees.
    """
    J = np.linspace(J_start, J_end, 1024)
    hue = PchipInterpolator(*zip(*sorted(hue_keys), strict=True))(J)
    chroma = PchipInterpolator(*zip(*sorted(chroma_keys), strict=True))(J)

    cap = 0.97 * np.array([max_chroma(j, h) for j, h in zip(J, hue, strict=True)])
    chroma = np.minimum(
        gaussian_filter1d(np.minimum(chroma, cap), 6, mode="nearest"), cap
    )
    jab = np.c_[J, chroma * np.cos(np.radians(hue)), chroma * np.sin(np.radians(hue))]

    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(jab, axis=0), axis=1))]
    s = np.linspace(0, arc[-1], n)
    return np.column_stack([np.interp(s, arc, jab[:, i]) for i in range(3)])


def to_rgb(jab):
    return np.clip(cspace_convert(jab, "CAM02-UCS", "sRGB1"), 0, 1)


def ember(n=N_COLOURS):
    J_o, C_o, h_o = lightness_chroma_hue(BRAND_ORANGE)
    return to_rgb(
        path(
            15.0,
            96.0,
            hue_keys=[(15.0, 30.0), (J_o, h_o), (96.0, 80.0)],
            chroma_keys=[(15.0, 14.0), (J_o, C_o), (96.0, 12.0)],
            n=n,
        )
    )


def thaw(n=N_COLOURS):
    J_centre, J_end = 95.0, 20.0
    J_o, C_o, h_o = lightness_chroma_hue(BRAND_ORANGE)
    J_b, C_b, h_b = lightness_chroma_hue(DEEP_BLUE)
    orange = path(
        J_centre,
        J_end,
        hue_keys=[(J_centre, 62.0), (J_o, h_o), (J_end, 32.0)],
        chroma_keys=[(J_centre, 0.0), (J_o, C_o), (J_end, 20.0)],
        n=n // 2,
    )
    # the blue keeps more chroma at the orange anchor's lightness, so that both halves
    # are about as long and the steps about equal across the centre
    blue = path(
        J_centre,
        J_end,
        hue_keys=[(J_centre, h_b + 5), (J_b, h_b), (J_end, -98.0)],
        chroma_keys=[(J_centre, 0.0), (J_o, 40.0), (J_b, C_b), (J_end, 30.0)],
        n=n // 2,
    )
    return to_rgb(np.vstack([blue[::-1], orange]))


OUTPUT = Path(__file__).parents[3] / "src" / "pytes" / "colourmaps"

if __name__ == "__main__":
    for name, rgb in {"ember": ember(), "thaw": thaw()}.items():
        file = OUTPUT / f"{name}.csv"
        lines = [", ".join(f"{c:.6f}" for c in colour) for colour in rgb]
        file.write_text("red, green, blue\n" + "\n".join(lines) + "\n")
        print(f"wrote {len(lines)} colours to {file}")
