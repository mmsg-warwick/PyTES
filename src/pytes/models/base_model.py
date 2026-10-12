#
# Base model for PyTES models
#
"""Base class of PyTES models: a fixed composition of submodels, checked when built."""

import pybamm

from ..variables import add_temperature_variables


class WiringError(ValueError):
    """The submodels' declared inputs and outputs do not fit together"""


class BaseModel(pybamm.BaseModel):
    """
    A heat battery model: a fixed composition of submodels (DESIGN D3).

    Subclasses define :meth:`get_parameters` and :meth:`set_submodels`. The model builds
    itself from the submodels and checks their declarations:

    - every name a submodel requires is provided by exactly one submodel;
    - every submodel adds exactly the names it provides (plus their [degC] twins);
    - a submodel only reads the names it requires or provides (it sees no others).

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
        Check that every required name is provided by exactly one submodel.

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
            for name in submodel.requires:
                if name not in providers:
                    raise WiringError(
                        f"{submodel.name!r} requires '{name}', which no submodel provides"
                    )
        return providers

    @staticmethod
    def _view(variables, submodel):
        """The variables a submodel may read: those it requires or provides"""
        names = set(submodel.requires) | set(submodel.provides)
        return {
            k: v for k, v in variables.items() if k in names or _twin_of(k) in names
        }

    def _call(self, submodel, method, variables):
        view = self._view(variables, submodel)
        try:
            return getattr(submodel, method)(view)
        except KeyError as error:
            raise WiringError(
                f"{submodel.name!r} reads {error} in {method} without declaring it in "
                "'requires'"
            ) from None

    def build_model(self):
        """Build the equations and variables from the submodels, checking the wiring"""
        self.check_wiring()
        variables = {
            "Time [s]": pybamm.t,
            "Time [min]": pybamm.t / 60,
            "Time [h]": pybamm.t / 3600,
        }
        added = {}
        for submodel in self.submodels.values():
            new = submodel.get_fundamental_variables()
            added[submodel] = set(new)
            variables.update(new)

        pending = list(self.submodels.values())
        while pending:
            ready = [
                s for s in pending if all(name in variables for name in s.requires)
            ]
            if not ready:
                names = ", ".join(repr(s.name) for s in pending)
                raise WiringError(f"Circular requirements between {names}")
            for submodel in ready:
                view = self._view(variables, submodel)
                before = set(view)
                new = self._call_coupled(submodel, view)
                new_names = set(new) - before
                added[submodel] |= new_names
                variables.update({k: new[k] for k in new_names})
                pending.remove(submodel)

        for submodel, names in added.items():
            declared = set(submodel.provides)
            missing = declared - names
            undeclared = {n for n in names - declared if _twin_of(n) not in declared}
            if missing:
                raise WiringError(
                    f"{submodel.name!r} does not provide {sorted(missing)}"
                )
            if undeclared:
                raise WiringError(
                    f"{submodel.name!r} adds undeclared variables {sorted(undeclared)}"
                )

        for submodel in self.submodels.values():
            for method in (
                "set_rhs",
                "set_algebraic",
                "set_boundary_conditions",
                "set_initial_conditions",
                "set_events",
            ):
                self._call(submodel, method, variables)
            self.rhs.update(submodel.rhs)
            self.algebraic.update(submodel.algebraic)
            self.initial_conditions.update(submodel.initial_conditions)
            self.events.extend(submodel.events)
            for var, bcs in submodel.boundary_conditions.items():
                existing = self.boundary_conditions.setdefault(var, {})
                clash = set(existing) & set(bcs)
                if clash:
                    raise WiringError(
                        f"{submodel.name!r} sets the {sorted(clash)} boundary condition "
                        f"of {var.name!r}, which another submodel already sets"
                    )
                existing.update(bcs)

        self.variables.update(variables)

    def _call_coupled(self, submodel, view):
        try:
            return submodel.get_coupled_variables(dict(view))
        except KeyError as error:
            raise WiringError(
                f"{submodel.name!r} reads {error} in get_coupled_variables without "
                "declaring it in 'requires'"
            ) from None

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


def _twin_of(name):
    """The [K] name a [degC] name is the twin of (or None)"""
    if name.endswith("[degC]"):
        return name[: -len("[degC]")] + "[K]"
    return None
