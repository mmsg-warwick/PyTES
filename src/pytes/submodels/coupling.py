#
# Coupling submodels
#
"""
Coupling submodels: the coupling slot of DESIGN D5.

A coupling takes the fluid state and the storage surface state, returns the heat the fluid
gains per unit length of flow path, and imposes the matching boundary condition on the
storage. Where it can, the heat is taken from the receiving side's discrete energy balance
(the ledger, DESIGN D6), so that energy is conserved exactly.
"""

import pybamm

from .base_submodel import BaseSubModel
from .fluid import HEAT_GAIN


class LedgerWallCoupling(BaseSubModel):
    """
    A storage in direct contact with the flow path wall, exchanging heat with the fluid
    through a heat transfer coefficient ``h`` (from the fluid-property object).

    The storage sees ``-k dT/dn = h (T_f - T_s)`` at its inner surface, where ``T_s`` is
    its surface temperature. The heat the fluid gains is the heat the storage loses,
    computed from the storage's own discrete energy balance: minus the integral of
    ``dH/dt`` over the storage cross-section. This telescopes to the discrete flux at the
    wall, so energy is conserved exactly. (``h (T_s - T_f)`` times the perimeter differs
    slightly, as the storage flux uses the conductivity at the cell face rather than at
    the surface.)

    Parameters
    ----------
    param : object
        The model's parameters.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    storage : :class:`pytes.submodels.EnthalpyStorage`
        The storage.
    """

    provides = (HEAT_GAIN,)

    def __init__(self, param, fluid, storage, name="Wall coupling"):
        super().__init__(param, name)
        self.fluid = fluid
        self.storage = storage
        label = storage.label
        self._dHdt = f"{label} enthalpy rate of change [W.m-3]"
        self._T_s = f"{label} surface temperature [K]"
        self._H_s = f"{label} surface enthalpy [J.m-3]"
        self.requires = (
            "Heat transfer fluid temperature [K]",
            self._dHdt,
            self._T_s,
            self._H_s,
        )

    def get_coupled_variables(self, variables):
        dHdt = variables[self._dHdt]
        integral = self.storage.geometry.cross_section_integral(dHdt)
        variables[HEAT_GAIN] = -integral
        return variables

    def set_boundary_conditions(self, variables):
        storage = self.storage
        T_f = variables["Heat transfer fluid temperature [K]"]
        T_s = variables[self._T_s]
        h = self.fluid.heat_transfer_coefficient(T_f)
        k_s = storage.material.k(variables[self._H_s], storage.internal_states)
        # -k dT/dn = h (T_f - T_s), with n pointing into the storage
        gradient = h * (T_s - T_f) / k_s
        if storage.geometry.inner == "right":
            gradient = -gradient
        self.boundary_conditions[storage.T] = {
            storage.geometry.inner: (gradient, "Neumann")
        }


class FinRootCoupling(BaseSubModel):
    """
    Fins whose roots are on the flow path wall, exchanging heat with the fluid through a
    heat transfer coefficient ``h`` (from the fluid-property object).

    The heat the fluid exchanges over one fin pitch of wall enters through the fin root
    alone: ``-k_c dT_c/dy = (d_m / d_c) h (T_f - T_c)`` at the root. The heat the fluid
    gains per unit length is ``P h (T_c - T_f)``, with ``P`` the wall perimeter. Both use the
    same expression, so energy is conserved exactly.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``perimeter``, ``d_c`` and ``d_m``.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    fin : :class:`pytes.submodels.SensibleConduction`
        The fins.
    """

    provides = (HEAT_GAIN,)

    def __init__(self, param, fluid, fin, name="Fin root coupling"):
        super().__init__(param, name)
        self.fluid = fluid
        self.fin = fin
        self._T_c = f"{fin.label} surface temperature [K]"
        self.requires = ("Heat transfer fluid temperature [K]", self._T_c)

    def _wall_flux(self, variables):
        """Heat flux from the wall into the fluid [W.m-2]"""
        T_f = variables["Heat transfer fluid temperature [K]"]
        h = self.fluid.heat_transfer_coefficient(T_f)
        return h * (variables[self._T_c] - T_f)

    def get_coupled_variables(self, variables):
        variables[HEAT_GAIN] = self.param.perimeter * self._wall_flux(variables)
        return variables

    def set_boundary_conditions(self, variables):
        param = self.param
        fin = self.fin
        self.boundary_conditions[fin.T] = {
            fin.geometry.inner: (
                self._wall_flux(variables) / (fin.material.k * param.d_c / param.d_m),
                "Neumann",
            )
        }


class FinPCMCoupling(BaseSubModel):
    """
    Phase-change material between two fins, at the fin temperature where it touches a fin.

    The PCM sees ``T = T_c`` at the fin surface. The heat the fin gains per unit fin volume
    is minus the heat the PCM on both sides gains, computed from the PCM's own discrete
    energy balance: ``-(2 / d_c)`` times the integral of ``dH/dt`` across the half-gap
    (the flux at the midplane is zero). This telescopes to the discrete flux at the fin
    face, so energy is conserved exactly.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``d_c``.
    fin : :class:`pytes.submodels.SensibleConduction`
        The fins.
    pcm : :class:`pytes.submodels.EnthalpyStorage`
        The PCM between the fins.
    """

    def __init__(self, param, fin, pcm, name="Fin-PCM coupling"):
        super().__init__(param, name)
        self.fin = fin
        self.pcm = pcm
        self._dHdt = f"{pcm.label} enthalpy rate of change [W.m-3]"
        self._T_c = f"{fin.label} temperature [K]"
        self.requires = (self._dHdt, self._T_c)
        self.provides = (fin.source_variable,)

    def get_coupled_variables(self, variables):
        dHdt = variables[self._dHdt]
        variables[self.fin.source_variable] = (
            -2 / self.param.d_c * pybamm.Integral(dHdt, self.pcm.geometry.variable)
        )
        return variables

    def set_boundary_conditions(self, variables):
        pcm = self.pcm
        self.boundary_conditions[pcm.T] = {
            pcm.geometry.inner: (variables[self._T_c], "Dirichlet")
        }
