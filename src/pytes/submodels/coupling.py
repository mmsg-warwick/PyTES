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

    The heat flux into the storage is given by the surface flux law from the fluid state and
    the storage surface temperature ``T_s`` (by default ``h (T_f - T_s)``). The heat the fluid gains is the heat the storage loses, computed from the
    storage's own discrete energy balance: minus the integral of ``dH/dt`` over the storage
    cross-section. This telescopes to the discrete flux at the wall, so energy is conserved
    exactly, whatever the flux law. (The flux times the perimeter differs slightly, as the
    storage flux uses the conductivity at the cell face rather than at the surface.)

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
    """

    def __init__(
        self, param, fluid, label, geometry, flux_law=None, name="Wall coupling"
    ):
        self.fluid = fluid
        self.label = label
        self.storage_geometry = geometry
        self.flux_law = flux_law or NewtonCooling()
        super().__init__(param, name)

    def build(self):
        label = self.label
        geometry = self.storage_geometry
        dHdt = self.coupled(
            f"{label} enthalpy rate of change [W.m-3]", geometry.primary_domain
        )
        h_f = self.coupled(FLUID_ENTHALPY, "pipe")
        T_f = self.coupled(FLUID_TEMPERATURE, "pipe")
        T_s = self.coupled(f"{label} surface temperature [K]", geometry.boundary_domain)
        self.variables = {
            HEAT_GAIN: -geometry.cross_section_integral(dHdt),
            f"{label} boundary heat flux [W.m-2]": self.flux_law.heat_flux(
                self.fluid, h_f, T_f, T_s
            ),
        }


class FinRootCoupling(BaseSubModel):
    """
    Fins whose roots are on the flow path wall, exchanging heat with the fluid.

    The surface flux law gives the heat flux ``q`` from the fluid into the wall, at the fin
    temperature ``T_c`` (by default ``h (T_f - T_c)``). The heat the fluid exchanges over one
    fin pitch of wall enters through the fin root alone, so the heat flux into the fin root
    is ``(d_m / d_c) q``. The heat the fluid gains per unit length is ``-P q``, with ``P``
    the wall perimeter. Both use the same expression, so energy is conserved exactly.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``perimeter``, ``d_c`` and ``d_m``.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    label : str, optional
        The fins' label (see :class:`pytes.submodels.SensibleConduction`, default "Fin").
    flux_law : :class:`pytes.submodels.SurfaceFluxLaw`, optional
        The surface flux law (default :class:`pytes.submodels.NewtonCooling`).
    """

    def __init__(
        self, param, fluid, label="Fin", flux_law=None, name="Fin root coupling"
    ):
        self.fluid = fluid
        self.label = label
        self.flux_law = flux_law or NewtonCooling()
        super().__init__(param, name)

    def build(self):
        param = self.param
        h_f = self.coupled(FLUID_ENTHALPY, "pipe")
        T_f = self.coupled(FLUID_TEMPERATURE, "pipe")
        T_c = self.coupled(f"{self.label} surface temperature [K]", "pipe")
        # Heat flux from the fluid into the wall [W.m-2]
        wall_flux = self.flux_law.heat_flux(self.fluid, h_f, T_f, T_c)
        self.variables = {
            HEAT_GAIN: -param.perimeter * wall_flux,
            f"{self.label} boundary heat flux [W.m-2]": param.d_m
            / param.d_c
            * wall_flux,
        }


class FinPCMCoupling(BaseSubModel):
    """
    Phase-change material between two fins, at the fin temperature where it touches a fin.

    The PCM's boundary temperature is the fin temperature. The heat the fin gains per unit
    fin volume is minus the heat the PCM on both sides gains, computed from the PCM's own
    discrete energy balance: ``-(2 / d_c)`` times the integral of ``dH/dt`` across the
    half-gap (the flux at the midplane is zero). This telescopes to the discrete flux at the
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
        dHdt = self.coupled(
            f"{self.pcm_label} enthalpy rate of change [W.m-3]",
            geometry.primary_domain,
        )
        T_c = self.coupled(
            f"{self.fin_label} temperature [K]", geometry.boundary_domain
        )
        fin_source = -2 / self.param.d_c * pybamm.Integral(dHdt, geometry.variable)
        self.variables = add_temperature_variables(
            {f"{self.fin_label} heat source [W.m-3]": fin_source},
            {f"{self.pcm_label} boundary temperature [K]": T_c},
        )
