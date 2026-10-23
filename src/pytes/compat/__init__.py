"""
Workarounds for PyBaMM behaviour that PyTES depends on.

Every workaround lives here, never in a model or submodel. Each one names the upstream issue
it works around and the condition under which it can be removed.
"""

from .advection import LimitedFiniteVolume, fluid_spatial_method
from .coupled import resolve_coupled_variables
from .solution import set_step_description
from .upwind import upwind_inlet_value

__all__ = [
    "LimitedFiniteVolume",
    "fluid_spatial_method",
    "resolve_coupled_variables",
    "set_step_description",
    "upwind_inlet_value",
]
