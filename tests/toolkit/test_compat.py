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


# Each shim has two paths, and a given PyBaMM takes only one of them. The tests below force
# each path, so that both are tested (and covered) on any PyBaMM; the behaviour tests (e.g.
# energy conservation) check the path the installed PyBaMM takes.


@pytest.mark.parametrize("fixed", [True, False], ids=["fixed", "not fixed"])
def test_upwind_inlet_value_on_both_paths(fixed, monkeypatch):
    monkeypatch.setattr(compat.upwind, "upwind_uses_boundary_value", lambda: fixed)
    T = pybamm.Variable("T", domain="flow path")
    T_in = pybamm.Parameter("Inlet temperature [K]")
    value = compat.upwind_inlet_value(T, T_in)
    if fixed:
        assert value is T_in
    else:
        assert value == (T_in + pybamm.boundary_value(T, "left")) / 2


def test_citation_database_goes_to_read_citations_where_it_takes_a_file(monkeypatch):
    read = []
    monkeypatch.setattr(compat.citations, "reads_citation_files", lambda: True)
    monkeypatch.setattr(pybamm.citations, "read_citations", read.append)
    compat.add_citation_database()
    assert read == [compat.citations.CITATIONS_FILE]


def test_citation_database_needs_pybtex(monkeypatch):
    # Without pybtex, PyBaMM's citations do nothing, and so does the fallback
    def add_citation(key, entry):
        raise AssertionError("no citation is added without pybtex")

    monkeypatch.setattr(compat.citations, "reads_citation_files", lambda: False)
    monkeypatch.setattr(pybamm.citations, "_module_import_error", True)
    monkeypatch.setattr(pybamm.citations, "_add_citation", add_citation)
    compat.add_citation_database()


def test_citation_fallback_cites_keys_registered_before_loading(monkeypatch, tmp_path):
    # A key registered while still unknown is cited once its database is loaded, as
    # read_citations does on PyBaMM 26.11
    pytest.importorskip("pybtex")
    monkeypatch.setattr(compat.citations, "reads_citation_files", lambda: False)
    database = tmp_path / "extra.bib"
    database.write_text(
        "@misc{PyTESCompatTest, title = {A reference loaded after it was cited}, "
        "year = {2026}}\n"
    )
    pybamm.citations._reset()
    pybamm.citations.register("PyTESCompatTest")
    compat.add_citation_database(database)
    filename = tmp_path / "citations.txt"
    pybamm.print_citations(filename)
    assert "loaded after it was cited" in filename.read_text()
    pybamm.citations._reset()


def test_citation_keys_of_the_parameter_sets_are_in_the_database():
    keys = set(
        re.findall(r"@\w+\{([^,]+),", compat.citations.CITATIONS_FILE.read_text())
    )
    cited = set()
    for name in pytes.parameter_layers.SETS:
        cited |= set(pytes.parameter_layers.compose_set(name)["citations"])
    assert cited and cited <= keys
