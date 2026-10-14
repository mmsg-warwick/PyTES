#
# Base model of the finned-pipe family
#
"""Base class of the finned-pipe family: the pipe, the PCM annulus and the defaults."""

import pybamm

from ... import compat
from ...submodels import AdvectedFluid, FlowPath
from ..base_model import BaseModel
from .parameter_values import get_parameter_values
from .parameters import FinnedPipeParameters


class BaseFinnedPipeModel(BaseModel):
    """
    Base model of the finned-pipe family: heat transfer fluid flowing along a pipe that
    exchanges heat with the surrounding PCM and fins. One pipe is modelled; device totals
    are multiplied by the number of pipes. See
    :mod:`pytes.models.finned_pipe.parameters` for the geometry and the assumptions.

    Attributes
    ----------
    y : pybamm.SpatialVariable
        Distance from the pipe axis [m], from the pipe radius to the PCM outer radius, in
        the "PCM vertical" domain (cylindrical coordinates).
    z : pybamm.SpatialVariable
        Distance along the pipe from the inlet [m], in the "pipe" domain.
    """

    def __init__(
        self, name, operating_mode="discharge", initial_state="state of charge"
    ):
        self.y = pybamm.SpatialVariable(
            "y",
            domains={"primary": "PCM vertical", "secondary": "pipe"},
            coord_sys="cylindrical polar",
        )
        self.z = pybamm.SpatialVariable(
            "z", domains={"primary": "pipe"}, coord_sys="cartesian"
        )
        super().__init__(
            name=name, operating_mode=operating_mode, initial_state=initial_state
        )

    def get_parameters(self):
        return FinnedPipeParameters()

    def fluid_submodel(self):
        """The heat transfer fluid in the pipes"""
        param = self.param
        flow_path = FlowPath(self.z, param.Z, param.area, param.N_pipes)
        return AdvectedFluid(param, param.fluid, flow_path)

    def integrate_over_pipe(self, symbol):
        """
        Integrate a symbol over one pipe: for a "PCM vertical" symbol, its integral over the
        annulus around the pipe, ``int int symbol 2 pi y dy dz``; for a "pipe" symbol,
        ``int symbol dz``.
        """
        if symbol.domain == ["PCM vertical"]:
            symbol = pybamm.Integral(symbol, self.y)
        return pybamm.Integral(symbol, self.z)

    @property
    def default_geometry(self):
        """
        The PCM annulus (``y`` from the pipe radius to the PCM outer radius) and the pipe
        (``z`` from 0 to the pipe length)
        """
        return pybamm.Geometry(
            {
                "PCM vertical": {self.y: {"min": self.param.R_f, "max": self.param.H}},
                "pipe": {self.z: {"min": pybamm.Scalar(0), "max": self.param.Z}},
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
    def default_var_pts(self):
        """Number of mesh points in each spatial variable"""
        return {self.y: 20, self.z: 20}

    @property
    def default_spatial_methods(self):
        """Finite volumes in every domain; the pipe uses the fluid's spatial method"""
        spatial_methods = {
            domain: pybamm.FiniteVolume() for domain in self.default_geometry
        }
        spatial_methods["pipe"] = compat.fluid_spatial_method()
        return spatial_methods

    @property
    def default_quick_plot_variables(self):
        """Variables shown by :class:`pybamm.QuickPlot` by default (DESIGN D15)"""
        return [
            ["Inlet temperature [degC]", "Outlet temperature [degC]"],
            "Heat transfer fluid temperature [degC]",
            "Power [kW]",
            "State of charge",
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
        """See :func:`pytes.models.finned_pipe.get_parameter_values`"""
        return get_parameter_values()
