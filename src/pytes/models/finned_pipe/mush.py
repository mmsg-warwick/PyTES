#
# Mush model of the finned-pipe family
#
"""Finned-pipe model that resolves the fins and the PCM between them."""

import pybamm

from ...submodels import (
    DeviceEnergy,
    EnthalpyStorage,
    FinPCMCoupling,
    FinRootCoupling,
    StorageGeometry,
)
from .base_finned_pipe import BaseFinnedPipeModel


class MushModel(BaseFinnedPipeModel):
    """
    Finned-pipe model that resolves the fins and the PCM separately. Heat flows from the
    pipe wall along annular fins ("PCM vertical") and from the fins into the PCM between
    them ("PCM horizontal"), at each point along the pipe.

    The PCM only exchanges heat with the fins: it does not touch the pipe wall, and heat
    flows through it only across the gap between two fins (in ``x``), not radially or along
    the pipe. By symmetry, only half the gap is modelled, from the fin surface
    (``x = d_c / 2``) to the midplane (``x = d_m / 2``). The PCM uses the properties of the
    PCM on its own (:class:`pytes.materials.PureMaterial`).

    Submodels:

    - "fluid": :class:`pytes.submodels.AdvectedFluid`;
    - "storage": :class:`pytes.submodels.EnthalpyStorage` of the PCM across the half-gap
      (cartesian);
    - "fins": :class:`pytes.submodels.EnthalpyStorage` of the fin metal, radially along
      the fins (cylindrical);
    - "coupling": :class:`pytes.submodels.FinRootCoupling`, the fluid and the fin roots;
    - "fin-PCM coupling": :class:`pytes.submodels.FinPCMCoupling`;
    - "device energy": :class:`pytes.submodels.DeviceEnergy`.

    Parameters
    ----------
    name : str, optional
        The name of the model.

    Attributes
    ----------
    x : pybamm.SpatialVariable
        Distance from the fin centreline [m], from half the fin thickness to half the fin
        pitch, in the "PCM horizontal" domain.
    """

    def __init__(self, name="Mush model"):
        self.x = pybamm.SpatialVariable(
            "x",
            domains={
                "primary": "PCM horizontal",
                "secondary": "PCM vertical",
                "tertiary": "pipe",
            },
            coord_sys="cartesian",
        )
        super().__init__(name=name)

    def set_submodels(self):
        param = self.param
        x, y = self.x, self.y

        # The PCM between two fins spans x in [d_c / 2, d_m / 2] (by symmetry), so
        # integrating over x and multiplying by 2 / d_m gives the PCM per unit length of
        # the fin pitch
        def integrate_pcm(symbol):
            return param.N_pipes * self.integrate_over_pipe(
                2 / param.d_m * pybamm.Integral(symbol, x)
            )

        def pcm_cross_section(symbol):
            return pybamm.Integral(2 / param.d_m * pybamm.Integral(symbol, x), y)

        # The fins take up a fraction delta of the annulus
        def integrate_fin(symbol):
            return param.N_pipes * self.integrate_over_pipe(param.delta * symbol)

        def fin_cross_section(symbol):
            return pybamm.Integral(param.delta * symbol, y)

        fluid = self.fluid_submodel()
        pcm_geometry = StorageGeometry(x, integrate_pcm, pcm_cross_section)
        pcm = EnthalpyStorage(
            param, param.pcm, pcm_geometry, inner_condition="temperature"
        )
        fin_geometry = StorageGeometry(y, integrate_fin, fin_cross_section)
        # The fin metal is a sensible material, its enthalpy scaled like the temperatures
        fins = EnthalpyStorage(
            param,
            param.metal,
            fin_geometry,
            label="Fin",
            heat_source=True,
            H_scale=param.metal.rho_c_p * param.temperature_scale,
            H_reference=param.metal.T2H(param.temperature_reference),
        )
        self.submodels["fluid"] = fluid
        self.submodels["storage"] = pcm
        self.submodels["fins"] = fins
        self.submodels["coupling"] = FinRootCoupling(
            param, param.fluid, fins.label, fin_geometry
        )
        self.submodels["fin-PCM coupling"] = FinPCMCoupling(
            param, pcm.label, pcm_geometry, fins.label
        )
        self.submodels["device energy"] = DeviceEnergy(param, fluid, [pcm, fins])

    @property
    def default_geometry(self):
        """
        That of :class:`BaseFinnedPipeModel`, plus the half-gap between two fins (``x``
        from half the fin thickness to half the fin pitch)
        """
        geometry = super().default_geometry
        geometry["PCM horizontal"] = {
            self.x: {"min": self.param.d_c / 2, "max": self.param.d_m / 2}
        }
        return geometry

    @property
    def default_var_pts(self):
        """
        Number of mesh points in each spatial variable. 10 points in ``x`` change the
        outlet temperature by about 0.02 K and are about 4 times faster
        """
        return {self.x: 20, self.y: 20, self.z: 20}
