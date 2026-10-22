#
# Base model for PyTES models
#
"""Base class of PyTES models: a fixed composition of submodels, checked when built."""

import pybamm

from .. import compat
from ..submodels.base_submodel import parameter_names
from ..variables import add_unit_twins


class WiringError(ValueError):
    """The submodels' inputs and outputs do not fit together"""


class OptionError(ValueError):
    """An option, a value or a combination of options that the model does not allow"""


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

    The equations are the same for charge and discharge, and the model has no events:
    cut-offs are the terminations of an experiment (DESIGN D11).

    Variants are chosen through ``options`` (DESIGN D3): each model declares the values it
    allows in :attr:`allowed_options`, the first being the default. An unknown option or
    value raises, as does a combination :meth:`check_options` rejects; a model never swaps a
    submodel the user did not ask for.

    Parameters
    ----------
    name : str
        The name of the model.
    options : dict, optional
        The model's options; missing ones take their defaults.

    Attributes
    ----------
    param : object
        The parameters, from :meth:`get_parameters`.
    options : dict
        The model's options, defaults included.
    submodels : dict
        The submodels, by name, in the order they were added.
    controls : dict
        The model's controls (DESIGN D9): the parameter symbols an experiment may turn
        into solver unknowns, keyed by the name of the matching variable.
    """

    #: Scale of the temperature variables [K]
    temperature_scale = 200

    #: Allowed values of each option, the first being the default
    allowed_options = {}

    #: Options that were renamed, by old name: the error for an old name gives the new one
    renamed_options = {"storage": "storage along flow path"}

    def __init__(self, name, options=None):
        super().__init__(name=name)
        self.options = self.process_options(options)
        self.set_spatial_variables()
        self.param = self.get_parameters()
        self.submodels = {}
        self.set_submodels()
        self.build_model()

    def process_options(self, options):
        """
        The options with their defaults filled in.

        Raises
        ------
        pytes.OptionError
            If an option or a value is not allowed (an option that was renamed included),
            or the combination is rejected by :meth:`check_options`.
        """
        options = dict(options or {})
        for key, value in options.items():
            if key in self.renamed_options:
                raise OptionError(
                    f"{self.name}: option '{key}' was renamed to "
                    f"'{self.renamed_options[key]}'"
                )
            if key not in self.allowed_options:
                raise OptionError(
                    f"{self.name}: option '{key}' not recognised; the options are "
                    f"{sorted(self.allowed_options)}"
                )
            if value not in self.allowed_options[key]:
                raise OptionError(
                    f"{self.name}: value '{value}' of option '{key}' not recognised; "
                    f"it must be one of {list(self.allowed_options[key])}"
                )
        options = {
            key: options.get(key, values[0])
            for key, values in self.allowed_options.items()
        }
        self.check_options(options)
        return options

    @classmethod
    def check_options(cls, options):
        """
        Raise :class:`pytes.OptionError` for an incompatible combination of options (none
        here). A class method, so that the admitted combinations can be listed without
        building the model.

        Parameters
        ----------
        options : dict
            Every option, defaults included.
        """

    def set_spatial_variables(self):
        """Create the spatial variables, which may depend on the options"""

    def get_parameters(self):
        """Return the model's parameters"""
        raise NotImplementedError

    def set_submodels(self):
        """Fill ``self.submodels``"""
        raise NotImplementedError

    @property
    def controls(self):
        """
        The controls, inlet temperature and mass flow rate, as parameter symbols, keyed by
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

    @property
    def geometry_parameters(self):
        """Names of the parameters in the default geometry (the domain lengths), sorted"""
        symbols = [
            bound
            for domain in self.default_geometry.values()
            for extent in domain.values()
            for bound in extent.values()
            if isinstance(bound, pybamm.Symbol)
        ]
        return parameter_names(symbols)

    def print_submodel_info(self):
        """
        Print the submodels: for each slot, the class, the variables it requires and
        provides, the parameters it uses and its modelling assumptions; then the parameters
        of the model's geometry (DESIGN D3).
        """
        for slot, submodel in self.submodels.items():
            print(f"{slot}: {type(submodel).__name__} ({submodel.name})")
            for heading, names in (
                ("requires", submodel.requires),
                ("provides", submodel.provides),
                ("parameters", submodel.parameters),
                ("assumptions", submodel.assumptions),
            ):
                print(f"    {heading}:")
                for name in names or ("(none)",):
                    print(f"        {name}")
        print("geometry parameters:")
        for name in self.geometry_parameters or ("(none)",):
            print(f"    {name}")

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
        """
        Merge the submodels, check the wiring, resolve the coupled variables and add the
        unit twins (DESIGN D12: the submodels define every quantity in SI units)
        """
        providers = self.check_wiring()
        self.variables = {"Time [s]": pybamm.t}
        try:
            self.update(*self.submodels.values())
        except pybamm.ModelError as error:
            raise WiringError(str(error)) from None
        compat.resolve_coupled_variables(self)
        self._check_domains(providers)
        self.variables = add_unit_twins(dict(self.variables))
