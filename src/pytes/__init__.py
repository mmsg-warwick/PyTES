"""
PyTES: models and tools for heat batteries (thermal energy storage), built on PyBaMM.

- Models (strict): :mod:`pytes.models`, by family. Each is a fixed composition of
  submodels, listed in ``model.submodels``.
- Toolkit (permissive): materials (:mod:`pytes.materials`), fluids (:mod:`pytes.fluids`),
  experiments (:mod:`pytes.experiments`) and the conformance checks
  (:mod:`pytes.conformance`).
"""

from . import (
    compat,
    experiments,
    fluids,
    materials,
    models,
    parameters,
    submodels,
    variables,
)
from .models import BaseModel, WiringError
from .models.finned_pipe import MushModel, SharpFrontModel

__all__ = [
    "BaseModel",
    "MushModel",
    "SharpFrontModel",
    "WiringError",
    "compat",
    "experiments",
    "fluids",
    "materials",
    "models",
    "parameters",
    "submodels",
    "variables",
]
