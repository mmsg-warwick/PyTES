"""Renamed names and their deprecation (DESIGN D17)."""

import dataclasses
import importlib
import json
import re
from pathlib import Path

import pytest
from conftest import MODEL_CLASSES
from packaging.version import Version

import pytes
from pytes import deprecation
from pytes.deprecation import PyTESDeprecationWarning, Rename

ROOT = Path(__file__).parents[2]

#: Where users read PyTES code: the example notebooks and the user documentation. Not
#: the changelog (nor its copy in docs/, made when the site is built): it records the
#: names of its time
USER_FACING = [
    *sorted((ROOT / "examples").glob("*.ipynb")),
    ROOT / "README.md",
    *sorted(p for p in (ROOT / "docs").glob("*.md") if p.name != "changelog.md"),
]

#: A deprecated function, for the tests of the mechanism
OLD_FUNCTION = Rename(
    "object",
    "pytes.variables.old_unit_twins",
    "pytes.variables.unit_twins",
    finding="F-000",
    renamed_in="0.1.0a3",
    removed_in="0.2.0",
)

#: A deprecated option, for the tests of the mechanism
OLD_OPTION = Rename(
    "option",
    "storage layout",
    "storage along flow path",
    finding="F-000",
    renamed_in="0.1.0a3",
    removed_in="0.2.0",
)


@pytest.fixture
def renames(monkeypatch):
    """The registry with the test renames added, and pytes.variables wired"""
    monkeypatch.setattr(
        deprecation, "RENAMES", (*deprecation.RENAMES, OLD_FUNCTION, OLD_OPTION)
    )
    monkeypatch.setattr(
        pytes.variables,
        "__getattr__",
        deprecation.module_getattr("pytes.variables"),
        raising=False,
    )


@pytest.mark.parametrize("rename", deprecation.RENAMES, ids=lambda r: r.old)
def test_registry_entry_is_consistent(rename):
    assert rename.kind in ("object", "option")
    assert rename.old != rename.new
    assert re.fullmatch(r"F-\d{3}", rename.finding)
    assert Version(rename.renamed_in) <= Version(rename.removed_in)
    if rename.alias:
        assert Version(rename.renamed_in) < Version(rename.removed_in)
        # Fails when a release reaches the removal release: retire the alias then
        assert Version(pytes.__version__) < Version(rename.removed_in), (
            f"PyTES {pytes.__version__} reached the removal release of '{rename.old}': "
            "set alias=False"
        )


def _check_object(rename):
    """The old name of an object warns and gives the new object, or raises"""
    module, _, name = rename.old.rpartition(".")
    new_module, _, new_name = rename.new.rpartition(".")
    new = getattr(importlib.import_module(new_module), new_name)
    if not rename.alias:
        with pytest.raises(AttributeError, match=re.escape(rename.message)):
            getattr(importlib.import_module(module), name)
        return
    with pytest.warns(PyTESDeprecationWarning, match=re.escape(rename.message)):
        old = getattr(importlib.import_module(module), name)
    assert old is new


def _check_option(rename):
    """The old name of an option warns and sets the new one, or raises"""
    classes = [c for c in MODEL_CLASSES if rename.new in c.allowed_options]
    assert classes, f"no model has the option '{rename.new}'"
    for cls in classes:
        value = cls.allowed_options[rename.new][-1]
        if not rename.alias:
            with pytest.raises(pytes.OptionError, match=re.escape(rename.message)):
                cls(options={rename.old: value})
            continue
        with pytest.warns(PyTESDeprecationWarning, match=re.escape(rename.message)):
            options = cls(options={rename.old: value}).options
        assert options == cls(options={rename.new: value}).options


def test_old_names_warn_or_raise():
    """Every old name in the registry, including the module wiring of objects"""
    for rename in deprecation.RENAMES:
        {"object": _check_object, "option": _check_option}[rename.kind](rename)


def test_deprecated_names_warn(renames):
    _check_object(OLD_FUNCTION)
    _check_option(OLD_OPTION)
    assert "will stop working in PyTES 0.2.0" in OLD_FUNCTION.message


def test_retired_alias_raises(renames, monkeypatch):
    retired = dataclasses.replace(OLD_FUNCTION, alias=False)
    monkeypatch.setattr(deprecation, "RENAMES", (retired,))
    _check_object(retired)
    assert "will stop working" not in retired.message


def test_import_of_a_deprecated_name_warns(renames):
    with pytest.warns(PyTESDeprecationWarning):
        from pytes.variables import old_unit_twins
    assert old_unit_twins is pytes.variables.unit_twins


def test_warning_points_to_the_users_line(renames):
    # Raised several calls deep in PyTES (model __init__, process_options)
    with pytest.warns(PyTESDeprecationWarning) as record:
        pytes.PackedBedModel(options={"storage layout": "averaged"})
    assert record[0].filename == __file__
    with pytest.warns(PyTESDeprecationWarning) as record:
        pytes.variables.old_unit_twins  # noqa: B018
    assert record[0].filename == __file__


def test_option_under_both_names_raises(renames):
    options = {"storage layout": "averaged", "storage along flow path": "resolved"}
    with (
        pytest.warns(PyTESDeprecationWarning),
        pytest.raises(pytes.OptionError, match="under both its old and new names"),
    ):
        pytes.PackedBedModel(options=options)


def test_unknown_name_is_an_attribute_error(renames):
    with pytest.raises(AttributeError, match="has no attribute 'nothing'"):
        pytes.variables.nothing  # noqa: B018


def _text(path):
    """The text of a file, or the sources of a notebook's cells"""
    if path.suffix == ".ipynb":
        cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
        return "\n".join("".join(cell["source"]) for cell in cells)
    return path.read_text(encoding="utf-8")


def _pattern(rename):
    """How the old name appears in code: an option, in a dict passed as ``options=``"""
    if rename.kind == "object":
        return rf"\b{re.escape(rename.old.rpartition('.')[2])}\b"
    return rf'options\s*=\s*\{{[^}}]*"{re.escape(rename.old)}"\s*:'


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_user_facing_files_use_new_names(path):
    """Old names never appear where users copy code from (the tests run with
    PyTESDeprecationWarning as an error, which covers the code they run)"""
    text = _text(path)
    for rename in deprecation.RENAMES:
        assert not re.search(_pattern(rename), text), (
            f"{path.name} uses '{rename.old}': use '{rename.new}'"
        )


def test_old_name_patterns():
    assert re.search(_pattern(OLD_FUNCTION), "old_unit_twins(name)")
    assert not re.search(_pattern(OLD_FUNCTION), "unit_twins(name)")
    assert re.search(_pattern(OLD_OPTION), 'options={"storage layout": "averaged"}')
    assert re.search(_pattern(OLD_OPTION), 'options={"a": 1, "storage layout": "x"}')
    assert not re.search(_pattern(OLD_OPTION), 'ComposedModel({"storage layout": s})')
