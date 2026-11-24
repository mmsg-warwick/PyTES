"""Each model registers the references it is built on with pybamm.citations"""

import pybamm
import pytest

import pytes

pytest.importorskip("pybtex")

REFERENCES = {
    "BrosaPlanella2025": "A simple model for latent thermal energy storage",
    "Ismail2002": "spherical capsules packed bed latent heat storage",
    "Luckins2025": "Homogenized models for composite phase-change materials",
}


@pytest.fixture
def printed(tmp_path):
    """The printed citations of what is created inside the test"""
    pybamm.citations._reset()

    def text():
        filename = tmp_path / "citations.txt"
        pybamm.print_citations(filename)
        return filename.read_text()

    yield text
    pybamm.citations._reset()


@pytest.mark.parametrize(
    "model, cited",
    [
        (pytes.SharpFrontModel, {"Luckins2025"}),
        (pytes.MushModel, {"Luckins2025"}),
        (pytes.PackedBedModel, {"BrosaPlanella2025", "Ismail2002"}),
        (
            lambda: pytes.PackedBedModel(options={"storage element": "lumped"}),
            {"BrosaPlanella2025"},
        ),
        (
            lambda: pytes.PackedBedModel(
                options={"storage along flow path": "averaged"}
            ),
            {"BrosaPlanella2025"},
        ),
    ],
    ids=["sharp front", "mush", "packed bed", "lumped capsule", "averaged bed"],
)
def test_model_registers_its_references(model, cited, printed):
    model()
    text = printed()
    for key, title in REFERENCES.items():
        assert (title in text) == (key in cited), key
