import pytest

import pytes

#: Every admitted model class
MODEL_CLASSES = [pytes.SharpFrontModel, pytes.MushModel, pytes.PackedBedModel]


def _variant(model_class, options):
    """A factory of the model with the given options, named after them"""

    def make(**kwargs):
        return model_class(options=options, **kwargs)

    values = ",".join(options.values())
    make.__name__ = (
        f"{model_class.__name__}[{values}]" if values else model_class.__name__
    )
    return make


def _variants(model_class):
    """Every combination of the model's allowed options"""
    combinations = [{}]
    for key, values in model_class.allowed_options.items():
        combinations = [{**c, key: v} for c in combinations for v in values]
    return [_variant(model_class, options) for options in combinations]


#: Every admitted model, with every combination of its options (DESIGN D3). The
#: conformance suite runs over all of them.
MODELS = [variant for cls in MODEL_CLASSES for variant in _variants(cls)]

#: A coarse mesh for fast tests, by spatial variable name
COARSE_MESH = {"r": 5, "x": 5, "y": 6, "z": 10}


def var_pts(model, mesh=None):
    """A mesh keyed by the model's own spatial variables"""
    mesh = COARSE_MESH if mesh is None else mesh
    return {getattr(model, k): n for k, n in mesh.items() if hasattr(model, k)}


@pytest.fixture(params=MODELS, ids=lambda make: make.__name__)
def model_class(request):
    return request.param
