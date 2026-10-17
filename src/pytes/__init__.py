"""
PyTES: models and tools for heat batteries (thermal energy storage), built on PyBaMM.

- Models (strict): :mod:`pytes.models`, by family. Each is a fixed composition of
  submodels, listed in ``model.submodels``.
- Toolkit (permissive): materials (:mod:`pytes.materials`), fluids (:mod:`pytes.fluids`),
  experiments (:mod:`pytes.experiments`), post-processing (:mod:`pytes.postprocessing`),
  standard plots (:mod:`pytes.plotting`, with the ``plot`` extra),
  the conformance checks (:mod:`pytes.conformance`) and analytical solutions for validation
  (:mod:`pytes.validation`).
"""

from importlib.metadata import version as _version

from . import (
    compat,
    experiments,
    fluids,
    materials,
    models,
    parameters,
    postprocessing,
    submodels,
    validation,
    variables,
)
from .models import BaseModel, ComposedModel, OptionError, WiringError
from .models.finned_tube import MushModel, SharpFrontModel
from .models.packed_bed import PackedBedModel
from .postprocessing import energy_between

#: The installed version of PyTES
__version__ = _version("pytes")

__all__ = [
    "__version__",
    "BaseModel",
    "ComposedModel",
    "MushModel",
    "OptionError",
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
    "validation",
    "variables",
]
