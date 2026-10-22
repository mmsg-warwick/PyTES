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
packed beds. Correlations are registered by flow geometry in :data:`CORRELATIONS`, and
:func:`register_correlation` adds one, from PyTES or from a user, as a value of the models'
"heat transfer coefficient" option.
"""

from collections.abc import Sequence
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
    state, flow included, comes with each call as a :class:`FluidState`. A law that needs a
    variable of another submodel (e.g. the storage conductivity, for :class:`Jeffreson`)
    reads it as a :class:`pybamm.CoupledVariable` listed in :attr:`coupled_variables`,
    which the coupling declares as its own requirements, so the model's wiring checks see
    it.

    Attributes
    ----------
    coupled_variables : dict
        The :class:`pybamm.CoupledVariable` objects the law reads, by name (none by
        default).
    """

    coupled_variables = {}

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


class TubeCorrelation(NusseltCorrelation):
    """
    A Nusselt correlation for the flow inside tubes (flow ``"tube"``, the finned-tube
    models): the characteristic length is the tube diameter and the velocity the mean
    velocity in a tube. Subclasses implement :meth:`nusselt`.

    Parameters
    ----------
    radius : pybamm.Symbol
        The tube radius [m].
    n_tubes : pybamm.Symbol or float, optional
        Number of tubes sharing the device's mass flow rate (default 1).
    """

    def __init__(self, radius, n_tubes=1):
        super().__init__(2 * radius, np.pi * radius**2, n_tubes)


class PackedBedCorrelation(NusseltCorrelation):
    """
    A Nusselt correlation for the flow through a packed bed (flow ``"packed bed"``, the
    packed-bed model): the characteristic length is the particle diameter and the velocity
    the superficial velocity, the mass flow rate over the whole bed cross-section.
    Subclasses implement :meth:`nusselt`.

    Parameters
    ----------
    radius : pybamm.Symbol
        The particle radius [m].
    bed_area : pybamm.Symbol
        The bed cross-sectional area [m2], porosity not removed.
    """

    def __init__(self, radius, bed_area):
        super().__init__(2 * radius, bed_area)


class Gnielinski(TubeCorrelation):
    """
    Fully developed flow in a smooth tube: the Gnielinski correlation in turbulent flow, the
    laminar Nusselt number at a uniform wall temperature, 3.66, below ``Re = 2300``, and
    a linear interpolation between them in the transition, as in the VDI Heat Atlas
    (`Gnielinski, "On heat transfer in tubes", International Journal of Heat and Mass
    Transfer 63, 2013 <https://doi.org/10.1016/j.ijheatmasstransfer.2013.04.015>`__):

    - ``Nu = 3.66`` for ``Re <= 2300``;
    - ``Nu = (1 - g) 3.66 + g Nu_t(10^4)``, ``g = (Re - 2300) / (10^4 - 2300)``, for
      ``2300 < Re < 10^4``;
    - ``Nu = Nu_t(Re)`` for ``Re >= 10^4``, with
      ``Nu_t = (f / 8) (Re - 1000) Pr / (1 + 12.7 sqrt(f / 8) (Pr^(2/3) - 1))`` and the
      friction factor ``f = (0.79 ln(Re) - 1.64)^-2``.

    The entrance region and the variation of the properties between the bulk and the wall
    are neglected. The Nusselt number is continuous in ``Re``; its slope is not, at
    ``Re = 2300`` and ``10^4``. Registered as "Gnielinski" for the flow ``"tube"``.
    """

    #: Laminar Nusselt number, fully developed flow at a uniform wall temperature
    nusselt_laminar = 3.66
    #: Reynolds numbers at which the transition starts and ends
    reynolds_transition = (2300, 1e4)

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


class WakaoKaguei(PackedBedCorrelation):
    """
    Fluid to particle heat transfer in a packed bed: the correlation of `Wakao, Kaguei and
    Funazkri (Chemical Engineering Science 34, 1979, 325-336)
    <https://doi.org/10.1016/0009-2509(79)85064-2>`__, ``Nu = 2 + 1.1 Re^0.6 Pr^(1/3)``,
    with the particle diameter as the characteristic length and the superficial velocity in
    the Reynolds number. Fitted for ``15 < Re < 8500``. Registered as "Wakao-Kaguei" for the
    flow ``"packed bed"``.
    """

    def nusselt(self, Re, Pr):
        return 2 + 1.1 * Re**0.6 * Pr ** (1 / 3)


class Jeffreson(SurfaceFluxLaw):
    """
    Newton's law of cooling for a lumped sphere, with Jeffreson's correction for the
    conduction resistance inside it (issue #5): the heat flux into the sphere is
    ``h_eff (T_f - T_s)``, with ``T_s`` the sphere's (uniform) temperature and

    ``1 / h_eff = 1 / h + R / (5 k)``, that is ``h_eff = h / (1 + Bi / 5)``, ``Bi = h R / k``,

    where ``h`` is the heat transfer coefficient of the law it corrects, ``R`` the sphere's
    radius and ``k`` its conductivity (C. P. Jeffreson, "Prediction of breakthrough curves
    in packed beds: 1. Applicability of single parameter models", AIChE Journal 18, 1972).
    The correction is exact for the slow variation of a sensible sphere; while a PCM melts
    or freezes inside the sphere it is an approximation, with ``k`` the conductivity at the
    sphere's mean enthalpy.

    Parameters
    ----------
    law : :class:`NewtonCooling`
        The law it corrects, which gives ``h`` (a constant coefficient or a Nusselt
        correlation).
    radius : pybamm.Symbol
        The sphere's radius ``R`` [m].
    conductivity : str
        Name of the variable holding the sphere's conductivity [W.m-1.K-1], e.g.
        "Phase-change material thermal conductivity [W.m-1.K-1]" from a
        :class:`pytes.submodels.LumpedStorage`.
    domain : str or list of str, optional
        Primary domain of that variable (default: none).

    Raises
    ------
    TypeError
        If ``law`` is not a :class:`NewtonCooling`.
    """

    def __init__(self, law, radius, conductivity, domain=None):
        if not isinstance(law, NewtonCooling):
            raise TypeError(
                f"Jeffreson's correction applies to a heat transfer coefficient (a "
                f"NewtonCooling law), got {type(law).__name__}"
            )
        self.law = law
        self.radius = radius
        self.conductivity = pybamm.CoupledVariable(conductivity, domain)
        self.coupled_variables = {conductivity: self.conductivity}

    def biot(self, fluid, fluid_state):
        """The Biot number of the sphere, ``h R / k``"""
        h = self.law.heat_transfer_coefficient(fluid, fluid_state)
        return h * self.radius / self.conductivity

    def heat_transfer_coefficient(self, fluid, fluid_state):
        """The corrected coefficient ``h_eff`` [W.m-2.K-1]"""
        h = self.law.heat_transfer_coefficient(fluid, fluid_state)
        return h / (1 + self.biot(fluid, fluid_state) / 5)

    def heat_flux(self, fluid, fluid_state, T_s):
        h_eff = self.heat_transfer_coefficient(fluid, fluid_state)
        return h_eff * (fluid_state.T - T_s)

    def variables(self, fluid, fluid_state):
        """
        Those of the law it corrects, plus "Effective heat transfer coefficient
        [W.m-2.K-1]" and "Surface Biot number"
        """
        return {
            **self.law.variables(fluid, fluid_state),
            "Effective heat transfer coefficient [W.m-2.K-1]": (
                self.heat_transfer_coefficient(fluid, fluid_state)
            ),
            "Surface Biot number": self.biot(fluid, fluid_state),
        }


#: The base class of the correlations of each flow geometry
FLOWS = {"tube": TubeCorrelation, "packed bed": PackedBedCorrelation}

#: The correlations shipped with PyTES, by flow geometry and name
BUILT_IN_CORRELATIONS = {
    "tube": {"Gnielinski": Gnielinski},
    "packed bed": {"Wakao-Kaguei": WakaoKaguei},
}

#: The registered correlations, by flow geometry and name: those shipped with PyTES and
#: those added by :func:`register_correlation`
CORRELATIONS = {
    flow: dict(built_in) for flow, built_in in BUILT_IN_CORRELATIONS.items()
}

#: The value of the "heat transfer coefficient" option for a constant coefficient
CONSTANT = "constant"


def _flow_base(flow):
    try:
        return FLOWS[flow]
    except KeyError:
        raise ValueError(
            f"Unknown flow '{flow}'; the flows are {', '.join(map(repr, FLOWS))}"
        ) from None


def register_correlation(name, nusselt, flow, replace=False):
    """
    Register a Nusselt correlation, so that the models of its flow geometry accept its name
    as a value of the "heat transfer coefficient" option.

    The family supplies the geometry (see :class:`TubeCorrelation` and
    :class:`PackedBedCorrelation`) and the fluid-property object the properties, so a
    correlation is only its Nusselt number. Energy is conserved whatever the correlation
    (DESIGN D6); :func:`pytes.conformance.check_model` checks a model that uses it.

    Parameters
    ----------
    name : str
        The name of the correlation, the option value that selects it.
    nusselt : callable or type
        A function ``nusselt(Re, Pr)`` of the Reynolds and Prandtl numbers, as PyBaMM
        symbols (so use ``pybamm.log``, ``pybamm.sqrt``, etc.), returning the Nusselt
        number; or a subclass of the flow's correlation class implementing
        :meth:`NusseltCorrelation.nusselt`.
    flow : str
        The flow geometry: ``"tube"`` (the finned-tube models) or ``"packed bed"`` (the
        packed-bed model).
    replace : bool, optional
        Whether to replace a correlation registered earlier under the same name, e.g. when
        a notebook cell runs again (default False). A correlation shipped with PyTES cannot
        be replaced.

    Returns
    -------
    type
        The correlation class, a subclass of the flow's correlation class.

    Raises
    ------
    ValueError
        If the flow is unknown, or the name is not a non-empty string, is "constant", is
        a built-in correlation, or is already registered and ``replace`` is False.
    TypeError
        If ``nusselt`` is neither callable nor a subclass of the flow's correlation class.

    Examples
    --------
    >>> import pytes
    >>> pytes.submodels.register_correlation(
    ...     "Dittus-Boelter", lambda Re, Pr: 0.023 * Re**0.8 * Pr**0.4, flow="tube"
    ... )  # doctest: +SKIP
    >>> model = pytes.SharpFrontModel(
    ...     options={"heat transfer coefficient": "Dittus-Boelter"}
    ... )  # doctest: +SKIP
    """
    base = _flow_base(flow)
    if not isinstance(name, str) or not name:
        raise ValueError(
            f"A correlation's name must be a non-empty string, got {name!r}"
        )
    if name == CONSTANT:
        raise ValueError(f"'{CONSTANT}' is the constant coefficient, not a correlation")
    if name in BUILT_IN_CORRELATIONS[flow]:
        raise ValueError(f"'{name}' is a correlation of PyTES and cannot be replaced")
    if name in CORRELATIONS[flow] and not replace:
        raise ValueError(
            f"A correlation '{name}' is already registered for the flow '{flow}'; pass "
            "replace=True to replace it"
        )
    if isinstance(nusselt, type):
        if not issubclass(nusselt, base):
            raise TypeError(
                f"A correlation class for the flow '{flow}' must subclass "
                f"{base.__name__}, got {nusselt.__name__}"
            )
        correlation = nusselt
    elif callable(nusselt):
        correlation = type(
            base.__name__,
            (base,),
            {
                "nusselt": lambda self, Re, Pr: nusselt(Re, Pr),
                "__doc__": f"The correlation '{name}', registered for the flow '{flow}'",
            },
        )
    else:
        raise TypeError(
            "A correlation is a function nusselt(Re, Pr) or a subclass of "
            f"{base.__name__}, got {nusselt!r}"
        )
    CORRELATIONS[flow][name] = correlation
    return correlation


class HeatTransferCoefficientOptions(Sequence):
    """
    The values of a model's "heat transfer coefficient" option: "constant", then the names
    of the correlations registered for its flow geometry. They are read from
    :data:`CORRELATIONS` when used, so a correlation registered after the model class was
    defined is allowed.

    Parameters
    ----------
    flow : str
        The flow geometry, ``"tube"`` or ``"packed bed"``.
    """

    def __init__(self, flow):
        _flow_base(flow)
        self.flow = flow

    def _values(self):
        return (CONSTANT, *CORRELATIONS[self.flow])

    def __getitem__(self, index):
        return self._values()[index]

    def __len__(self):
        return len(self._values())

    def __repr__(self):
        return f"HeatTransferCoefficientOptions({self.flow!r}): {list(self)}"

    def flux_law(self, value, *geometry):
        """
        The surface flux law an option value selects.

        Parameters
        ----------
        value : str
            The option value, "constant" or a registered correlation.
        *geometry : pybamm.Symbol
            The family's geometry, passed to the correlation's constructor.

        Returns
        -------
        :class:`SurfaceFluxLaw`
        """
        if value == CONSTANT:
            return NewtonCooling()
        return CORRELATIONS[self.flow][value](*geometry)
