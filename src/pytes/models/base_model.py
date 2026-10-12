#
# Base model for PyTES models
#
"""Base class of PyTES models: a fixed composition of submodels, checked when built."""

import pybamm

from .. import compat
from ..variables import add_temperature_variables


class WiringError(ValueError):
    """The submodels' inputs and outputs do not fit together"""


class BaseModel(pybamm.BaseModel):
    """
    A heat battery model: a fixed composition of submodels (DESIGN D3).

    Subclasses define :meth:`get_parameters` and :meth:`set_submodels`. Each submodel reads
    the variables of the others as :class:`pybamm.CoupledVariable` (its ``requires``). When
    the model is built it merges the submodels with :meth:`pybamm.BaseModel.update`, checks
    the wiring and resolves every coupled variable, so the finished model contains none:

    - every required name is provided by exactly one submodel;
    - no variable depends on itself through coupled variables;
    - once resolved, each provided variable has the primary domain its coupled variable
      declares.

    Parameters
    ----------
    name : str
        The name of the model.
    operating_mode : str or None, optional
        Sets the cut-off event (DESIGN D11). "discharge" (default) stops when the outlet
        temperature falls below "Cut-off temperature [K]", "charge" stops when it rises
        above it, and None runs to the final time. Charge and discharge are defined by heat
        flowing into or out of the storage.

    Attributes
    ----------
    param : object
        The parameters, from :meth:`get_parameters`.
    submodels : dict
        The submodels, by name, in the order they were added.
    controls : dict
        The model's controls (DESIGN D9): the parameter symbols an experiment may turn
        into solver unknowns, keyed by the name of the matching variable.
    """

    #: Scale of the temperature variables [K]
    temperature_scale = 200

    def __init__(self, name, operating_mode="discharge"):
        super().__init__(name=name)
        if operating_mode not in ("discharge", "charge", None):
            msg = (
                f"Operating mode '{operating_mode}' not recognised, "
                "must be 'discharge', 'charge' or None"
            )
            raise ValueError(msg)
        self.operating_mode = operating_mode
        self.param = self.get_parameters()
        self.submodels = {}
        self.set_submodels()
        self.build_model()
        self.set_events()

    def get_parameters(self):
        """Return the model's parameters"""
        raise NotImplementedError

    def set_submodels(self):
        """Fill ``self.submodels``"""
        raise NotImplementedError

    @property
    def controls(self):
        """
        The controls: inlet temperature and mass flow rate, as parameter symbols, keyed by
        the names of the matching variables
        """
        return {
            "Inlet temperature [K]": self.param.T_in,
            "Mass flow rate [kg.s-1]": self.param.mdot,
        }

    def power(self, variables, controls=None):
        """
        Power [W] with some controls replaced by given symbols.

        The experiment runner uses this to write a step's power equation with the step's
        target values, so that the equation depends on the control it adjusts.

        Parameters
        ----------
        variables : dict
            The model's variables.
        controls : dict, optional
            Symbols replacing the controls, keyed by control name.
        """
        controls = controls or {}
        fluid = self.param.fluid
        T_in = controls.get("Inlet temperature [K]", variables["Inlet temperature [K]"])
        mdot = controls.get(
            "Mass flow rate [kg.s-1]", variables["Mass flow rate [kg.s-1]"]
        )
        return mdot * (variables["Outlet specific enthalpy [J.kg-1]"] - fluid.h(T_in))

    def check_wiring(self):
        """
        Check that the submodels fit together (see the class docstring).

        Returns
        -------
        dict
            The submodel providing each variable name.

        Raises
        ------
        WiringError
        """
        providers = {}
        for submodel in self.submodels.values():
            for name in submodel.provides:
                if name in providers:
                    raise WiringError(
                        f"'{name}' is provided by both {providers[name].name!r} and "
                        f"{submodel.name!r}"
                    )
                providers[name] = submodel
        for submodel in self.submodels.values():
            for name in submodel.coupled_variables:
                if name not in providers:
                    raise WiringError(
                        f"{submodel.name!r} requires '{name}', which no submodel provides"
                    )
        self._check_no_cycles(providers)
        return providers

    def _check_domains(self, providers):
        """
        Raise if a provided variable is not on the primary domain its coupled variable
        declares. Checked after resolution: before it, an expression built from coupled
        variables only knows their primary domains.
        """
        for submodel in self.submodels.values():
            for name, coupled in submodel.coupled_variables.items():
                provided = self.variables[name]
                if coupled.domain and coupled.domain != provided.domain:
                    raise WiringError(
                        f"{submodel.name!r} requires '{name}' on {coupled.domain}, but "
                        f"{providers[name].name!r} provides it on {provided.domain}"
                    )

    def _check_no_cycles(self, providers):
        """Raise if a provided variable depends on itself through coupled variables"""

        def coupled_names(symbol):
            return {
                node.name
                for node in symbol.pre_order()
                if isinstance(node, pybamm.CoupledVariable)
            }

        done, active = set(), []

        def visit(name):
            if name in done:
                return
            if name in active:
                cycle = " -> ".join([*active[active.index(name) :], name])
                raise WiringError(f"Circular dependency: {cycle}")
            active.append(name)
            for other in coupled_names(providers[name].variables[name]):
                visit(other)
            active.pop()
            done.add(name)

        for name in providers:
            visit(name)

    def build_model(self):
        """Merge the submodels, check the wiring and resolve the coupled variables"""
        providers = self.check_wiring()
        self.variables = {
            "Time [s]": pybamm.t,
            "Time [min]": pybamm.t / 60,
            "Time [h]": pybamm.t / 3600,
        }
        try:
            self.update(*self.submodels.values())
        except pybamm.ModelError as error:
            raise WiringError(str(error)) from None
        compat.resolve_coupled_variables(self)
        self._check_domains(providers)

    def set_events(self):
        """
        Set the cut-off event of the operating mode: the solution stops when the outlet
        temperature falls below (discharge) or rises above (charge) the cut-off
        temperature. No event is set when the operating mode is None.
        """
        T_out = self.variables["Outlet temperature [K]"]
        if self.operating_mode == "discharge":
            self.events.append(
                pybamm.Event("Cut-off temperature [K]", T_out - self.param.T_cut)
            )
        elif self.operating_mode == "charge":
            self.events.append(
                pybamm.Event("Cut-off temperature [K]", self.param.T_cut - T_out)
            )

    @staticmethod
    def add_temperature_variables(variables, temperatures):
        """See :func:`pytes.variables.add_temperature_variables`"""
        return add_temperature_variables(variables, temperatures)
