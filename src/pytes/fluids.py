#
# Heat transfer fluid properties
#
"""
Heat transfer fluid (HTF) properties.

The fluid-property object is the only way a model obtains fluid properties (DESIGN D8). Power
is defined from the specific enthalpy, ``mdot (h_out - h_in)``, so the definitions stay valid
for a fluid whose enthalpy is not linear in temperature (a refrigerant, later).
"""

import pybamm


class ConstantPropertyLiquid:
    """
    A liquid with constant density and specific heat capacity, so that its specific enthalpy
    is linear in temperature: ``h = c_p (T - T_ref)``. The pressure is ignored.

    The enthalpy reference ``T_ref`` only shifts ``h``; energy variables and power use
    differences of ``h``, so it never shows in the outputs.

    Parameters
    ----------
    prefix : str, optional
        Prefix of the parameter names (default "Heat transfer fluid").
    T_ref : pybamm.Symbol or float, optional
        Temperature at which ``h = 0`` [K] (default 0 K).

    Attributes
    ----------
    rho_param, c_p_param, k_param, mu_param : pybamm.Parameter
        "<prefix> density [kg.m-3]", "<prefix> specific heat capacity [J.kg-1.K-1]",
        "<prefix> conductivity [W.m-1.K-1]" and "<prefix> viscosity [Pa.s]". The
        conductivity and the viscosity are not used by the current models; they are the hook
        for axial diffusion and for flow-dependent heat transfer coefficients.
    h_coefficient : pybamm.Parameter
        "Heat transfer coefficient [W.m-2.K-1]", constant for now.
    """

    def __init__(self, prefix="Heat transfer fluid", T_ref=0):
        self.prefix = prefix
        self.T_ref = T_ref
        self.rho_param = pybamm.Parameter(f"{prefix} density [kg.m-3]")
        self.c_p_param = pybamm.Parameter(
            f"{prefix} specific heat capacity [J.kg-1.K-1]"
        )
        self.k_param = pybamm.Parameter(f"{prefix} conductivity [W.m-1.K-1]")
        self.mu_param = pybamm.Parameter(f"{prefix} viscosity [Pa.s]")
        self.h_coefficient = pybamm.Parameter("Heat transfer coefficient [W.m-2.K-1]")

    def h(self, T, p=None):
        """Specific enthalpy [J.kg-1] at temperature ``T`` [K] (``p`` is ignored)"""
        return self.c_p_param * (T - self.T_ref)

    def T(self, h, p=None):
        """Temperature [K] at specific enthalpy ``h`` [J.kg-1] (``p`` is ignored)"""
        return self.T_ref + h / self.c_p_param

    def c_p(self, T, p=None):
        """Specific heat capacity ``dh/dT`` [J.kg-1.K-1]"""
        return self.c_p_param

    def rho(self, T, p=None):
        """Density [kg.m-3]"""
        return self.rho_param

    def k(self, T, p=None):
        """Conductivity [W.m-1.K-1]"""
        return self.k_param

    def mu(self, T, p=None):
        """Dynamic viscosity [Pa.s]"""
        return self.mu_param

    def heat_transfer_coefficient(self, T, mass_flow_rate=None, geometry=None):
        """
        Heat transfer coefficient [W.m-2.K-1] between the fluid and a wall or a surface.

        Constant for now. ``mass_flow_rate`` and ``geometry`` are the hook for Nusselt and
        Reynolds number correlations (deferred).
        """
        return self.h_coefficient
