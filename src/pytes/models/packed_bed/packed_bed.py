#
# Packed-bed model
#
"""Model of a packed bed of PCM capsules, with the capsules resolved along the bed."""

import pybamm

from ... import compat
from ...submodels import (
    AdvectedFluid,
    DeviceEnergy,
    EnthalpyStorage,
    FlowPath,
    HeatTransferCoefficientOptions,
    Jeffreson,
    LedgerWallCoupling,
    LumpedGeometry,
    LumpedStorage,
    PerAreaTotals,
    StorageGeometry,
)
from ..base_model import BaseModel
from .parameter_values import get_parameter_values
from .parameters import PackedBedParameters


class PackedBedModel(BaseModel):
    """
    Packed bed of spherical PCM capsules, with the fluid flowing through the voids. At each
    point along the bed, one capsule stands for all those at that position: heat flows by
    conduction across it ("capsule", radially from its centre) and into the fluid at its
    surface. See :mod:`pytes.models.packed_bed.parameters` for the geometry and the
    assumptions.

    Submodels:

    - "fluid": :class:`pytes.submodels.AdvectedFluid`, through the voids (flow area
      ``eps A``, a single flow path);
    - "storage": :class:`pytes.submodels.EnthalpyStorage` of the PCM in a capsule
      (spherical), exchanging heat at its surface; or, for a lumped capsule,
      :class:`pytes.submodels.LumpedStorage`;
    - "coupling": :class:`pytes.submodels.LedgerWallCoupling`, the fluid and the capsule
      surfaces (``3 (1 - eps) / R`` of surface per unit bed volume);
    - "device energy": :class:`pytes.submodels.DeviceEnergy`;
    - "per-area totals": :class:`pytes.submodels.PerAreaTotals`, the device totals per unit
      bed cross-sectional area (e.g. "Power per unit area [W.m-2]").

    Options:

    - "storage along flow path": "resolved" (default), a capsule at every point along the
      bed; or "averaged", one capsule standing for the average along the bed, exchanging
      heat with the fluid averaged along it (DESIGN D3, D4; the "reduced model" of the
      `encapsulated-LTES <https://github.com/mmsg-warwick/encapsulated-LTES>`_ repository).
    - "storage element": "resolved" (default), the temperature resolved across each
      capsule; "lumped", a uniform temperature in each capsule (issue #5), much cheaper,
      and accurate when the capsule's Biot number is small; or "lumped with Jeffreson", a
      lumped capsule whose heat transfer coefficient is corrected for the conduction
      inside it (:class:`pytes.submodels.Jeffreson`), whichever coefficient the "heat
      transfer coefficient" option gives.
    - "heat transfer coefficient": "constant" (default), "Heat transfer coefficient
      [W.m-2.K-1]" (:class:`pytes.submodels.NewtonCooling`); or a Nusselt correlation for
      the flow through the bed, by name: "Wakao-Kaguei"
      (:class:`pytes.submodels.WakaoKaguei`, issue #6), or any correlation registered for
      the flow ``"packed bed"`` with :func:`pytes.submodels.register_correlation`.

    Parameters
    ----------
    name : str, optional
        The name of the model.
    options : dict, optional
        The model's options.

    Attributes
    ----------
    r : pybamm.SpatialVariable
        Distance from the capsule centre [m], from 0 to the capsule radius, in the
        "capsule" domain (spherical), with the "flow path" as its secondary domain unless
        the storage is averaged. Not set for a lumped capsule.
    z : pybamm.SpatialVariable
        Distance along the bed from the inlet [m], in the "flow path" domain.
    """

    allowed_options = {
        "storage along flow path": ("resolved", "averaged"),
        "storage element": ("resolved", "lumped", "lumped with Jeffreson"),
        "heat transfer coefficient": HeatTransferCoefficientOptions("packed bed"),
    }

    def __init__(self, name="Packed bed model", options=None):
        super().__init__(name=name, options=options)

    @property
    def averaged(self):
        """Whether the capsules are averaged along the bed"""
        return self.options["storage along flow path"] == "averaged"

    @property
    def lumped(self):
        """Whether each capsule has a uniform temperature"""
        return self.options["storage element"].startswith("lumped")

    def set_spatial_variables(self):
        if not self.lumped:
            domains = {"primary": "capsule"}
            if not self.averaged:
                domains["secondary"] = "flow path"
            self.r = pybamm.SpatialVariable(
                "r", domains=domains, coord_sys="spherical polar"
            )
        self.z = pybamm.SpatialVariable(
            "z", domains={"primary": "flow path"}, coord_sys="cartesian"
        )

    def get_parameters(self):
        return PackedBedParameters()

    def set_submodels(self):
        param = self.param
        z = self.z

        if self.lumped:
            # The capsules take (1 - eps) A of bed volume per unit bed length
            def cross_section_integral(symbol):
                return param.A * (1 - param.eps) * symbol

        else:
            # The integral over r of a spherical symbol is over the capsule volume (it
            # includes 4 pi r**2); there are capsule_density capsules per unit bed volume
            def cross_section_integral(symbol):
                return param.A * param.capsule_density * pybamm.Integral(symbol, self.r)

        # An averaged capsule is the same at every z
        def integrate(symbol):
            per_length = cross_section_integral(symbol)
            if self.averaged:
                return param.Z * per_length
            return pybamm.Integral(per_length, z)

        flow_path = FlowPath(z, param.Z, param.flow_area, 1)
        fluid = AdvectedFluid(param, param.fluid, flow_path)
        if self.lumped:
            geometry = LumpedGeometry(
                integrate,
                cross_section_integral,
                3 / param.R,
                flow_path,
                averaged=self.averaged,
            )
            storage = LumpedStorage(param, param.pcm, geometry)
        else:
            geometry = StorageGeometry(
                self.r,
                integrate,
                cross_section_integral,
                inner="right",
                flow_path=flow_path if self.averaged else None,
            )
            storage = EnthalpyStorage(param, param.pcm, geometry)
        self.submodels["fluid"] = fluid
        self.submodels["storage"] = storage
        self.submodels["coupling"] = LedgerWallCoupling(
            param, param.fluid, storage.label, geometry, flux_law=self.flux_law(storage)
        )
        self.submodels["device energy"] = DeviceEnergy(param, fluid, [storage])
        self.submodels["per-area totals"] = PerAreaTotals(param, param.A)

    def flux_law(self, storage):
        """
        The surface flux law at the capsules, from the "heat transfer coefficient" option,
        corrected for the conduction inside the capsule with "storage element": "lumped
        with Jeffreson"
        """
        values = self.allowed_options["heat transfer coefficient"]
        law = values.flux_law(
            self.options["heat transfer coefficient"], self.param.R, self.param.A
        )
        if self.options["storage element"] == "lumped with Jeffreson":
            law = Jeffreson(
                law,
                self.param.R,
                f"{storage.label} thermal conductivity [W.m-1.K-1]",
                storage.storage_geometry.boundary_domain,
            )
        return law

    @property
    def default_geometry(self):
        """
        A capsule (``r`` from 0 to the capsule radius), unless it is lumped, and the bed
        (``z``)
        """
        geometry = {
            "flow path": {self.z: {"min": pybamm.Scalar(0), "max": self.param.Z}}
        }
        if not self.lumped:
            geometry["capsule"] = {
                self.r: {"min": pybamm.Scalar(0), "max": self.param.R}
            }
        return pybamm.Geometry(geometry)

    @property
    def default_submesh_types(self):
        """Uniform 1D meshes in every domain"""
        return {
            domain: pybamm.MeshGenerator(pybamm.Uniform1DSubMesh)
            for domain in self.default_geometry
        }

    @property
    def default_var_pts(self):
        """
        Number of mesh points in each spatial variable (F-052). The error comes mostly from
        ``r``, and falls slowly with it because of the melting front inside the capsules.
        For the default charge, against 160 points in ``r`` (40 in ``z``), 40 give 0.27 K
        on average in the outlet temperature and 1.8 % in the stored energy; against 640
        points in ``z`` (40 in ``r``), 40 give 0.063 K and 0.33 %, and 5.4 K at most, in a
        short spike as the front leaves the bed. It solves in about 1.5 s. A lumped capsule
        has no ``r``.
        """
        if self.lumped:
            return {self.z: 40}
        return {self.r: 40, self.z: 40}

    @property
    def default_spatial_methods(self):
        """Finite volumes in every domain; the bed uses the fluid's spatial method"""
        methods = {"flow path": compat.fluid_spatial_method()}
        if not self.lumped:
            methods["capsule"] = pybamm.FiniteVolume()
        return methods

    @property
    def default_quick_plot_variables(self):
        """Variables shown by :class:`pybamm.QuickPlot` by default (DESIGN D15)"""
        return [
            ["Inlet temperature [degC]", "Outlet temperature [degC]"],
            "Heat transfer fluid temperature [degC]",
            "Power [kW]",
            "Average liquid fraction",
        ]

    @property
    def default_solver(self):
        """IDAKLU with ``rtol=1e-5`` and ``atol=1e-8``, as for the finned-tube family"""
        return pybamm.IDAKLUSolver(rtol=1e-5, atol=1e-8)

    @property
    def default_parameter_values(self):
        """See :func:`pytes.models.packed_bed.get_parameter_values`"""
        return get_parameter_values()
