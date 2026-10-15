#
# Analytical solutions for validation
#
"""
Analytical solutions the models are validated against (DESIGN D1, §6). Importable, like the
conformance checks, so that anyone can compare a model with them.

- :func:`schumann`: a packed bed of a sensible material with lumped particles (Schumann,
  1929).
- :func:`sphere_melting_time`: the quasi-steady melting of a sphere from its surface, the
  limit of the spherical Stefan problem at small Stefan number.
"""

import numpy as np
from scipy.integrate import quad
from scipy.special import i0e


def _kernel(a, b):
    """``exp(-(a + b)) I0(2 sqrt(a b))``, evaluated without overflow"""
    return np.exp(-((np.sqrt(a) - np.sqrt(b)) ** 2)) * i0e(2 * np.sqrt(a * b))


def schumann(xi, eta):
    """
    Schumann's solution for a packed bed of a sensible material with lumped particles, no
    axial conduction or dispersion, initially uniform, with a step in the inlet temperature.

    With ``theta = (T - T_0) / (T_in - T_0)`` for the fluid and the solid, the equations are
    ``d theta_f / d xi = theta_s - theta_f`` and ``d theta_s / d eta = theta_f - theta_s``,
    with ``theta_f = 1`` at the inlet and ``theta_s = 0`` initially, in the variables

    - ``xi = h a z / (eps rho_f c_f u)``: the number of transfer units from the inlet,
    - ``eta = h a (t - z / u) / ((1 - eps) rho_s c_s)``: the time since the fluid that
      entered at ``t = 0`` reached ``z``, in units of the particles' time constant,

    with ``a`` the particle surface per unit bed volume and ``u`` the interstitial velocity.
    Before that fluid arrives (``eta <= 0``) both are 0.

    Parameters
    ----------
    xi, eta : float
        The transfer units and the transfer time.

    Returns
    -------
    theta_f, theta_s : float
        The fluid and solid temperatures, scaled.
    """
    if eta <= 0:
        return 0.0, 0.0
    theta_f = 1 - quad(lambda s: _kernel(s, eta), 0, xi, epsabs=1e-13, epsrel=1e-12)[0]
    theta_s = quad(lambda s: _kernel(xi, s), 0, eta, epsabs=1e-13, epsrel=1e-12)[0]
    return theta_f, theta_s


def sphere_melting_time(liquid_fraction):
    """
    Time for a sphere at its melting temperature to melt a volume fraction
    ``liquid_fraction`` when its surface is held above the melting temperature, in the
    quasi-steady limit (small Stefan number, conduction through the liquid shell only):

    ``t / tau = 1 - 3 (s / R)**2 + 2 (s / R)**3``, with ``s / R = (1 - liquid_fraction)**(1/3)``

    the radius of the solid core, and ``tau = rho L R**2 / (6 k_l (T_surface - T_m))`` the
    time to melt it completely.

    Parameters
    ----------
    liquid_fraction : float or numpy.ndarray
        The melted volume fraction, between 0 and 1.

    Returns
    -------
    float or numpy.ndarray
        The time, in units of ``tau``.
    """
    s = (1 - np.asarray(liquid_fraction)) ** (1 / 3)
    return 1 - 3 * s**2 + 2 * s**3
