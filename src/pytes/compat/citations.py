"""
The PyTES citation database in :data:`pybamm.citations`.

Upstream: pybamm-team/PyBaMM#5950, done in part by PR #6003 (PyBaMM 26.11):
``Citations.read_citations`` takes the path of a BibTeX file and adds its entries to the
known citations without citing them. The entry point in #5950 is still open.

Problem: before 26.11, ``read_citations`` reads only PyBaMM's own ``CITATIONS.bib``, so the
keys that PyTES parameter sets list in ``"citations"`` (e.g. ``"Nallusamy2007"``) are
unknown, and :func:`pybamm.print_citations` drops them with a warning.

Workaround: on a PyBaMM whose ``read_citations`` takes a file (detected by
:func:`reads_citation_files`), PyTES passes its ``CITATIONS.bib`` to it. On an older one,
it adds the entries through the private ``Citations._add_citation``, as ``read_citations``
does there. Either way this runs when :mod:`pytes` is imported, and does nothing without
pybtex (``pybamm[cite]``), as PyBaMM's citations do.

Remove when: the oldest supported PyBaMM has the fix (``fixed_in`` in
:data:`pytes.compat.SHIMS`). Then call ``pybamm.citations.read_citations`` directly, or use
the entry point if #5950 adds one.
"""

import inspect
from pathlib import Path

import pybamm

#: The BibTeX file of the references PyTES cites
CITATIONS_FILE = Path(__file__).parents[1] / "CITATIONS.bib"


def reads_citation_files():
    """
    Whether ``pybamm.citations.read_citations`` takes the path of a BibTeX file
    (pybamm-team/PyBaMM#6003, in 26.11).

    Returns
    -------
    bool
    """
    return len(inspect.signature(pybamm.citations.read_citations).parameters) > 0


def add_citation_database(filename=CITATIONS_FILE):
    """
    Add the entries of a BibTeX file to the citations PyBaMM knows, without citing them.
    Keys registered before they were known (e.g. by a parameter set) are then cited.

    Parameters
    ----------
    filename : str or pathlib.Path, optional
        The BibTeX file (default: PyTES's ``CITATIONS.bib``).
    """
    citations = pybamm.citations
    if reads_citation_files():
        citations.read_citations(filename)
        return
    if citations._module_import_error:
        return
    from pybtex.database import parse_file

    for key, entry in parse_file(filename, bib_format="bibtex").entries.items():
        citations._add_citation(key, entry)
        if key in citations._unknown_citations:
            citations._papers_to_cite.add(key)
            citations._unknown_citations.discard(key)
