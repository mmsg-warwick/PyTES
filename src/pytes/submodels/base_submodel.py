#
# Base class for PyTES submodels
#
"""
Base class for submodels.

PyBaMM's own ``pybamm.BaseSubModel`` assumes a battery (its domains must be "negative",
"separator" or "positive" and its options are battery options), so PyTES has its own. It
keeps PyBaMM's method names, so the build loop reads the same.
"""


class BaseSubModel:
    """
    A part of a model with declared inputs and outputs.

    Subclasses declare the variable names they need from other submodels (``requires``)
    and the names they add (``provides``), and override the ``get_*`` and ``set_*`` methods
    they need. The model checks the declarations when it is built: every required name must
    be provided by exactly one submodel, and every submodel must add the names it declares.

    Parameters
    ----------
    param : object
        The model's parameters.
    name : str, optional
        Name of the submodel.

    Attributes
    ----------
    requires : tuple of str
        Names of the variables this submodel needs from other submodels.
    provides : tuple of str
        Names of the variables this submodel adds.
    assumptions : tuple of str
        Modelling assumptions, in a sentence each (for model cards).
    rhs, algebraic, boundary_conditions, initial_conditions : dict
        Equations, filled by the ``set_*`` methods.
    events : list
        Events, filled by :meth:`set_events`.
    """

    requires = ()
    provides = ()
    assumptions = ()

    def __init__(self, param, name=None):
        self.param = param
        self.name = name or type(self).__name__
        self.rhs = {}
        self.algebraic = {}
        self.boundary_conditions = {}
        self.initial_conditions = {}
        self.events = []

    def get_fundamental_variables(self):
        """
        Return the variables this submodel can define without other submodels (its state
        variables, typically).

        Returns
        -------
        dict
        """
        return {}

    def get_coupled_variables(self, variables):
        """
        Return ``variables`` with the variables this submodel defines from those of other
        submodels added.

        Parameters
        ----------
        variables : dict
            All the variables defined so far, including every name in ``requires``.

        Returns
        -------
        dict
        """
        return variables

    def set_rhs(self, variables):
        """Set ``self.rhs`` from the complete variables"""

    def set_algebraic(self, variables):
        """Set ``self.algebraic`` from the complete variables"""

    def set_boundary_conditions(self, variables):
        """Set ``self.boundary_conditions`` from the complete variables"""

    def set_initial_conditions(self, variables):
        """Set ``self.initial_conditions`` from the complete variables"""

    def set_events(self, variables):
        """Append to ``self.events`` from the complete variables"""

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r})"
