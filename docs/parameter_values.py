"""
The Parameter values page, generated at each build from the registered parameter layers
(:data:`pytes.parameter_layers.LAYERS`) and sets (:data:`pytes.parameter_layers.SETS`), so
that it always shows the values the code holds.

Each layer's docstring gives its description, its source ("Source:") and, for the
materials and fluids, the temperature at which its constant values were taken
("Taken at:"). Those two lines are shown as fields.
"""

import inspect
import re

from pytes import parameter_layers

#: Section titles of the kinds, by key
TITLES = {
    "operation": "Operation",
    "coupling": "Coupling",
    "heat_transfer_fluid": "Heat transfer fluid",
    "pcm": "Phase-change material",
    "metal": "Metal",
    "finned_tube_flow_path": "Finned-tube flow path",
    "finned_tube_storage_element": "Finned-tube storage element",
    "packed_bed_flow_path": "Packed-bed flow path",
    "packed_bed_storage_element": "Packed-bed storage element",
}

_FIELD = re.compile(r"^(Source|Taken at):\s*(.*)$")

INTRO = """\
Parameter values
================

.. This page is generated at each build by docs/parameter_values.py: do not edit it.

The parameter values PyTES provides, read from the code at each build. A parameter set is
composed from layers of several kinds, so that one, e.g. the PCM, can be swapped without
touching the rest (see :mod:`pytes.parameter_layers`). Every value is in SI units, under the
name the models read. Each layer gives its source and, for the materials and fluids, the
temperature at which its values were taken: the models hold one value per phase, constant
in temperature.

A set or a layer is obtained with::

    import pytes

    parameter_values = pytes.parameter_layers.compose_set("Finned tube default")
    pcm = pytes.parameter_layers.get("pcm", "PCM 60")

"""


def _label(*parts):
    return "parameter-values-" + "-".join(
        re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-") for part in parts
    )


def _heading(text, underline):
    return [text, underline * len(text), ""]


def _value(name, value):
    if callable(value):
        return "a function"
    text = str(value) if isinstance(value, int) else f"{value:.6g}"
    if name.endswith("temperature [K]"):
        text += f" ({value - 273.15:.6g} °C)"
    return text


def _docstring(function):
    """The docstring as reStructuredText, with the source and temperature as fields"""
    lines = []
    for line in inspect.cleandoc(function.__doc__ or "").splitlines():
        match = _FIELD.match(line)
        if match:
            if lines and lines[-1] and not lines[-1].startswith((":", "   ")):
                lines.append("")
            lines.append(f":{match.group(1)}: {match.group(2)}")
        elif lines and lines[-1].startswith((":", "   ")) and line:
            # The continuation of a field
            lines.append(f"   {line}")
        else:
            lines.append(line)
    return lines + [""]


def _table(layer):
    rows = [
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 3 2",
        "",
        "   * - Parameter",
        "     - Value",
    ]
    for name, value in layer.items():
        if name != "citations":
            rows += [f"   * - ``{name}``", f"     - {_value(name, value)}"]
    return rows + [""]


def _sets():
    lines = _heading("Parameter sets", "-")
    lines += [
        "The named sets, composed with :func:`pytes.parameter_layers.compose_set`. The "
        "default parameter values of each family are one of them.",
        "",
    ]
    for name, layers in parameter_layers.SETS.items():
        lines += [f".. _{_label('set', name)}:", ""]
        lines += _heading(name, "~")
        lines += [
            ".. list-table::",
            "   :header-rows: 1",
            "   :widths: 2 3",
            "",
            "   * - Kind",
            "     - Layer",
        ]
        for kind, layer in layers.items():
            lines += [
                f"   * - {TITLES.get(kind, kind)}",
                f"     - :ref:`{layer} <{_label(kind, layer)}>`",
            ]
        lines.append("")
    return lines


def _kinds():
    lines = _heading("Layers", "-")
    lines += [
        "The registered layers of each kind, obtained with "
        ":func:`pytes.parameter_layers.get`.",
        "",
    ]
    for key, layers in parameter_layers.LAYERS.items():
        kind = parameter_layers.KINDS[key]
        lines += [f".. _{_label('kind', key)}:", ""]
        lines += _heading(TITLES.get(key, key), "~")
        lines += [f"{kind.description}.", ""]
        for name, function in layers.items():
            lines += [f".. _{_label(key, name)}:", ""]
            lines += _heading(name, "^")
            lines += _docstring(function)
            lines += [f'``pytes.parameter_layers.get("{key}", "{name}")``', ""]
            lines += _table(function())
    return lines


def write(path):
    """
    Write the Parameter values page.

    Parameters
    ----------
    path : pathlib.Path
        The page to write, a reStructuredText file.
    """
    lines = [INTRO] + _sets() + _kinds()
    path.write_text("\n".join(lines), encoding="utf-8")
