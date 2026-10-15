#
# Coupling submodels
#
"""
Coupling submodels: the coupling slot of DESIGN D5.

A coupling takes the fluid state and the storage surface state, provides the heat the fluid
gains per unit length of flow path, and provides the condition the storage applies on its
inner side (a heat flux into it, or a temperature). Where it can, the heat is taken from the
receiving side's discrete energy balance (the ledger, DESIGN D6), so that energy is
conserved exactly. The heat flux across a fluid-storage surface comes from a replaceable
surface flux law (:mod:`pytes.submodels.flux_laws`), Newton's law of cooling by default.
"""

import pybamm

from ..variables import add_temperature_variables
from .base_submodel import BaseSubModel
from .fluid import FLUID_ENTHALPY, FLUID_TEMPERATURE, HEAT_GAIN
from .flux_laws import NewtonCooling


class LedgerWallCoupling(BaseSubModel):
    """
    A storage in direct contact with the flow path wall, exchanging heat with the fluid.

    The heat flux into the storage is ``flux_factor`` times the surface flux law's flux
    from the fluid state and the storage surface temperature ``T_s`` (by default
    ``h (T_f - T_s)``). The heat the fluid gains is the heat the storage loses through its
    boundaries, computed from the storage's own discrete energy balance: minus the integral
    of its conduction heating rate over the storage cross-section (the ledger, DESIGN D6).
    This telescopes to the discrete flux at the wall, so energy is conserved exactly,
    whatever the flux law or the conductivity. (The flux times the perimeter differs
    slightly, as the storage flux uses the conductivity at the cell face rather than at the
    surface.)

    Parameters
    ----------
    param : object
        The model's parameters.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    label : str
        The storage's label (see :class:`pytes.submodels.EnthalpyStorage`).
    geometry : :class:`pytes.submodels.StorageGeometry`
        The storage's geometry.
    flux_law : :class:`pytes.submodels.SurfaceFluxLaw`, optional
        The surface flux law (default :class:`pytes.submodels.NewtonCooling`).
    flux_factor : pybamm.Symbol or float, optional
        Ratio of the wall area to the storage's inner surface area (default 1).
    """

    def __init__(
        self,
        param,
        fluid,
        label,
        geometry,
        flux_law=None,
        flux_factor=1,
        name="Wall coupling",
    ):
        self.fluid = fluid
        self.label = label
        self.storage_geometry = geometry
        self.flux_law = flux_law or NewtonCooling()
        self.flux_factor = flux_factor
        super().__init__(param, name)

    def build(self):
        label = self.label
        geometry = self.storage_geometry
        conduction = self.coupled(
            f"{label} conduction heating rate [W.m-3]", geometry.primary_domain
        )
        h_f = self.coupled(FLUID_ENTHALPY, "flow path")
        T_f = self.coupled(FLUID_TEMPERATURE, "flow path")
        T_s = self.coupled(f"{label} surface temperature [K]", geometry.boundary_domain)
        heat_flux = self.flux_law.heat_flux(self.fluid, h_f, T_f, T_s)
        self.variables = {
            HEAT_GAIN: -geometry.cross_section_integral(conduction),
            f"{label} boundary heat flux [W.m-2]": self.flux_factor * heat_flux,
        }


class FinRootCoupling(LedgerWallCoupling):
    """
    Fins whose roots are on the flow path wall, exchanging heat with the fluid.

    The heat the fluid exchanges over one fin pitch of wall enters through the fin root
    alone, so the heat flux into the fin root is ``d_m / d_c`` times the surface flux law's
    flux. The heat the fluid gains is taken from the fins' discrete energy balance, as in
    :class:`LedgerWallCoupling`, so energy is conserved exactly.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``d_c`` and ``d_m``.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    label : str
        The fins' label (see :class:`pytes.submodels.EnthalpyStorage`).
    geometry : :class:`pytes.submodels.StorageGeometry`
        The fins' geometry.
    flux_law : :class:`pytes.submodels.SurfaceFluxLaw`, optional
        The surface flux law (default :class:`pytes.submodels.NewtonCooling`).
    """

    def __init__(
        self, param, fluid, label, geometry, flux_law=None, name="Fin root coupling"
    ):
        super().__init__(
            param,
            fluid,
            label,
            geometry,
            flux_law=flux_law,
            flux_factor=param.d_m / param.d_c,
            name=name,
        )


class FinPCMCoupling(BaseSubModel):
    """
    Phase-change material between two fins, at the fin temperature where it touches a fin.

    The PCM's boundary temperature is the fin temperature. The heat the fin gains per unit
    fin volume is minus the heat the PCM on both sides gains through the fin face, computed
    from the PCM's own discrete energy balance: ``-(2 / d_c)`` times the integral of its
    conduction heating rate across the half-gap (the flux at the midplane is zero). This telescopes to the discrete flux at the
    fin face, so energy is conserved exactly.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``d_c``.
    pcm_label : str
        The PCM's label (see :class:`pytes.submodels.EnthalpyStorage`).
    pcm_geometry : :class:`pytes.submodels.StorageGeometry`
        The PCM's geometry (across the half-gap).
    fin_label : str, optional
        The fins' label (default "Fin").
    """

    def __init__(
        self, param, pcm_label, pcm_geometry, fin_label="Fin", name="Fin-PCM coupling"
    ):
        self.pcm_label = pcm_label
        self.pcm_geometry = pcm_geometry
        self.fin_label = fin_label
        super().__init__(param, name)

    def build(self):
        geometry = self.pcm_geometry
        conduction = self.coupled(
            f"{self.pcm_label} conduction heating rate [W.m-3]",
            geometry.primary_domain,
        )
        T_c = self.coupled(
            f"{self.fin_label} temperature [K]", geometry.boundary_domain
        )
        fin_source = (
            -2 / self.param.d_c * pybamm.Integral(conduction, geometry.variable)
        )
        self.variables = add_temperature_variables(
            {f"{self.fin_label} heat source [W.m-3]": fin_source},
            {f"{self.pcm_label} boundary temperature [K]": T_c},
        )
