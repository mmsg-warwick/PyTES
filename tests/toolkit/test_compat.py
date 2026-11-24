"""
The shim registry (DESIGN D16): every workaround is registered, each detects its upstream
fix, and a shim is flagged for removal once the oldest supported PyBaMM has the fix.
"""

import importlib
import pkgutil
import re
import tomllib
from pathlib import Path

import pybamm
import pytest
from packaging.version import Version

import pytes
from pytes import compat

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def pybamm_floor():
    """The oldest PyBaMM release PyTES supports, from ``pyproject.toml``"""
    dependencies = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    (floor,) = [
        match.group(1)
        for dependency in dependencies
        if (match := re.fullmatch(r"pybamm>=([\d.]+)", dependency.replace(" ", "")))
    ]
    return Version(floor)


def installed_release():
    """The installed PyBaMM release, or None for a development version (e.g. main)"""
    version = Version(pybamm.__version__)
    return None if version.is_devrelease or version.local else version


def test_every_compat_module_is_registered():
    modules = {
        info.name for info in pkgutil.iter_modules(compat.__path__) if not info.ispkg
    }
    assert modules == set(compat.SHIMS)
    for name in modules:
        docstring = importlib.import_module(f"pytes.compat.{name}").__doc__
        assert "Upstream:" in docstring and "Remove when:" in docstring, name


@pytest.mark.parametrize("shim", compat.SHIMS.values(), ids=lambda shim: shim.module)
def test_shim_is_removed_once_the_floor_has_the_fix(shim):
    if shim.fixed_in is None:
        pytest.skip("not fixed upstream yet")
    assert pybamm_floor() < Version(shim.fixed_in), (
        f"The PyBaMM floor {pybamm_floor()} has the fix for pytes.compat.{shim.module} "
        f"({shim.upstream}, fixed in {shim.fixed_in}): remove the shim"
    )


@pytest.mark.parametrize("shim", compat.SHIMS.values(), ids=lambda shim: shim.module)
def test_shim_detects_the_fix_of_the_installed_release(shim):
    # On a release, detection must agree with the release that fixes the issue: a probe
    # that stops detecting the fix would silently keep the workaround forever
    release = installed_release()
    if shim.has_fix is None or shim.fixed_in is None or release is None:
        pytest.skip("nothing to compare")
    assert shim.has_fix() == (release >= Version(shim.fixed_in))


@pytest.mark.parametrize("fallback", [False, True], ids=["installed", "fallback"])
def test_parameter_set_citations_are_printed(fallback, monkeypatch, tmp_path):
    # Both paths of the citations shim: the installed PyBaMM's own (read_citations on 26.11
    # and later), and the fallback through Citations._add_citation (older releases)
    pytest.importorskip("pybtex")
    if fallback:
        monkeypatch.setattr(compat.citations, "reads_citation_files", lambda: False)
    pybamm.citations._reset()
    pybamm.ParameterValues({"citations": ["Raul2018"]})  # known: loaded on import
    pybamm.ParameterValues({"citations": ["Nallusamy2007"]})
    compat.add_citation_database()  # loading again changes nothing
    filename = tmp_path / "citations.txt"
    pybamm.print_citations(filename)
    text = filename.read_text()
    assert "Raul" in text and "Nallusamy" in text
    pybamm.citations._reset()


def test_citation_keys_of_the_parameter_sets_are_in_the_database():
    keys = set(
        re.findall(r"@\w+\{([^,]+),", compat.citations.CITATIONS_FILE.read_text())
    )
    cited = set()
    for name in pytes.parameter_layers.SETS:
        cited |= set(pytes.parameter_layers.compose_set(name)["citations"])
    assert cited and cited <= keys
