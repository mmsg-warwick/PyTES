#
# Parameter values of the packed-bed family
#
"""Default parameter values of the packed-bed family."""

import numpy as np
import pybamm


def get_parameter_values(parameter_set="Nallusamy2007"):
    """
    Return parameter values for the packed-bed models.

    - "Nallusamy2007" (default): the experiments of Nallusamy, Sampath and Velraj (2007),
      a 47 l stainless-steel tank (360 mm diameter, 460 mm high) of paraffin in spherical
      capsules (55 mm diameter), charged with water at 70 °C and about 2 l/min from 32 °C.
      The measured temperatures are in ``examples/data``.
    - "Raul2018": a bed of capsules of a PCM melting at 168.7 °C, charged with a thermal
      oil. The source gives no cross-section, so "Bed cross-sectional area [m2]" is a 1 m2
      placeholder: per-area results are meaningful, device totals scale with it.

    Both sets come from the `encapsulated-LTES
    <https://github.com/mmsg-warwick/encapsulated-LTES>`_ repository (DESIGN, F-002),
    converted to PyTES parameters: the flow is the mass flow rate ``rho_f eps A u`` of the interstitial
    velocity ``u``, and the PCM melts sharply with corners smoothed over 0.5 K (DESIGN D7).
    Energies are zero at the initial temperature.

    Parameters
    ----------
    parameter_set : str, optional
        The name of the parameter set (default "Nallusamy2007").

    Returns
    -------
    :class:`pybamm.ParameterValues`
    """
    if parameter_set == "Nallusamy2007":
        area = np.pi * 0.18**2
        porosity = 0.5
        rho_f = 1000
        values = {
            # Device level
            "Reference temperature [K]": 273.15 + 32,
            "Initial temperature [K]": 273.15 + 32,
            "Inlet temperature [K]": 273.15 + 70,
            # Interstitial velocity 6.5e-4 m/s, about 2 l/min
            "Mass flow rate [kg.s-1]": rho_f * porosity * area * 6.5e-4,
            # Heat transfer fluid (water)
            "Heat transfer fluid density [kg.m-3]": rho_f,
            "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 4186,
            "Heat transfer fluid conductivity [W.m-1.K-1]": 0.6,
            "Heat transfer coefficient [W.m-2.K-1]": 100,
            # PCM (paraffin)
            "PCM solid phase conductivity [W.m-1.K-1]": 0.4,
            "PCM liquid phase conductivity [W.m-1.K-1]": 0.15,
            "PCM solid phase density [kg.m-3]": 861,
            "PCM liquid phase density [kg.m-3]": 778,
            "PCM solid phase specific heat capacity [J.kg-1.K-1]": 1850,
            "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 2384,
            "PCM latent heat [J.kg-1]": 213e3,
            "PCM melting temperature [K]": 273.15 + 60,
            "PCM melting range [K]": 0,
            "PCM smoothing width [K]": 0.5,
            # Bed
            "Bed length [m]": 0.46,
            "Bed cross-sectional area [m2]": area,
            "Bed porosity": porosity,
            "Capsule radius [m]": 27.5e-3,
        }
    elif parameter_set == "Raul2018":
        area = 1  # placeholder: the source gives no cross-section
        porosity = 0.6
        rho_f = 720.9
        values = {
            "Reference temperature [K]": 400,
            "Initial temperature [K]": 400,
            "Inlet temperature [K]": 453.15,
            # Interstitial velocity 1e-2 m/s
            "Mass flow rate [kg.s-1]": rho_f * porosity * area * 1e-2,
            "Heat transfer fluid density [kg.m-3]": rho_f,
            "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 3097.4,
            "Heat transfer fluid conductivity [W.m-1.K-1]": 0.116,
            "Heat transfer coefficient [W.m-2.K-1]": 100,
            "PCM solid phase conductivity [W.m-1.K-1]": 0.45,
            "PCM liquid phase conductivity [W.m-1.K-1]": 0.45,
            "PCM solid phase density [kg.m-3]": 1500,
            "PCM liquid phase density [kg.m-3]": 1500,
            "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2013.3,
            "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 2013.3,
            "PCM latent heat [J.kg-1]": 2.497e5,
            "PCM melting temperature [K]": 441.85,
            "PCM melting range [K]": 0,
            "PCM smoothing width [K]": 0.5,
            "Bed length [m]": 0.36,
            "Bed cross-sectional area [m2]": area,
            "Bed porosity": porosity,
            "Capsule radius [m]": 1.55e-2,
        }
    else:
        raise ValueError(f"Parameter set '{parameter_set}' not recognised")
    return pybamm.ParameterValues(values)
