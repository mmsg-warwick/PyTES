#
# Sharp-front model of the finned-tube family
#
"""Finned-tube model in which the PCM and the fins are homogenised."""

import pybamm

from ...submodels import (
    DeviceEnergy,
    EnthalpyStorage,
    LedgerWallCoupling,
    StorageGeometry,
)
from .base_finned_tube import BaseFinnedTubeModel


class SharpFrontModel(BaseFinnedTubeModel):
    """
    Finned-tube model in which the PCM and the fins are homogenised into a single composite
    material (:class:`pytes.materials.CompositeMaterial`), with heat conduction across the
    PCM ("storage depth", radially from the tube) at each point along the tube. With a sharp
    melting point and no smoothing ("PCM melting range [K]" and "PCM smoothing width [K]"
    both 0) the melting front is sharp, hence the name.

    Submodels:

    - "fluid": :class:`pytes.submodels.AdvectedFluid`;
    - "storage": :class:`pytes.submodels.EnthalpyStorage` of the composite, in cylindrical
      coordinates;
    - "coupling": :class:`pytes.submodels.LedgerWallCoupling`, the composite touching the
      tube wall;
    - "device energy": :class:`pytes.submodels.DeviceEnergy`.

    Parameters
    ----------
    name : str, optional
        The name of the model.
    options : dict, optional
        The model's options; see :class:`BaseFinnedTubeModel`.
    """

    def __init__(self, name="Sharp front model", options=None):
        super().__init__(name=name, options=options)

    def set_submodels(self):
        param = self.param
        y = self.y

        def integrate(symbol):
            return param.N_tubes * self.integrate_over_tube(symbol)

        def cross_section_integral(symbol):
            # The integral in cylindrical coordinates includes 2 pi y
            return pybamm.Integral(symbol, y)

        geometry = StorageGeometry(
            y,
            integrate,
            cross_section_integral,
            inner="left",
            flow_path=self.storage_flow_path(),
        )
        fluid = self.fluid_submodel()
        # The PCM and the fins are homogenised into a composite material, which keeps the
        # "Phase-change material" variable names
        storage = EnthalpyStorage(param, param.composite, geometry)
        self.submodels["fluid"] = fluid
        self.submodels["storage"] = storage
        self.submodels["coupling"] = LedgerWallCoupling(
            param, param.fluid, storage.label, geometry, flux_law=self.flux_law()
        )
        self.submodels["device energy"] = DeviceEnergy(param, fluid, [storage])

    @property
    def default_var_pts(self):
        """
        Number of mesh points in each spatial variable, with about the same error from each
        (F-052). For the default discharge, against 160 points in either and 20 or 40 in
        the other, ``y`` gives 0.054 K on average in the outlet temperature and 0.11 % in
        the stored energy, and ``z`` 0.066 K and 0.12 %, in about 1 s; 40 by 40 gives about
        a quarter of these errors, in about 5 times as long.
        """
        return {self.y: 20, self.z: 20}
