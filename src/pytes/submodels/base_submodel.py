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


class BaseSubModel(pybamm.BaseModel):
    """
    A part of a model, with its inputs and outputs readable from the code.

    Subclasses implement :meth:`build`, which sets ``variables``, ``rhs``, ``algebraic``,
    ``boundary_conditions``, ``initial_conditions`` and ``events``. A variable set by another
    submodel is read with :meth:`coupled`, never by reaching into that submodel.

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

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r})"
