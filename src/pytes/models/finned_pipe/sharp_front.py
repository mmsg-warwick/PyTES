#
# Sharp-front model of the finned-pipe family
#
"""Finned-pipe model in which the PCM and the fins are homogenised."""

import pybamm

from ...submodels import (
    DeviceEnergy,
    EnthalpyStorage,
    LedgerWallCoupling,
    StorageGeometry,
)
from .base_finned_pipe import BaseFinnedPipeModel


class SharpFrontModel(BaseFinnedPipeModel):
    """
    Finned-pipe model in which the PCM and the fins are homogenised into a single composite
    material (:class:`pytes.materials.CompositeMaterial`), with heat conduction across the
    PCM ("PCM vertical", radially from the pipe) at each point along the pipe. With a sharp
    melting point and no smoothing ("PCM melting range [K]" and "PCM smoothing width [K]"
    both 0) the melting front is sharp, hence the name.

    Submodels:

    - "fluid": :class:`pytes.submodels.AdvectedFluid`;
    - "storage": :class:`pytes.submodels.EnthalpyStorage` of the composite, in cylindrical
      coordinates;
    - "coupling": :class:`pytes.submodels.LedgerWallCoupling`, the composite touching the
      pipe wall;
    - "device energy": :class:`pytes.submodels.DeviceEnergy`.

    Parameters
    ----------
    name : str, optional
        The name of the model.
    """

    def __init__(self, name="Sharp front model"):
        super().__init__(name=name)

    def set_submodels(self):
        param = self.param
        y = self.y

        def integrate(symbol):
            return param.N_pipes * self.integrate_over_pipe(symbol)

        def cross_section_integral(symbol):
            # The integral in cylindrical coordinates includes 2 pi y
            return pybamm.Integral(symbol, y)

        geometry = StorageGeometry(y, integrate, cross_section_integral, inner="left")
        fluid = self.fluid_submodel()
        # The PCM and the fins are homogenised into a composite material, which keeps the
        # "Phase-change material" variable names
        storage = EnthalpyStorage(param, param.composite, geometry)
        self.submodels["fluid"] = fluid
        self.submodels["storage"] = storage
        self.submodels["coupling"] = LedgerWallCoupling(
            param, param.fluid, storage.label, geometry
        )
        self.submodels["device energy"] = DeviceEnergy(param, fluid, [storage])

    @property
    def default_var_pts(self):
        """Number of mesh points in each spatial variable"""
        return {self.y: 40, self.z: 40}
