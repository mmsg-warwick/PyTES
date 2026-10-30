"""
Build the SVG model diagrams from their TikZ sources.

Each ``<name>.tex`` in this folder (other than the shared preamble) is compiled with
``latex`` and converted with ``dvisvgm`` to ``<name>.svg`` next to it, with the text turned
into paths so that the SVGs need no fonts. The SVGs are committed, so the documentation
builds without TeX; rebuild them after changing a source::

    python docs/models/diagrams/build.py            # every diagram
    python docs/models/diagrams/build.py capsule    # only some

Needs a TeX distribution with TikZ and the standalone class, and dvisvgm (on Debian or
Ubuntu: ``texlive-pictures texlive-latex-extra dvisvgm``).
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PREAMBLE = "pytes-diagrams.tex"


def build(source):
    """Compile one TikZ source to an SVG next to it"""
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(HERE / PREAMBLE, tmp)
        shutil.copy(source, tmp)
        result = subprocess.run(
            ["latex", "-interaction=nonstopmode", "-halt-on-error", source.name],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.exit(f"{source.name}: latex failed\n{result.stdout[-2000:]}")
        dvi = Path(tmp) / source.with_suffix(".dvi").name
        svg = source.with_suffix(".svg")
        subprocess.run(
            [
                "dvisvgm",
                "--no-fonts",
                "--exact-bbox",
                "--optimize",
                str(dvi),
                "-o",
                str(svg),
            ],
            check=True,
            capture_output=True,
        )
    print(f"built {svg.relative_to(HERE)}")


def main(names):
    sources = sorted(p for p in HERE.glob("*.tex") if p.name != PREAMBLE)
    if names:
        sources = [p for p in sources if p.stem in names]
    for source in sources:
        build(source)


if __name__ == "__main__":
    main(sys.argv[1:])
