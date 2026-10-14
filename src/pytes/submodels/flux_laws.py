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

import pybamm


class SurfaceFluxLaw:
    """
    Base class of the surface flux laws.

    Subclasses implement :meth:`heat_flux`. Further arguments (e.g. the mass flow rate, for
    a correlation) are added when a law needs them; their interface is open (DESIGN §4).
    Geometry a law needs (e.g. a hydraulic diameter) is passed to its constructor by the
    family.
    """

    def heat_flux(self, fluid, h_f, T_f, T_s):
        """
        Heat flux [W.m-2] from the fluid into the storage surface.

        Parameters
        ----------
        fluid : object
            The fluid-property object, for properties at the fluid state.
        h_f : pybamm.Symbol
            Specific enthalpy of the fluid [J.kg-1].
        T_f : pybamm.Symbol
            Temperature of the fluid [K], ``fluid.T(h_f)``.
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

    def heat_flux(self, fluid, h_f, T_f, T_s):
        return self.coefficient * (T_f - T_s)
