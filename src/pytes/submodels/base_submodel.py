#
# Base class for PyTES submodels
#
"""
Base class for submodels.

A submodel is a small :class:`pybamm.BaseModel`: it sets its own variables, equations and
boundary and initial conditions, and refers to the variables of other submodels by name with
:class:`pybamm.CoupledVariable`. The model merges its submodels with
:meth:`pybamm.BaseModel.update` and resolves the coupled variables when it is built.

PyBaMM's ``pybamm.BaseSubModel`` is not used: it assumes a battery (its domains must be
"negative", "separator" or "positive" and its options are battery options).
"""

import pybamm


def parameter_names(symbols):
    """
    Names of the :class:`pybamm.Parameter` and :class:`pybamm.FunctionParameter` objects in
    some symbols, sorted.

    Parameters
    ----------
    symbols : iterable of pybamm.Symbol

    Returns
    -------
    tuple of str
    """
    names = set()
    for symbol in symbols:
        for node in symbol.pre_order():
            if isinstance(node, pybamm.Parameter | pybamm.FunctionParameter):
                names.add(node.name)
    return tuple(sorted(names))


class BaseSubModel(pybamm.BaseModel):
    """
    A part of a model, with its inputs and outputs readable from the code.

    Subclasses implement :meth:`build`, which sets ``variables``, ``rhs``, ``algebraic``,
    ``boundary_conditions``, ``initial_conditions`` and ``events``. A variable set by another
    submodel is read with :meth:`coupled`, never by reaching into that submodel.

    Besides the attributes below, the metadata is read from the code (DESIGN D3):
    :attr:`requires`, :attr:`provides` and :attr:`parameters`.

    Parameters
    ----------
    param : object
        The model's parameters.
    name : str, optional
        Name of the submodel.

    Attributes
    ----------
    param : object
        The model's parameters.
    coupled_variables : dict
        The :class:`pybamm.CoupledVariable` objects created by :meth:`coupled`, by name
        (PyBaMM's own record of the variables a model needs from other models).
    assumptions : tuple of str
        Modelling assumptions, in a sentence each (for model cards).
    """

    assumptions = ()

    def __init__(self, param, name=None):
        super().__init__(name=name or type(self).__name__)
        self.param = param
        self.build()

    def build(self):
        """Set the variables, equations and conditions of the submodel"""
        raise NotImplementedError

    def coupled(self, name, domain=None):
        """
        A variable set by another submodel, to be resolved when the model is built.

        Parameters
        ----------
        name : str
            Name of the variable.
        domain : str or list of str, optional
            Its primary domain. The model checks it against the variable that provides it.

        Returns
        -------
        pybamm.CoupledVariable
        """
        if name not in self.coupled_variables:
            self.coupled_variables = {
                **self.coupled_variables,
                name: pybamm.CoupledVariable(name, domain),
            }
        return self.coupled_variables[name]

    @property
    def requires(self):
        """Names of the variables this submodel needs from other submodels"""
        return tuple(self.coupled_variables)

    @property
    def provides(self):
        """Names of the variables this submodel sets"""
        return tuple(self.variables)

    @property
    def parameters(self):
        """
        Names of the parameters this submodel uses, read from its equations, conditions,
        variables and the scales of its states. Domain lengths are not among them: they
        enter through the model's geometry (see :attr:`pytes.BaseModel.geometry_parameters`).
        """
        symbols = [
            *self.rhs.values(),
            *self.algebraic.values(),
            *self.initial_conditions.values(),
            *self.variables.values(),
            *(event.expression for event in self.events),
        ]
        for bcs in self.boundary_conditions.values():
            symbols += [value for value, _ in bcs.values()]
        for state in [*self.rhs, *self.algebraic]:
            symbols += [
                s
                for s in (state.scale, state.reference)
                if isinstance(s, pybamm.Symbol)
            ]
        return parameter_names(symbols)

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r})"
