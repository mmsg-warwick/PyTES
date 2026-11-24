"""
Workarounds for PyBaMM behaviour that PyTES depends on.

Every workaround lives here, never in a model or submodel. Each one names the upstream issue
it works around and the condition under which it can be removed.

PyTES supports the PyBaMM releases of the last 3 months, so a shim stays until the oldest of
them has the fix (DESIGN D16). Meanwhile each shim detects the fix, by a new argument or a
tiny probe of the behaviour (never by the version number), and uses PyBaMM's code where it
exists, with the same results. :data:`SHIMS` records each one, with the release that fixes
it once known; a test fails when the PyBaMM floor in ``pyproject.toml`` reaches that
release, naming the shim to remove.
"""

from collections.abc import Callable
from dataclasses import dataclass

from .advection import LimitedFiniteVolume, fluid_spatial_method
from .citations import add_citation_database, reads_citation_files
from .coupled import resolve_coupled_variables
from .upwind import upwind_inlet_value, upwind_uses_boundary_value


@dataclass(frozen=True)
class Shim:
    """
    A workaround for a PyBaMM issue.

    Parameters
    ----------
    module : str
        The module of :mod:`pytes.compat` that holds it.
    upstream : str
        The upstream issues and pull requests.
    fixed_in : str or None
        The first PyBaMM release with the fix, or None if not fixed yet.
    has_fix : callable or None
        Returns whether the installed PyBaMM has the fix (the shim then defers to it), or
        None if the shim does not detect a fix yet.
    """

    module: str
    upstream: str
    fixed_in: str | None = None
    has_fix: Callable[[], bool] | None = None


#: Every shim in :mod:`pytes.compat`, by module name
SHIMS = {
    shim.module: shim
    for shim in [
        Shim(
            "upwind",
            "pybamm-team/PyBaMM#5860, PR #5861",
            fixed_in="26.11",
            has_fix=upwind_uses_boundary_value,
        ),
        Shim(
            "citations",
            "pybamm-team/PyBaMM#5950, PR #6003",
            fixed_in="26.11",
            has_fix=reads_citation_files,
        ),
        # Resolution is the default from 26.11 (PR #6002), but resolves to unprocessed
        # variables after parameter processing (not filed yet; draft in docs/upstream)
        Shim("coupled", "pybamm-team/PyBaMM#6001, PR #6002"),
        # No limited upwind scheme upstream yet (issue #7 here)
        Shim("advection", "pybamm-team/PyBaMM#3526, PR #3979"),
    ]
}

__all__ = [
    "SHIMS",
    "LimitedFiniteVolume",
    "Shim",
    "add_citation_database",
    "fluid_spatial_method",
    "reads_citation_files",
    "resolve_coupled_variables",
    "upwind_inlet_value",
    "upwind_uses_boundary_value",
]
