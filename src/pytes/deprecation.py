#
# Renamed names and their deprecation
#
"""
Renamed public names (DESIGN D17).

Every rename of a public name is one :class:`Rename` in :data:`RENAMES`. While its alias
is active, the old name still works and warns with :class:`PyTESDeprecationWarning`; once
the alias is retired, the old name raises an error that gives the new one. The entry is
never deleted, so that the error keeps pointing to the new name.

The kinds of names covered:

- ``"object"``: a class or function, by its full dotted path. The module that held the old
  name sets ``__getattr__ = module_getattr(__name__)``.
- ``"option"``: the name of a model option, checked by
  :meth:`pytes.BaseModel.process_options`.

Variable and parameter names are not covered yet (DESIGN §3): PyBaMM looks them up itself.

To silence the warnings, filter :class:`PyTESDeprecationWarning`; to find old names in your
own code, turn it into an error (``python -W error::DeprecationWarning``).
"""

import importlib
import sys
import warnings
from dataclasses import dataclass


class PyTESDeprecationWarning(DeprecationWarning):
    """A PyTES name was renamed; the old name still works, but will stop working"""


@dataclass(frozen=True)
class Rename:
    """
    A renamed public name.

    Parameters
    ----------
    kind : str
        ``"object"`` or ``"option"`` (see :mod:`pytes.deprecation`).
    old : str
        The old name; for an object, its full dotted path.
    new : str
        The new name; for an object, its full dotted path.
    finding : str
        The entry in ``docs/design/findings.md`` that logs the rename, e.g. ``"F-050"``.
    renamed_in : str
        The release that renamed it.
    removed_in : str
        The release from which the old name no longer works. Equal to ``renamed_in`` for a
        rename without an alias.
    alias : bool, optional
        Whether the old name still works, with a warning (default). Set to False when a
        release reaches ``removed_in``; the tests fail until then.
    """

    kind: str
    old: str
    new: str
    finding: str
    renamed_in: str
    removed_in: str
    alias: bool = True

    @property
    def message(self):
        """What happened to the old name and what to use instead"""
        label = f"option '{self.old}'" if self.kind == "option" else f"'{self.old}'"
        message = (
            f"{label} was renamed to '{self.new}' in PyTES {self.renamed_in} "
            f"({self.finding})"
        )
        if self.alias:
            message += f"; the old name will stop working in PyTES {self.removed_in}"
        return message


#: Every renamed public name, oldest first
RENAMES = (
    Rename(
        "option",
        "storage",
        "storage along flow path",
        finding="F-050",
        renamed_in="0.1.0a3",
        removed_in="0.1.0a3",
        alias=False,
    ),
)


def find(kind, old):
    """The :class:`Rename` of an old name of the given kind, or None"""
    for rename in RENAMES:
        if rename.kind == kind and rename.old == old:
            return rename
    return None


def _user_stacklevel():
    """
    The ``stacklevel`` of the first frame outside PyTES, for :func:`warnings.warn` called
    by :func:`check`, so that the warning points to the user's own line
    """
    # Frame 2 is the caller of check, which is stacklevel 2 for a warning check issues
    frame, level = sys._getframe(2), 2
    while frame.f_back is not None and frame.f_globals.get("__name__", "").startswith(
        "pytes."
    ):
        frame, level = frame.f_back, level + 1
    return level


def check(rename, error):
    """
    Warn that the old name is deprecated, or raise if its alias is retired.

    Parameters
    ----------
    rename : :class:`Rename`
    error : type
        The exception to raise if the alias is retired.

    Raises
    ------
    error
        If the alias is retired.
    """
    if not rename.alias:
        raise error(rename.message)
    warnings.warn(
        rename.message, PyTESDeprecationWarning, stacklevel=_user_stacklevel()
    )


def module_getattr(module):
    """
    A module-level ``__getattr__`` that resolves the module's renamed objects.

    Parameters
    ----------
    module : str
        The module's ``__name__``.
    """

    def __getattr__(name):
        rename = find("object", f"{module}.{name}")
        if rename is None:
            raise AttributeError(f"module {module!r} has no attribute {name!r}")
        check(rename, AttributeError)
        new_module, _, new_name = rename.new.rpartition(".")
        return getattr(importlib.import_module(new_module), new_name)

    return __getattr__
