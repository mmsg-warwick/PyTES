"""
Resolving :class:`pybamm.CoupledVariable` when a model is built.

Upstream: no issue filed yet. PyBaMM resolves coupled variables in the model's equations only
when the discretisation is created with ``resolve_coupled_variables=True``; the default
(``False``, also in :class:`pybamm.Simulation`) fails with "CoupledVariable ... was not
resolved before discretisation".

Workaround: PyTES models resolve every coupled variable when they are built, so the finished
model contains none and works with a default :class:`pybamm.Simulation`, solvers and PyBOP.

Remove when: PyBaMM resolves coupled variables by default (in :class:`pybamm.Discretisation`
and everything that builds one), at which point the models can keep them unresolved.
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
