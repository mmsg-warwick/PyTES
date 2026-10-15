"""
PyTES: models and tools for heat batteries (thermal energy storage), built on PyBaMM.

- Models (strict): :mod:`pytes.models`, by family. Each is a fixed composition of
  submodels, listed in ``model.submodels``.
- Toolkit (permissive): materials (:mod:`pytes.materials`), fluids (:mod:`pytes.fluids`),
  experiments (:mod:`pytes.experiments`), post-processing (:mod:`pytes.postprocessing`)
  and the conformance checks (:mod:`pytes.conformance`).
"""

from . import (
    compat,
    experiments,
    fluids,
    materials,
    models,
    parameters,
    postprocessing,
    submodels,
    variables,
)
from .models import BaseModel, ComposedModel, WiringError
from .models.finned_tube import MushModel, SharpFrontModel
from .models.packed_bed import PackedBedModel
from .postprocessing import energy_between

__all__ = [
    "BaseModel",
    "ComposedModel",
    "MushModel",
    "PackedBedModel",
    "SharpFrontModel",
    "WiringError",
    "energy_between",
    "compat",
    "experiments",
    "fluids",
    "materials",
    "models",
    "parameters",
    "postprocessing",
    "submodels",
    "variables",
]
