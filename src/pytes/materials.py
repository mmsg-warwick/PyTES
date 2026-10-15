#
# Storage materials
#
"""
Storage materials: the enthalpy-temperature relation, the conductivity and the liquid
fraction of the material a storage submodel holds.

A material maps its enthalpy per unit volume ``H`` and its internal states to a temperature.
The materials here have no internal states (``internal_states`` is empty), so the
temperature is a function of ``H`` alone. Materials with kinetics or hysteresis will add
internal states without changing the storage submodels (DESIGN D7).

Enthalpies are per unit volume and relative to 0 K. Energy variables subtract the enthalpy
at the reference temperature, so this reference never shows in the outputs.
"""

import pybamm


def smooth_min(a, b, width):
    """
    Smooth approximation of min(a, b),
    ``(a + b - sqrt((a - b)**2 + width**2)) / 2``.

    It rounds the corner at ``a = b`` over a distance of order ``width``, is never larger
    than min(a, b), differs from it by at most ``width / 2`` (at the corner), and is
    exactly min(a, b) when ``width`` is 0.

    Parameters
    ----------
    a, b : pybamm.Symbol or float
        The values to compare.
    width : pybamm.Symbol or float
        Smoothing width, in the units of ``a`` and ``b``.

    Returns
    -------
    pybamm.Symbol
        The smoothed minimum.
    """
    return (a + b - pybamm.sqrt((a - b) ** 2 + width**2)) / 2


def smooth_max(a, b, width):
    """
    Smooth approximation of max(a, b),
    ``(a + b + sqrt((a - b)**2 + width**2)) / 2``. Never smaller than max(a, b); see
    :func:`smooth_min`.
    """
    return (a + b + pybamm.sqrt((a - b) ** 2 + width**2)) / 2


class SensibleMaterial:
    """
    A material that does not change phase, such as the metal of the fins.

    Parameters
    ----------
    prefix : str, optional
        Prefix of the parameter names (default "Metal"): "<prefix> conductivity
        [W.m-1.K-1]", "<prefix> density [kg.m-3]" and "<prefix> specific heat capacity
        [J.kg-1.K-1]".

    Attributes
    ----------
    k_param, rho, c_p : pybamm.Parameter
        Conductivity [W.m-1.K-1], density [kg.m-3] and specific heat capacity
        [J.kg-1.K-1].
    rho_c_p : pybamm.Symbol
        Volumetric heat capacity [J.m-3.K-1].
    internal_states : tuple
        Empty: the temperature is a function of the enthalpy alone.
    changes_phase : bool
        False: the material has no liquid fraction.
    H_scale, H_reference : pybamm.Symbol
        Typical enthalpy scale and reference [J.m-3], those of 100 K and 300 K. A storage
        submodel may override them (e.g. to scale like the model's temperatures).
    """

    internal_states = ()
    changes_phase = False

    def __init__(self, prefix="Metal"):
        self.prefix = prefix
        self.k_param = pybamm.Parameter(f"{prefix} conductivity [W.m-1.K-1]")
        self.rho = pybamm.Parameter(f"{prefix} density [kg.m-3]")
        self.c_p = pybamm.Parameter(f"{prefix} specific heat capacity [J.kg-1.K-1]")
        self.rho_c_p = self.rho * self.c_p
        self.H_scale = self.rho_c_p * 100
        self.H_reference = self.rho_c_p * 300

    def H2T(self, H, states=()):
        """Temperature [K] as a function of the enthalpy per unit volume [J.m-3]"""
        return H / self.rho_c_p

    def T2H(self, T):
        """Enthalpy per unit volume [J.m-3], relative to 0 K, at temperature ``T`` [K]"""
        return self.rho_c_p * T

    def k(self, H, states=()):
        """Conductivity [W.m-1.K-1] (constant)"""
        return self.k_param


class PhaseChangeMaterial:
    """
    Thermal properties of a material that melts, and the enthalpy-temperature relations
    derived from them. The enthalpy is per unit volume and relative to 0 K.

    Subclasses set the solid and liquid volumetric heat capacities ``rho_c_p_s`` and
    ``rho_c_p_l`` [J.m-3.K-1], the volumetric latent heat ``rho_L`` [J.m-3], the solid and
    liquid conductivities ``k_s`` and ``k_l`` [W.m-1.K-1], the melting temperature ``T_m``
    [K], the melting range ``melting_range`` [K] and the smoothing width
    ``smoothing_width`` [K], then call :meth:`_set_derived`.

    The material melts between the solidus ``T_m - melting_range / 2`` and the liquidus
    ``T_m + melting_range / 2`` (DESIGN D7). In between (the mushy zone) the enthalpy is
    linear in temperature: the latent heat spread evenly, plus the mean of the solid and
    liquid heat capacities. A melting range of 0 gives a sharp melting point, where the
    temperature stays at ``T_m`` while the material melts.

    Separately, the corners of the relations at the solidus and liquidus are smoothed over
    ``smoothing_width``, a numerical device that makes the models faster. A width of 0
    gives exact corners. Both may be 0.

    Attributes
    ----------
    internal_states : tuple
        Empty: the temperature is a function of the enthalpy alone.
    changes_phase : bool
        True: the material has a liquid fraction.
    T_solidus, T_liquidus : pybamm.Symbol
        Solidus and liquidus temperatures [K].
    rho_c_p_mushy : pybamm.Symbol
        Sensible heat capacity in the mushy zone [J.m-3.K-1], the mean of the solid and
        liquid ones.
    H_solidus, H_liquidus : pybamm.Symbol
        Enthalpy at the solidus (fully solid) and at the liquidus (fully liquid) [J.m-3].
    dT_smooth : pybamm.Symbol
        The smoothing width, floored at 1e-9 K so that derivatives stay defined where the
        arguments of :func:`smooth_min` and :func:`smooth_max` are equal (its effect is at
        most 5e-10 K).
    H_scale, H_reference : pybamm.Symbol
        Scale and reference for the enthalpy as a solver variable: the enthalpy of the
        mushy zone and its middle. The scaled enthalpy is then the liquid fraction minus 1/2
        while melting, and of order one over the operating range, as the sensible heat is
        comparable to the latent heat.
    """

    internal_states = ()
    changes_phase = True

    def _set_derived(self):
        """Set the solidus, the liquidus, the smoothing width and the scaling"""
        self.T_solidus = self.T_m - self.melting_range / 2
        self.T_liquidus = self.T_m + self.melting_range / 2
        self.rho_c_p_mushy = (self.rho_c_p_s + self.rho_c_p_l) / 2
        self.H_solidus = self.rho_c_p_s * self.T_solidus
        self.H_liquidus = (
            self.H_solidus + self.rho_L + self.rho_c_p_mushy * self.melting_range
        )
        # Floor the width at 1 nK so that derivatives stay defined (rather than 0 / 0)
        # where the arguments of smooth_min / smooth_max are equal, even when the
        # smoothing width is 0
        self.dT_smooth = pybamm.maximum(self.smoothing_width, 1e-9)
        # The scaled enthalpy is the liquid fraction - 1/2 while melting
        self.H_scale = self.H_liquidus - self.H_solidus
        self.H_reference = (self.H_solidus + self.H_liquidus) / 2

    def H2T(self, H, states=()):
        """
        Temperature as a function of the enthalpy and the internal states (none here).

        Below the solidus the temperature is ``H / rho_c_p_s``; in the mushy zone it rises
        linearly from the solidus to the liquidus temperature with the liquid fraction;
        above the liquidus it is ``T_liquidus + (H - H_liquidus) / rho_c_p_l``. The corners
        are smoothed over ``dT_smooth``.

        Parameters
        ----------
        H : pybamm.Symbol
            Enthalpy per unit volume, relative to 0 K [J.m-3].
        states : tuple, optional
            Internal states, in the order of ``internal_states`` (none for this material).

        Returns
        -------
        pybamm.Symbol
            Temperature [K].
        """
        # Each term is one piece, clipped: the corner widths in enthalpy match dT_smooth
        solid = smooth_min(H, self.H_solidus, self.rho_c_p_s * self.dT_smooth)
        liquid = smooth_max(H - self.H_liquidus, 0, self.rho_c_p_l * self.dT_smooth)
        return (
            solid / self.rho_c_p_s
            + self.melting_range * self.liquid_fraction(H, states)
            + liquid / self.rho_c_p_l
        )

    def T2H(self, T):
        """
        Enthalpy as a function of the temperature.

        This is the exact (unsmoothed) relation. Away from the solidus and the liquidus it
        inverts :meth:`H2T` up to about ``dT_smooth**2 / (4 d)``, with ``d`` the distance
        to the nearer of them. For a sharp melting point (melting range 0), the material at
        exactly ``T = T_m`` is taken to be fully solid.

        Parameters
        ----------
        T : pybamm.Symbol
            Temperature [K].

        Returns
        -------
        pybamm.Symbol
            Enthalpy per unit volume, relative to 0 K [J.m-3].
        """
        # The floor makes a melting range of 0 a step, solid at T_m
        width = pybamm.maximum(self.melting_range, 1e-12)
        phi = pybamm.minimum(pybamm.maximum((T - self.T_solidus) / width, 0), 1)
        return (
            self.rho_c_p_s * pybamm.minimum(T, self.T_solidus)
            + (self.H_liquidus - self.H_solidus) * phi
            + self.rho_c_p_l * pybamm.maximum(T - self.T_liquidus, 0)
        )

    def k(self, H, states=()):
        """
        Conductivity [W.m-1.K-1] as a function of the enthalpy [J.m-3], interpolated
        linearly in the liquid fraction between ``k_s`` and ``k_l``.
        """
        return self.k_s + (self.k_l - self.k_s) * self.liquid_fraction(H, states)

    def liquid_fraction(self, H, states=()):
        """
        Liquid fraction as a function of the enthalpy [J.m-3]: the fraction of the mushy
        zone's enthalpy, ``(H - H_solidus) / (H_liquidus - H_solidus)``, clipped to
        [0, 1] with the corners smoothed over the enthalpy widths matching ``dT_smooth``
        (``rho_c_p_s * dT_smooth`` and ``rho_c_p_l * dT_smooth``). In the mushy zone it is
        also ``(T - T_solidus) / melting_range``. It is between 0 and 1 up to an overshoot
        of order ``(rho_c_p * dT_smooth / rho_L)**2`` when smoothed.
        """
        dH = self.H_liquidus - self.H_solidus
        phi = (H - self.H_solidus) / dH
        phi = smooth_max(phi, 0, self.rho_c_p_s * self.dT_smooth / dH)
        return smooth_min(phi, 1, self.rho_c_p_l * self.dT_smooth / dH)


class PureMaterial(PhaseChangeMaterial):
    """
    A phase-change material on its own: ``rho_c_p_s = rho_s c_p_s``,
    ``rho_c_p_l = rho_l c_p_l``, ``rho_L = rho_s L`` (the latent heat per unit volume uses
    the solid density, neglecting the volume change on melting).

    Parameters
    ----------
    prefix : str, optional
        Prefix of the parameter names (default "PCM"), e.g. "<prefix> latent heat
        [J.kg-1]", "<prefix> melting range [K]" and "<prefix> smoothing width [K]".

    Attributes
    ----------
    k_s, k_l, rho_s, rho_l, c_p_s, c_p_l, L, T_m, melting_range, smoothing_width : \
pybamm.Parameter
        "<prefix> solid phase conductivity [W.m-1.K-1]", "<prefix> liquid phase
        conductivity [W.m-1.K-1]", "<prefix> solid phase density [kg.m-3]", "<prefix>
        liquid phase density [kg.m-3]", "<prefix> solid phase specific heat capacity
        [J.kg-1.K-1]", "<prefix> liquid phase specific heat capacity [J.kg-1.K-1]",
        "<prefix> latent heat [J.kg-1]", "<prefix> melting temperature [K]" (the middle
        of the melting range), "<prefix> melting range [K]" (from solidus to liquidus; 0
        for a sharp melting point) and "<prefix> smoothing width [K]" (numerical; 0 for
        exact corners).
    """

    def __init__(self, prefix="PCM"):
        self.prefix = prefix
        self.k_s = pybamm.Parameter(f"{prefix} solid phase conductivity [W.m-1.K-1]")
        self.k_l = pybamm.Parameter(f"{prefix} liquid phase conductivity [W.m-1.K-1]")
        self.rho_s = pybamm.Parameter(f"{prefix} solid phase density [kg.m-3]")
        self.rho_l = pybamm.Parameter(f"{prefix} liquid phase density [kg.m-3]")
        self.c_p_s = pybamm.Parameter(
            f"{prefix} solid phase specific heat capacity [J.kg-1.K-1]"
        )
        self.c_p_l = pybamm.Parameter(
            f"{prefix} liquid phase specific heat capacity [J.kg-1.K-1]"
        )
        self.L = pybamm.Parameter(f"{prefix} latent heat [J.kg-1]")
        self.T_m = pybamm.Parameter(f"{prefix} melting temperature [K]")
        self.melting_range = pybamm.Parameter(f"{prefix} melting range [K]")
        self.smoothing_width = pybamm.Parameter(f"{prefix} smoothing width [K]")

        self.rho_c_p_s = self.rho_s * self.c_p_s
        self.rho_c_p_l = self.rho_l * self.c_p_l
        self.rho_L = self.rho_s * self.L
        self._set_derived()


class CompositeMaterial(PhaseChangeMaterial):
    """
    A phase-change material and a sensible filler (such as metal fins) homogenised into one
    material, with the filler taking up a volume fraction ``delta``:

    - heat capacities: volume averages,
      ``rho_c_p_s = delta rho_c_p_filler + (1 - delta) rho_c_p_s,PCM`` (and similarly for
      the liquid);
    - latent heat: ``rho_L = (1 - delta) rho_L,PCM``, as only the PCM melts;
    - conductivities: volume averages, ``k_s = (1 - delta) k_s,PCM + delta k_filler`` (and
      similarly for the liquid), i.e. the parallel arrangement, for heat flowing along the
      filler.

    Parameters
    ----------
    pcm : :class:`PureMaterial`
        The phase-change material.
    filler : :class:`SensibleMaterial`
        The filler.
    volume_fraction : pybamm.Symbol
        Volume fraction of the filler, ``delta``.
    """

    def __init__(self, pcm, filler, volume_fraction):
        self.pcm = pcm
        self.filler = filler
        delta = volume_fraction
        self.T_m = pcm.T_m
        self.melting_range = pcm.melting_range
        self.smoothing_width = pcm.smoothing_width
        self.rho_c_p_s = filler.rho_c_p * delta + pcm.rho_c_p_s * (1 - delta)
        self.rho_c_p_l = filler.rho_c_p * delta + pcm.rho_c_p_l * (1 - delta)
        self.rho_L = pcm.rho_L * (1 - delta)
        self.k_s = pcm.k_s * (1 - delta) + filler.k_param * delta
        self.k_l = pcm.k_l * (1 - delta) + filler.k_param * delta
        self._set_derived()
