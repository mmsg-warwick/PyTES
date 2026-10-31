"""
Sphinx configuration for the PyTES documentation (issue #4).

Build locally with::

    uv run --group docs sphinx-build -W --keep-going docs docs/_build/html
"""

import re
import shutil
import sys
from pathlib import Path

import pytes

DOCS = Path(__file__).parent
sys.path.insert(0, str(DOCS))

import parameter_values  # noqa: E402

ROOT = DOCS.parent

# -- Project ------------------------------------------------------------------------------

project = "PyTES"
author = "the PyTES developers"
copyright = "the PyTES developers"
release = pytes.__version__
version = release

# -- General ------------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "myst_nb",
    "sphinx_copybutton",
]

exclude_patterns = [
    "_build",
    # Private working notes (gitignored)
    "upstream",
    # Notes for whoever edits the logo, not part of the site
    "_static/LOGO-USAGE.md",
]

# British English (CLAUDE.md), also in the search index
language = "en_GB"

# -- Example notebooks --------------------------------------------------------------------

# The notebooks live in examples/, outside the documentation source, and are copied in at
# each build (the copies are gitignored). They are rendered from their committed outputs,
# never executed here: CI already runs them (nbmake)
_NOTEBOOKS = DOCS / "examples"
for _notebook in sorted((ROOT / "examples").glob("*.ipynb")):
    shutil.copy2(_notebook, _NOTEBOOKS / _notebook.name)

nb_execution_mode = "off"
myst_enable_extensions = ["dollarmath", "amsmath"]
# Anchors for the headings of Markdown pages (CONTRIBUTING.md links to its own sections)
myst_heading_anchors = 3

# -- Pages from the repository root -------------------------------------------------------

# The changelog and the contribution guide are written for GitHub, with links relative to
# the repository root. Their pages are generated at each build (and gitignored), with links
# to the design documents and to each other kept inside the site and the rest sent to GitHub
GITHUB = "https://github.com/mmsg-warwick/PyTES"
_PAGES = {"CHANGELOG.md": "changelog.md", "CONTRIBUTING.md": "contributing.md"}
_LINK = re.compile(r"\]\((?!https?:|#)([^)#]+)(#[^)]*)?\)")


def _site_link(match):
    path, anchor = match.group(1), match.group(2) or ""
    if path in _PAGES:
        return f"]({_PAGES[path]}{anchor})"
    if path.startswith("docs/design/") and path.endswith(".md"):
        return f"]({path.removeprefix('docs/')}{anchor})"
    kind = "blob" if (ROOT / path).is_file() else "tree"
    return f"]({GITHUB}/{kind}/main/{path}{anchor})"


for _source, _page in _PAGES.items():
    _text = (ROOT / _source).read_text(encoding="utf-8")
    (DOCS / _page).write_text(_LINK.sub(_site_link, _text), encoding="utf-8")

# -- Parameter values ---------------------------------------------------------------------

# Generated at each build (and gitignored) from the registered parameter layers and sets, so
# that the page shows the values the code holds
parameter_values.write(DOCS / "parameter_values.rst")

# -- API reference ------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_use_rtype = False
napoleon_preprocess_types = True
# Attributes sections as fields, so that they do not clash with documented properties
napoleon_use_ivar = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "pybamm": ("https://docs.pybamm.org/en/latest", None),
}

# -- HTML ---------------------------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = f"PyTES {release}"
html_static_path = ["_static"]
# The logo's colours
html_css_files = ["pytes.css"]
# A square of the colour before inline hex colours, such as `#E8590C`
html_js_files = ["colour-chips.js"]
html_favicon = "_static/favicon.svg"
html_theme_options = {
    "logo": {
        "image_light": "_static/pytes-logo-light.svg",
        "image_dark": "_static/pytes-logo-dark.svg",
        "alt_text": "PyTES",
    },
    "github_url": GITHUB,
    "icon_links": [
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/pytes-thermal/",
            "icon": "fa-brands fa-python",
        },
    ],
    "navbar_align": "left",
    "show_toc_level": 2,
}
html_context = {
    "github_user": "mmsg-warwick",
    "github_repo": "PyTES",
    "github_version": "main",
    "doc_path": "docs",
}
