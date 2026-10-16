#
# Surface flux laws
#
"""
Surface flux laws: the heat flux across the surface between the fluid and a storage, used by
the couplings (DESIGN D6).

The couplings take the heat from the storage side's discrete energy balance (the ledger), so
energy is conserved exactly whatever law gives the flux. A law is therefore a replaceable
part of a coupling: Newton's law of cooling is the default, and others (a series wall or
contact resistance, a nonlinear or radiative law, a flow-dependent coefficient) need no
change to the conservation logic.
"""

from dataclasses import dataclass

import pybamm


@dataclass(frozen=True)
class FluidState:
    """
    The fluid side of a surface, as a surface flux law sees it (DESIGN D6). New fields may
    be added (e.g. for a refrigerant) without breaking existing laws, which read only the
    fields they need.

    Attributes
    ----------
    h : pybamm.Symbol
        Specific enthalpy of the fluid [J.kg-1].
    T : pybamm.Symbol
        Temperature of the fluid [K], ``fluid.T(h)``.
    mass_flow_rate : pybamm.Symbol
        Mass flow rate through the whole device [kg.s-1]. A law built for a family
        converts it to the flow it needs (per tube, per unit area) from that family's
        geometry.
    p : pybamm.Symbol or None
        Pressure [Pa]; None while the models do not compute it.
    """

    h: pybamm.Symbol
    T: pybamm.Symbol
    mass_flow_rate: pybamm.Symbol
    p: pybamm.Symbol | None = None


class SurfaceFluxLaw:
    """
    Base class of the surface flux laws.

    Subclasses implement :meth:`heat_flux`. Geometry a law needs (e.g. a hydraulic
    diameter, for a correlation) is passed to its constructor by the family; the fluid's
    state, flow included, comes with each call as a :class:`FluidState`.
    """

    def heat_flux(self, fluid, fluid_state, T_s):
        """
        Heat flux [W.m-2] from the fluid into the storage surface.

        Parameters
        ----------
        fluid : object
            The fluid-property object, for properties at the fluid state.
        fluid_state : :class:`FluidState`
            The fluid's state at the surface.
        T_s : pybamm.Symbol
            Temperature of the storage surface [K].

        Returns
        -------
        pybamm.Symbol
            The heat flux, positive into the storage.
        """
        raise NotImplementedError


class NewtonCooling(SurfaceFluxLaw):
    """
    Newton's law of cooling, ``h (T_f - T_s)``, with a constant heat transfer coefficient
    ``h``.

    Parameters
    ----------
    name : str, optional
        Name of the coefficient parameter (default "Heat transfer coefficient
        [W.m-2.K-1]").

    Attributes
    ----------
    coefficient : pybamm.Parameter
        The heat transfer coefficient [W.m-2.K-1].
    """

    def __init__(self, name="Heat transfer coefficient [W.m-2.K-1]"):
        self.coefficient = pybamm.Parameter(name)

    def heat_flux(self, fluid, fluid_state, T_s):
        return self.coefficient * (fluid_state.T - T_s)
