#
# Standard plots
#
"""
Standard plots (toolkit, DESIGN D15), for one solution or several to compare. They use only
the outputs every model provides, so they work for any model and family, and need the
``plot`` extra (matplotlib).

- :func:`plot_summary`: inlet and outlet temperature, power and discharged energy against
  time.
- :func:`plot_power_against_energy`: power against discharged energy, the key comparison
  plot.
- :func:`plot_fluid_profiles`: the fluid temperature along the flow path at given times.

Each returns the figure and its axes, for further styling.

The PyTES plot colours (DESIGN D15) are available, not yet the default:

- the colour cycles :data:`THERMAL` and :data:`THERMAL_DARK`, also as the matplotlib
  styles ``"pytes.thermal"`` and ``"pytes.thermal_dark"``
  (``plt.style.use("pytes.thermal")``);
- the colourmaps ``"pytes.ember"`` (sequential) and ``"pytes.thaw"`` (diverging), and their
  reversals ``"pytes.ember_r"`` and ``"pytes.thaw_r"``, registered with matplotlib when this
  module is imported (``cmap="pytes.ember"``).
"""

import importlib.resources

import numpy as np

#: The colour cycle "PyTES Thermal", for light backgrounds (style ``"pytes.thermal"``)
THERMAL = ("#E8590C", "#1F4E9C", "#14A08A", "#F0A930", "#A23B72", "#88C7F0", "#36312E")

#: The colour cycle "PyTES Thermal (dark)", for dark backgrounds (style
#: ``"pytes.thermal_dark"``)
THERMAL_DARK = (
    "#F76707",
    "#6785F9",
    "#04B68B",
    "#FFC66C",
    "#B06C99",
    "#B2D5F8",
    "#D9D0C7",
)

#: The colourmaps registered with matplotlib, each also reversed (name ending in ``_r``)
COLOURMAPS = ("pytes.ember", "pytes.thaw")


def register_colourmaps():
    """
    Register the PyTES colourmaps (:data:`COLOURMAPS`) and their reversals with matplotlib.

    Done when :mod:`pytes.plotting` is imported, if matplotlib is installed; registering
    again does nothing.
    """
    import matplotlib
    from matplotlib.colors import ListedColormap

    data = importlib.resources.files("pytes") / "colourmaps"
    for name in COLOURMAPS:
        if name in matplotlib.colormaps:
            continue
        with (data / f"{name.removeprefix('pytes.')}.csv").open() as file:
            colours = np.loadtxt(file, delimiter=",", skiprows=1)
        colourmap = ListedColormap(colours, name=name)
        matplotlib.colormaps.register(colourmap)
        matplotlib.colormaps.register(colourmap.reversed())


def _pyplot():
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise ImportError(
            "pytes.plotting needs matplotlib: install the plot extra, "
            "pip install 'pytes-thermal[plot]'"
        ) from error
    return plt


def _as_list(solutions, labels):
    """The solutions as a list, with a label for each (default: the model names)"""
    if not isinstance(solutions, list | tuple):
        solutions = [solutions]
    if labels is None:
        labels = [solution.all_models[0].name for solution in solutions]
    if len(labels) != len(solutions):
        raise ValueError(f"{len(labels)} labels for {len(solutions)} solutions")
    return list(solutions), list(labels)


def _from_zero(ax):
    """Scale the y axis to include zero, without an offset in the tick labels"""
    ax.ticklabel_format(axis="y", useOffset=False)
    low, high = ax.dataLim.intervaly
    low, high = min(low, 0), max(high, 0)
    margin = 0.05 * (high - low) or 1
    ax.set_ylim(low - margin if low < 0 else 0, high + margin if high > 0 else 0)


def plot_summary(solutions, labels=None):
    """
    Inlet and outlet temperature, power and discharged energy against time.

    Parameters
    ----------
    solutions : pybamm.Solution or list of them
        The solutions to plot.
    labels : list of str, optional
        A label for each solution (default: the model names).

    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : numpy.ndarray of matplotlib.axes.Axes
        Temperatures, power, and discharged energy.
    """
    plt = _pyplot()
    solutions, labels = _as_list(solutions, labels)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), layout="constrained")
    for solution, label in zip(solutions, labels, strict=True):
        t = solution["Time [h]"].entries
        (line,) = axes[0].plot(
            t, solution["Outlet temperature [degC]"].entries, label=f"{label}, outlet"
        )
        axes[0].plot(
            t,
            solution["Inlet temperature [degC]"].entries,
            "--",
            color=line.get_color(),
            label=f"{label}, inlet",
        )
        axes[1].plot(t, solution["Power [kW]"].entries, label=label)
        axes[2].plot(t, solution["Discharged energy [kWh]"].entries, label=label)
    for ax, ylabel in zip(
        axes,
        ["Temperature [°C]", "Power [kW]", "Discharged energy [kWh]"],
        strict=True,
    ):
        ax.set_xlabel("Time [h]")
        ax.set_ylabel(ylabel)
    # A held power is a flat line at its value, not solver noise around an offset
    for ax in axes[1:]:
        _from_zero(ax)
    axes[0].legend(fontsize="small")
    if len(solutions) > 1:
        axes[1].legend(fontsize="small")
    return fig, axes


def plot_power_against_energy(solutions, labels=None):
    """
    Power against discharged energy (DESIGN D15), the key comparison between designs: how
    the power a device delivers falls as it gives up its energy.

    Parameters
    ----------
    solutions : pybamm.Solution or list of them
        The solutions to plot.
    labels : list of str, optional
        A label for each solution (default: the model names).

    Returns
    -------
    fig : matplotlib.figure.Figure
    ax : matplotlib.axes.Axes
    """
    plt = _pyplot()
    solutions, labels = _as_list(solutions, labels)
    fig, ax = plt.subplots(figsize=(5, 3.5), layout="constrained")
    for solution, label in zip(solutions, labels, strict=True):
        ax.plot(
            solution["Discharged energy [kWh]"].entries,
            solution["Power [kW]"].entries,
            label=label,
        )
    ax.set_xlabel("Discharged energy [kWh]")
    ax.set_ylabel("Power [kW]")
    _from_zero(ax)
    ax.legend(fontsize="small")
    return fig, ax


def plot_fluid_profiles(solution, times, label=None):
    """
    The fluid temperature along the flow path at given times.

    Parameters
    ----------
    solution : pybamm.Solution
        The solution.
    times : list of float
        Times [s].
    label : str, optional
        Title of the plot (default: the model name).

    Returns
    -------
    fig : matplotlib.figure.Figure
    ax : matplotlib.axes.Axes
    """
    plt = _pyplot()
    fluid = solution["Heat transfer fluid temperature [degC]"]
    z = fluid.mesh.nodes
    fig, ax = plt.subplots(figsize=(5, 3.5), layout="constrained")
    for t in times:
        ax.plot(z, np.ravel(fluid(t=t, z=z)), label=f"{t / 60:g} min")
    ax.set_xlabel("Distance along the flow path [m]")
    ax.set_ylabel("Fluid temperature [°C]")
    ax.set_title(label or solution.all_models[0].name)
    ax.legend(fontsize="small")
    return fig, ax


try:
    import matplotlib  # noqa: F401
except ImportError:  # pragma: no cover - depends on the environment
    pass
else:
    register_colourmaps()
