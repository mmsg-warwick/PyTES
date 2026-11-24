"""
The models, heat transfer correlations and analytical solutions register the references
they are built on with pybamm.citations
"""

import pybamm
import pytest

import pytes

pytest.importorskip("pybtex")

REFERENCES = {
    "BrosaPlanella2025": "A simple model for latent thermal energy storage",
    "Ismail2002": "spherical capsules packed bed latent heat storage",
    "Luckins2025": "Homogenized models for composite phase-change materials",
    "Gnielinski2013": "On heat transfer in tubes",
    "Wakao1979": "particle-to-fluid heat transfer coefficients",
    "Jeffreson1972": "Prediction of breakthrough curves in packed beds",
    "Schumann1929": "a liquid flowing through a porous prism",
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


def packed_bed(**options):
    return lambda: pytes.PackedBedModel(options=options)


@pytest.mark.parametrize(
    "create, cited",
    [
        (pytes.SharpFrontModel, {"Luckins2025"}),
        (pytes.MushModel, {"Luckins2025"}),
        (
            lambda: pytes.SharpFrontModel(
                options={"heat transfer coefficient": "Gnielinski"}
            ),
            {"Luckins2025", "Gnielinski2013"},
        ),
        (pytes.PackedBedModel, {"BrosaPlanella2025", "Ismail2002"}),
        (packed_bed(**{"storage element": "lumped"}), {"BrosaPlanella2025"}),
        (
            packed_bed(**{"storage element": "lumped with Jeffreson"}),
            {"BrosaPlanella2025", "Jeffreson1972"},
        ),
        (
            packed_bed(**{"storage along flow path": "averaged"}),
            {"BrosaPlanella2025"},
        ),
        (
            packed_bed(**{"heat transfer coefficient": "Wakao-Kaguei"}),
            {"BrosaPlanella2025", "Ismail2002", "Wakao1979"},
        ),
        (lambda: pytes.validation.schumann(1.0, 1.0), {"Schumann1929"}),
    ],
    ids=[
        "sharp front",
        "mush",
        "Gnielinski",
        "packed bed",
        "lumped capsule",
        "Jeffreson",
        "averaged bed",
        "Wakao-Kaguei",
        "Schumann",
    ],
)
def test_registers_its_references(create, cited, printed):
    create()
    text = printed()
    for key, title in REFERENCES.items():
        assert (title in text) == (key in cited), key
