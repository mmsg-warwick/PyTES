import pytest

import pytes

#: Every admitted model. The conformance suite runs over all of them.
MODELS = [pytes.SharpFrontModel, pytes.MushModel, pytes.PackedBedModel]

#: A coarse mesh for fast tests, by spatial variable name
COARSE_MESH = {"r": 5, "x": 5, "y": 6, "z": 10}


def var_pts(model, mesh=None):
    """A mesh keyed by the model's own spatial variables"""
    mesh = COARSE_MESH if mesh is None else mesh
    return {getattr(model, k): n for k, n in mesh.items() if hasattr(model, k)}


@pytest.fixture(params=MODELS, ids=lambda cls: cls.__name__)
def model_class(request):
    return request.param
