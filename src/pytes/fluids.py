#
# Heat transfer fluid properties
#
"""
Heat transfer fluid (HTF) properties.

The fluid-property object is the only way a model obtains fluid properties (DESIGN D8). Its
properties are functions of the fluid state, the specific enthalpy ``h`` and the pressure
``p``, the natural inputs of property tables, so that they stay valid for a fluid whose
temperature is flat across a phase change (a refrigerant, later). ``h(T, p)`` gives the
enthalpy for the inlet and initial conditions. Power is defined from the specific enthalpy,
``mdot (h_out - h_in)``.

The heat transfer coefficient is not a fluid property: it depends on the geometry and the
flow too, and belongs to the surface flux law of a coupling (DESIGN D6, D8, see
:mod:`pytes.submodels.flux_laws`).
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
        conductivity and the viscosity are used by the flow-dependent heat transfer
        coefficients (:class:`pytes.submodels.NusseltCorrelation`); the conductivity is also
        the hook for axial diffusion.
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

    def h(self, T, p=None):
        """Specific enthalpy [J.kg-1] at temperature ``T`` [K] (``p`` is ignored)"""
        return self.c_p_param * (T - self.T_ref)

    def T(self, h, p=None):
        """Temperature [K] at specific enthalpy ``h`` [J.kg-1] (``p`` is ignored)"""
        return self.T_ref + h / self.c_p_param

    def c_p(self, h, p=None):
        """Specific heat capacity ``dh/dT`` [J.kg-1.K-1] at specific enthalpy ``h``"""
        return self.c_p_param

    def rho(self, h, p=None):
        """Density [kg.m-3] at specific enthalpy ``h`` [J.kg-1]"""
        return self.rho_param

    def k(self, h, p=None):
        """Conductivity [W.m-1.K-1] at specific enthalpy ``h`` [J.kg-1]"""
        return self.k_param

    def mu(self, h, p=None):
        """Dynamic viscosity [Pa.s] at specific enthalpy ``h`` [J.kg-1]"""
        return self.mu_param
