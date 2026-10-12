"""
Labelling the step solutions of an experiment.

Upstream: no issue. From PyBaMM 26.10, :class:`pybamm.Solution` uses ``__slots__``, so new
attributes (such as a step description) can no longer be set on it. ``cycles`` and ``steps``
are still allowed.

Workaround: keep the description in a lookup keyed by the solution object.

Remove when: the runner moves to PyBaMM's own experiment framework, whose step solutions carry
their step, or PyBaMM gives :class:`pybamm.Solution` a field for it.
"""

import weakref

_descriptions = weakref.WeakKeyDictionary()


def set_step_description(solution, description):
    """
    Attach a step description to a solution.

    Parameters
    ----------
    solution : pybamm.Solution
        The solution of one step.
    description : str
        The step's description.
    """
    try:
        solution.step_description = description
    except AttributeError:
        _descriptions[solution] = description


def get_step_description(solution):
    """
    Return the step description attached by :func:`set_step_description`, or None.

    Parameters
    ----------
    solution : pybamm.Solution
        The solution of one step.
    """
    try:
        return solution.step_description
    except AttributeError:
        return _descriptions.get(solution)
