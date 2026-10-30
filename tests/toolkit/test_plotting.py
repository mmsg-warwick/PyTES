"""Standard plots and plot colours (DESIGN D15)."""

import subprocess
import sys

import matplotlib
import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes import plotting

matplotlib.use("Agg")


@pytest.fixture(scope="module")
def solutions():
    out = []
    for cls in (pytes.SharpFrontModel, pytes.PackedBedModel):
        model = cls()
        out.append(
            pybamm.Simulation(model, var_pts=var_pts(model)).solve(
                [0, 1800], t_interp=np.linspace(0, 1800, 31)
            )
        )
    return out


def test_summary(solutions):
    fig, axes = plotting.plot_summary(solutions)
    assert len(axes) == 3
    assert len(axes[0].lines) == 4  # outlet and inlet for each solution
    assert len(axes[1].lines) == len(axes[2].lines) == 2
    matplotlib.pyplot.close(fig)


def test_summary_of_one_solution(solutions):
    fig, axes = plotting.plot_summary(solutions[0], labels=["sharp front"])
    assert axes[1].lines[0].get_label() == "sharp front"
    matplotlib.pyplot.close(fig)


def test_power_against_energy(solutions):
    fig, ax = plotting.plot_power_against_energy(solutions, labels=["a", "b"])
    x, y = ax.lines[0].get_data()
    np.testing.assert_allclose(x, solutions[0]["Discharged energy [kWh]"].entries)
    np.testing.assert_allclose(y, solutions[0]["Power [kW]"].entries)
    matplotlib.pyplot.close(fig)


def test_fluid_profiles(solutions):
    fig, ax = plotting.plot_fluid_profiles(solutions[1], times=[0, 600, 1800])
    assert len(ax.lines) == 3
    # Uniform at the initial temperature, 32 degC
    np.testing.assert_allclose(ax.lines[0].get_data()[1], 32)
    matplotlib.pyplot.close(fig)


def test_labels_must_match():
    with pytest.raises(ValueError, match="2 labels for 1 solutions"):
        plotting._as_list(object(), ["a", "b"])


def test_power_and_energy_axes_include_zero_with_room_above(solutions):
    # A power held constant must show as a line at its value, not as solver noise around
    # an offset, nor on the edge of the axes
    fig, axes = plotting.plot_summary(solutions)
    for ax in axes[1:]:
        low, high = ax.get_ylim()
        assert low <= 0 < max(line.get_ydata().max() for line in ax.lines) < high
        assert not ax.yaxis.get_major_formatter().get_useOffset()
    matplotlib.pyplot.close(fig)


def _lightness(rgb):
    """CIELAB lightness L* of sRGB colours in [0, 1]"""
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    Y = linear @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 216 / 24389, 116 * np.cbrt(Y) - 16, 24389 / 27 * Y)


@pytest.mark.parametrize(
    ("style", "colours"),
    [
        ("pytes.thermal", plotting.THERMAL),
        ("pytes.thermal_dark", plotting.THERMAL_DARK),
    ],
)
def test_colour_cycle_styles(style, colours):
    # The style sheets shipped in the package hold the same colours as the constants
    with matplotlib.pyplot.style.context(style):
        cycle = matplotlib.rcParams["axes.prop_cycle"].by_key()["color"]
    assert [matplotlib.colors.to_hex(c).upper() for c in cycle] == list(colours)


def test_colours_are_not_the_default():
    # Importing pytes.plotting registers names only: matplotlib's defaults are unchanged
    default = matplotlib.rcParamsDefault["axes.prop_cycle"]
    assert matplotlib.rcParams["axes.prop_cycle"] == default


@pytest.mark.parametrize("name", plotting.COLOURMAPS)
def test_colourmaps_are_registered(name):
    colourmap = matplotlib.colormaps[name]
    assert colourmap.N == 256
    reversed_colourmap = matplotlib.colormaps[f"{name}_r"]
    np.testing.assert_array_equal(reversed_colourmap(0.0), colourmap(1.0))
    plotting.register_colourmaps()  # again: no error, same map
    assert matplotlib.colormaps[name] == colourmap


def test_ember_lightness_rises_through_the_brand_orange():
    rgb = matplotlib.colormaps["pytes.ember"](np.linspace(0, 1, 256))[:, :3]
    assert np.all(np.diff(_lightness(rgb)) > 0)
    brand = matplotlib.colors.to_rgb(plotting.THERMAL[0])
    assert np.min(np.linalg.norm(rgb - brand, axis=1)) < 0.01


def test_thaw_lightness_peaks_at_the_centre():
    # Lightest in the middle and falling steadily to both ends, about symmetrically. The map
    # is symmetric to 2.4 in CAM02-UCS lightness J' (make_colourmaps.py); CIELAB L*, used
    # here to avoid a colorspacious dependency, rates the saturated orange half lighter
    L = _lightness(matplotlib.colormaps["pytes.thaw"](np.linspace(0, 1, 256))[:, :3])
    assert np.all(np.diff(L[:128]) > 0)
    assert np.all(np.diff(L[128:]) < 0)
    assert np.max(np.abs(L - L[::-1])) < 6.5


def test_import_pytes_does_not_import_matplotlib():
    code = "import sys, pytes; assert 'matplotlib' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True)
