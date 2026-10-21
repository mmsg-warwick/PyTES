#
# Surface flux laws
#
"""
Surface flux laws: the heat flux across the surface between the fluid and a storage, used by
the couplings (DESIGN D6).

The couplings take the heat from the storage side's discrete energy balance (the ledger), so
energy is conserved exactly whatever law gives the flux. A law is therefore a replaceable
part of a coupling: Newton's law of cooling is the default, and others (a series wall or
contact resistance, a nonlinear or radiative law) need no change to the conservation logic.
Flow-dependent coefficients come from Nusselt number correlations
(:class:`NusseltCorrelation`): :class:`Gnielinski` inside tubes and :class:`WakaoKaguei` in
packed beds.
"""

from dataclasses import dataclass

import numpy as np
import pybamm

HEAT_TRANSFER_COEFFICIENT = "Heat transfer coefficient [W.m-2.K-1]"


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

    def variables(self, fluid, fluid_state):
        """
        Variables the law adds to the coupling's (e.g. its heat transfer coefficient), by
        name; none by default.
        """
        return {}


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

    def heat_transfer_coefficient(self, fluid, fluid_state):
        """
        The heat transfer coefficient [W.m-2.K-1] at the fluid state.

        Parameters
        ----------
        fluid : object
            The fluid-property object.
        fluid_state : :class:`FluidState`
            The fluid's state at the surface.
        """
        return self.coefficient

    def heat_flux(self, fluid, fluid_state, T_s):
        h = self.heat_transfer_coefficient(fluid, fluid_state)
        return h * (fluid_state.T - T_s)

    def variables(self, fluid, fluid_state):
        """The heat transfer coefficient, as "Heat transfer coefficient [W.m-2.K-1]\""""
        return {
            HEAT_TRANSFER_COEFFICIENT: self.heat_transfer_coefficient(
                fluid, fluid_state
            )
        }


class NusseltCorrelation(NewtonCooling):
    """
    Newton's law of cooling with a heat transfer coefficient from a Nusselt number
    correlation, ``h = Nu k / L``, with ``Nu`` a function of the Reynolds and Prandtl
    numbers (issue #6):

    ``Re = mdot_path L / (A mu)``,  ``Pr = mu c_p / k``,

    where ``mdot_path`` is the mass flow rate per flow path, ``L`` the characteristic
    length of the correlation, ``A`` the area its velocity is based on, and the properties
    ``mu``, ``c_p`` and ``k`` come from the fluid-property object at the fluid state. The
    flow may run either way: the Reynolds number uses the flow's magnitude.

    Subclasses implement :meth:`nusselt`. The correlation's constants are part of it, so a
    correlation has no parameters of its own: the geometry comes from the family, through
    the constructor.

    Parameters
    ----------
    length : pybamm.Symbol
        The characteristic length ``L`` [m] (a hydraulic or particle diameter).
    area : pybamm.Symbol
        The area ``A`` [m2] the velocity is based on, per flow path.
    n_paths : pybamm.Symbol or float, optional
        Number of flow paths sharing the device's mass flow rate (default 1).
    """

    def __init__(self, length, area, n_paths=1):
        self.length = length
        self.area = area
        self.n_paths = n_paths

    def reynolds(self, fluid, fluid_state):
        """The Reynolds number at the fluid state"""
        mdot_path = pybamm.AbsoluteValue(fluid_state.mass_flow_rate) / self.n_paths
        return mdot_path * self.length / (self.area * fluid.mu(fluid_state.h))

    def prandtl(self, fluid, fluid_state):
        """The Prandtl number at the fluid state"""
        h = fluid_state.h
        return fluid.mu(h) * fluid.c_p(h) / fluid.k(h)

    def nusselt(self, Re, Pr):
        """The Nusselt number from the Reynolds and Prandtl numbers"""
        raise NotImplementedError

    def heat_transfer_coefficient(self, fluid, fluid_state):
        Re = self.reynolds(fluid, fluid_state)
        Pr = self.prandtl(fluid, fluid_state)
        return self.nusselt(Re, Pr) * fluid.k(fluid_state.h) / self.length

    def variables(self, fluid, fluid_state):
        """
        The heat transfer coefficient, and the Reynolds, Prandtl and Nusselt numbers of
        the surface
        """
        Re = self.reynolds(fluid, fluid_state)
        Pr = self.prandtl(fluid, fluid_state)
        return {
            **super().variables(fluid, fluid_state),
            "Surface Reynolds number": Re,
            "Surface Prandtl number": Pr,
            "Surface Nusselt number": self.nusselt(Re, Pr),
        }


class Gnielinski(NusseltCorrelation):
    """
    Fully developed flow in a smooth tube: the Gnielinski correlation in turbulent flow, the
    laminar Nusselt number at a uniform wall temperature, 3.66, below ``Re = 2300``, and
    a linear interpolation between them in the transition, as in the VDI Heat Atlas
    (Gnielinski, "On heat transfer in tubes", International Journal of Heat and Mass
    Transfer 63, 2013):

    - ``Nu = 3.66`` for ``Re <= 2300``;
    - ``Nu = (1 - g) 3.66 + g Nu_t(10^4)``, ``g = (Re - 2300) / (10^4 - 2300)``, for
      ``2300 < Re < 10^4``;
    - ``Nu = Nu_t(Re)`` for ``Re >= 10^4``, with
      ``Nu_t = (f / 8) (Re - 1000) Pr / (1 + 12.7 sqrt(f / 8) (Pr^(2/3) - 1))`` and the
      friction factor ``f = (0.79 ln(Re) - 1.64)^-2``.

    The entrance region and the variation of the properties between the bulk and the wall
    are neglected. The Nusselt number is continuous in ``Re``; its slope is not, at
    ``Re = 2300`` and ``10^4``.

    Parameters
    ----------
    radius : pybamm.Symbol
        The tube radius [m]; the characteristic length is the diameter.
    n_tubes : pybamm.Symbol or float, optional
        Number of tubes sharing the device's mass flow rate (default 1).
    """

    #: Laminar Nusselt number, fully developed flow at a uniform wall temperature
    nusselt_laminar = 3.66
    #: Reynolds numbers at which the transition starts and ends
    reynolds_transition = (2300, 1e4)

    def __init__(self, radius, n_tubes=1):
        super().__init__(2 * radius, np.pi * radius**2, n_tubes)

    def nusselt_turbulent(self, Re, Pr):
        """The Gnielinski correlation, for ``Re >= 10^4``"""
        f = (0.79 * pybamm.log(Re) - 1.64) ** -2
        return (
            (f / 8)
            * (Re - 1000)
            * Pr
            / (1 + 12.7 * pybamm.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
        )

    def nusselt(self, Re, Pr):
        Re_lam, Re_turb = self.reynolds_transition
        g = pybamm.minimum(pybamm.maximum((Re - Re_lam) / (Re_turb - Re_lam), 0), 1)
        Nu_turb = self.nusselt_turbulent(pybamm.maximum(Re, Re_turb), Pr)
        return (1 - g) * self.nusselt_laminar + g * Nu_turb


class WakaoKaguei(NusseltCorrelation):
    """
    Fluid to particle heat transfer in a packed bed: the correlation of Wakao, Kaguei and
    Funazkri (Chemical Engineering Science 34, 1979, 325-336),
    ``Nu = 2 + 1.1 Re^0.6 Pr^(1/3)``, with the particle diameter as the characteristic
    length and the superficial velocity (the mass flow rate over the whole bed
    cross-section) in the Reynolds number. Fitted for ``15 < Re < 8500``.

    Parameters
    ----------
    radius : pybamm.Symbol
        The particle radius [m]; the characteristic length is the diameter.
    bed_area : pybamm.Symbol
        The bed cross-sectional area [m2], porosity not removed.
    """

    def __init__(self, radius, bed_area):
        super().__init__(2 * radius, bed_area)

    def nusselt(self, Re, Pr):
        return 2 + 1.1 * Re**0.6 * Pr ** (1 / 3)
