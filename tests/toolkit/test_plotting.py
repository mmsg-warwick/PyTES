"""Standard plots (DESIGN D15): they work for every model and for comparisons."""

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
