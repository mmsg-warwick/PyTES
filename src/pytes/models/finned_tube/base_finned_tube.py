#
# Base model of the finned-tube family
#
"""Base class of the finned-tube family: the tube, the PCM annulus and the defaults."""

import pybamm

from ... import compat
from ...submodels import AdvectedFluid, FlowPath, Gnielinski, NewtonCooling
from ..base_model import BaseModel
from .parameter_values import get_parameter_values
from .parameters import FinnedTubeParameters


class BaseFinnedTubeModel(BaseModel):
    """
    Base model of the finned-tube family: heat transfer fluid flowing along a tube that
    exchanges heat with the surrounding PCM and fins. One tube is modelled; device totals
    are multiplied by the number of tubes. See
    :mod:`pytes.models.finned_tube.parameters` for the geometry and the assumptions.

    Options:

    - "storage": "resolved" (default), the storage at every point along the tube; or
      "averaged", one storage cross-section standing for the average along the tube,
      exchanging heat with the fluid averaged along it (DESIGN D3, D4).
    - "heat transfer coefficient": "constant" (default), "Heat transfer coefficient
      [W.m-2.K-1]" (:class:`pytes.submodels.NewtonCooling`); or "Gnielinski", from the flow
      in the tube (:class:`pytes.submodels.Gnielinski`, issue #6).

    Parameters
    ----------
    name : str
        The name of the model.
    options : dict, optional
        The model's options.

    Attributes
    ----------
    y : pybamm.SpatialVariable
        Distance from the tube axis [m], from the tube radius to the storage outer radius ``R_f + D``, in
        the "storage depth" domain (cylindrical coordinates), with the "flow path" as its
        secondary domain unless the storage is averaged.
    z : pybamm.SpatialVariable
        Distance along the tube from the inlet [m], in the "flow path" domain.
    """

    allowed_options = {
        "storage": ("resolved", "averaged"),
        "heat transfer coefficient": ("constant", "Gnielinski"),
    }

    def __init__(self, name, options=None):
        super().__init__(name=name, options=options)

    @property
    def averaged(self):
        """Whether the storage is averaged along the tube"""
        return self.options["storage"] == "averaged"

    def storage_domains(self, *domains):
        """The given storage domains, then the flow path unless the storage is averaged"""
        domains = [*domains] if self.averaged else [*domains, "flow path"]
        return dict(zip(("primary", "secondary", "tertiary"), domains, strict=False))

    def set_spatial_variables(self):
        self.y = pybamm.SpatialVariable(
            "y",
            domains=self.storage_domains("storage depth"),
            coord_sys="cylindrical polar",
        )
        self.z = pybamm.SpatialVariable(
            "z", domains={"primary": "flow path"}, coord_sys="cartesian"
        )

    def get_parameters(self):
        return FinnedTubeParameters()

    @property
    def flow_path(self):
        """The flow paths: one per tube"""
        param = self.param
        return FlowPath(self.z, param.Z, param.area, param.N_tubes)

    def fluid_submodel(self):
        """The heat transfer fluid in the tubes"""
        return AdvectedFluid(self.param, self.param.fluid, self.flow_path)

    def flux_law(self):
        """The surface flux law at the tube wall, from the "heat transfer coefficient" option"""
        if self.options["heat transfer coefficient"] == "Gnielinski":
            return Gnielinski(self.param.R_f, self.param.N_tubes)
        return NewtonCooling()

    def storage_flow_path(self):
        """The flow path a storage geometry is averaged along, or None if resolved"""
        return self.flow_path if self.averaged else None

    def integrate_over_tube(self, symbol):
        """
        Integrate a symbol over one tube: for a "storage depth" symbol, its integral over the
        annulus around the tube, ``int int symbol 2 pi y dy dz``; for a "flow path" symbol,
        ``int symbol dz``. A storage averaged along the tube is the same at every ``z``,
        so its integral along the tube is the tube length times its value.
        """
        if symbol.domain == ["storage depth"]:
            symbol = pybamm.Integral(symbol, self.y)
        if symbol.domain == []:
            return self.param.Z * symbol
        return pybamm.Integral(symbol, self.z)

    @property
    def default_geometry(self):
        """
        The PCM annulus (``y`` from the tube radius to the storage outer radius ``R_f + D``) and the tube
        (``z`` from 0 to the tube length)
        """
        return pybamm.Geometry(
            {
                "storage depth": {self.y: {"min": self.param.R_f, "max": self.param.H}},
                "flow path": {self.z: {"min": pybamm.Scalar(0), "max": self.param.Z}},
            }
        )

    @property
    def default_submesh_types(self):
        """Uniform 1D meshes in every domain"""
        return {
            domain: pybamm.MeshGenerator(pybamm.Uniform1DSubMesh)
            for domain in self.default_geometry
        }

    @property
    def default_spatial_methods(self):
        """Finite volumes in every domain; the tube uses the fluid's spatial method"""
        spatial_methods = {
            domain: pybamm.FiniteVolume() for domain in self.default_geometry
        }
        spatial_methods["flow path"] = compat.fluid_spatial_method()
        return spatial_methods

    @property
    def default_quick_plot_variables(self):
        """Variables shown by :class:`pybamm.QuickPlot` by default (DESIGN D15)"""
        return [
            ["Inlet temperature [degC]", "Outlet temperature [degC]"],
            "Heat transfer fluid temperature [degC]",
            "Power [kW]",
            "Discharged energy [kWh]",
        ]

    @property
    def default_solver(self):
        """IDAKLU with ``rtol=1e-5`` and ``atol=1e-8``"""
        # Tighter than the IDAKLU defaults (rtol=1e-4, atol=1e-6): the PCM temperature is
        # computed from the enthalpy, so its error is only controlled through the
        # enthalpy (scaled by the latent heat). These keep the solver error in the PCM
        # temperature at about 0.05 K or less on the default meshes; the mush model needs
        # the tighter atol on its default mesh
        return pybamm.IDAKLUSolver(rtol=1e-5, atol=1e-8)

    @property
    def default_parameter_values(self):
        """See :func:`pytes.models.finned_tube.get_parameter_values`"""
        return get_parameter_values()
