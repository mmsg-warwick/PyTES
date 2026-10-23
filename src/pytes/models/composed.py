#
# Model composed from given submodels
#
"""A model built from submodels by the user (DESIGN D3)."""

import copy

from .base_model import BaseModel

#: The defaults a composed model takes, by argument name, and the property each sets
_DEFAULTS = {
    "geometry": "default_geometry",
    "submesh_types": "default_submesh_types",
    "var_pts": "default_var_pts",
    "spatial_methods": "default_spatial_methods",
    "solver": "default_solver",
    "parameter_values": "default_parameter_values",
    "quick_plot_variables": "default_quick_plot_variables",
}


class ComposedModel(BaseModel):
    """
    A model built from given submodels, for developing and testing submodels (DESIGN D3).

    The submodels are merged and checked exactly as in the built-in models (see
    :class:`pytes.BaseModel`), so the result works with :class:`pybamm.Simulation`, the
    experiment runner and the conformance checks. A composed model is not an admitted model
    (DESIGN D1).

    Replacing one slot of an existing model::

        base = pytes.SharpFrontModel()
        storage = base.submodels["storage"]
        coupling = pytes.submodels.WallCoupling(
            base.param, base.param.fluid, storage.label, storage.storage_geometry,
            flux_law=MyLaw(),
        )
        model = pytes.ComposedModel(
            {**base.submodels, "coupling": coupling}, base.param, name="My model",
            defaults_from=base,
        )

    The submodels are reused, not modified, so ``base`` is unchanged. The
    :class:`pytes.submodels.DeviceEnergy` submodel refers to the storage and fluid
    submodels it was built with (for :func:`pytes.energy_between`); rebuild it when
    replacing them.

    Parameters
    ----------
    submodels : dict
        The submodels, by slot name, in order. They must have been built with ``param``.
    param : object
        The parameters the submodels were built with (a
        :class:`pytes.parameters.DeviceParameters`, for the controls).
    name : str, optional
        The name of the model (default "Composed model").
    defaults_from : :class:`pybamm.BaseModel`, optional
        A model whose defaults (geometry, mesh, spatial methods, solver, parameter values
        and quick-plot variables) are used where no explicit value is given.
    geometry, submesh_types, var_pts, spatial_methods, solver, parameter_values, \
quick_plot_variables : optional
        Explicit defaults, used by :class:`pybamm.Simulation` as the ``default_*``
        properties. Each overrides ``defaults_from``; without either, PyBaMM's default
        applies.

    Raises
    ------
    pytes.WiringError
        If the submodels do not fit together.
    ValueError
        If the geometry, submesh types or spatial methods miss a domain of the model's
        states.
    """

    def __init__(
        self, submodels, param, name="Composed model", defaults_from=None, **defaults
    ):
        unknown = set(defaults) - set(_DEFAULTS)
        if unknown:
            raise TypeError(f"Unexpected arguments: {sorted(unknown)}")
        self._given_submodels = dict(submodels)
        self._param = param
        self._defaults_from = defaults_from
        self._defaults = defaults
        super().__init__(name=name)
        self._check_domains_covered()

    def get_parameters(self):
        return self._param

    def set_submodels(self):
        self.submodels.update(self._given_submodels)

    def _default(self, argument):
        """The explicit value, else that of ``defaults_from``, else PyBaMM's"""
        if argument in self._defaults:
            # A copy, as PyBaMM processes some defaults (e.g. the geometry) in place
            return copy.deepcopy(self._defaults[argument])
        if self._defaults_from is not None:
            return getattr(self._defaults_from, _DEFAULTS[argument])
        return getattr(super(), _DEFAULTS[argument])

    def _check_domains_covered(self):
        """Raise if a domain of a state has no geometry, submesh type or spatial method"""
        domains = {
            domain
            for state in self.rhs | self.algebraic
            for level in state.domains.values()
            for domain in level
        }
        for argument in ("geometry", "submesh_types", "spatial_methods"):
            missing = domains - set(self._default(argument))
            if missing:
                raise ValueError(
                    f"{self.name}: the {argument.replace('_', ' ')} miss the domains "
                    f"{sorted(missing)}; pass {argument}= or defaults_from="
                )

    @property
    def default_geometry(self):
        return self._default("geometry")

    @property
    def default_submesh_types(self):
        return self._default("submesh_types")

    @property
    def default_var_pts(self):
        return self._default("var_pts")

    @property
    def default_spatial_methods(self):
        return self._default("spatial_methods")

    @property
    def default_solver(self):
        return self._default("solver")

    @property
    def default_parameter_values(self):
        return self._default("parameter_values")

    @property
    def default_quick_plot_variables(self):
        return self._default("quick_plot_variables")
