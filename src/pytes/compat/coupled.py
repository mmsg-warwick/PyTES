"""
Resolving :class:`pybamm.CoupledVariable` when a model is built.

Upstream: pybamm-team/PyBaMM#6001, fixed by PR #6002 (PyBaMM 26.11), plus a bug not filed
yet (draft in the gitignored docs/upstream). Before 26.11, PyBaMM resolves coupled variables
only when the discretisation is created with ``resolve_coupled_variables=True`` (in
:class:`pybamm.Simulation`, through ``discretisation_kwargs``), and then not in boundary
conditions (#6001). From 26.11 it resolves them by default, also in boundary conditions.
But on every release it resolves them from the unprocessed ``model.variables`` after
parameter processing, so a variable whose scale or reference holds a parameter (as every
PyTES state does) no longer matches its processed key in ``model.rhs``, and discretisation
fails with "No key set for variable".

Workaround: PyTES models resolve every coupled variable when they are built, before
parameter processing, so the finished model contains none and works with a default
:class:`pybamm.Simulation`, solvers and PyBOP, on every supported PyBaMM. This shim does not
defer to PyBaMM's resolution until the bug above is fixed.

Remove when: PyBaMM resolves coupled variables correctly by default after parameter
processing, in every supported release (``fixed_in`` in :data:`pytes.compat.SHIMS`), at
which point the models can keep them unresolved (a contract change: log a finding).
"""

import pybamm


def resolve_coupled_variables(model):
    """
    Replace every :class:`pybamm.CoupledVariable` in a model by the variable it names.

    Resolves the equations, boundary and initial conditions, events and variables, in place.
    The caller checks the wiring first (every name provided, no cycles).

    Parameters
    ----------
    model : pybamm.BaseModel
        The model, whose ``variables`` provide every coupled name.
    """
    variables = dict(model.variables)
    cache = {}

    def resolve(symbol):
        def fn(node, new_leaves):
            if isinstance(node, pybamm.CoupledVariable):
                return resolve(variables[node.name])
            return pybamm.rebuild(node, new_leaves)

        return pybamm.tree_map(fn, symbol, cache=cache)

    model.rhs = {var: resolve(eq) for var, eq in model.rhs.items()}
    model.algebraic = {var: resolve(eq) for var, eq in model.algebraic.items()}
    model.initial_conditions = {
        var: resolve(eq) for var, eq in model.initial_conditions.items()
    }
    model.boundary_conditions = {
        var: {side: (resolve(value), kind) for side, (value, kind) in bcs.items()}
        for var, bcs in model.boundary_conditions.items()
    }
    model.events = [
        pybamm.Event(event.name, resolve(event.expression), event.event_type)
        for event in model.events
    ]
    model.variables = {name: resolve(symbol) for name, symbol in variables.items()}
