#
# Parameter values of the finned-pipe family
#
"""Default parameter values of the finned-pipe family."""

import pybamm


def get_parameter_values(parameter_set=None):
    """
    Return parameter values for the finned-pipe models.

    The default set is for a representative heat battery: 14 pipes with a total flow of
    20 l/min of water, aluminium fins, and a PCM melting at 58 °C. The battery starts uniform
    at 70 °C (liquid) and is discharged with water at 10 °C. Energies are zero at the uniform
    state at the reference temperature, 10 °C. See
    :class:`pytes.models.finned_pipe.FinnedPipeParameters` for the meaning of each parameter
    and the geometry.

    The melting point is smoothed over "PCM melting range [K]" = 0.5 K by default, which
    makes the models about 2 to 3 times faster and changes the outlet temperature by about
    0.05 K compared with a sharp melting point. Set it to 0 for a sharp melting point.

    Parameters
    ----------
    parameter_set : str, optional
        The name of the parameter set. Only the default (None) is available.

    Returns
    -------
    :class:`pybamm.ParameterValues`
    """
    if parameter_set is not None:
        raise ValueError(f"Parameter set '{parameter_set}' not recognised")
    return pybamm.ParameterValues(
        {
            # Device level
            "Reference temperature [K]": 273.15 + 10,
            "Initial temperature [K]": 273.15 + 70,
            "Inlet temperature [K]": 273.15 + 10,
            # 20 l/min of water in total
            "Mass flow rate [kg.s-1]": 1000 * 20 / 6e4,
            # Heat transfer fluid (water)
            "Heat transfer fluid density [kg.m-3]": 1000,
            "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 4186,
            "Heat transfer fluid conductivity [W.m-1.K-1]": 0.6,
            "Heat transfer coefficient [W.m-2.K-1]": 1000,
            # PCM
            "PCM solid phase conductivity [W.m-1.K-1]": 1,
            "PCM liquid phase conductivity [W.m-1.K-1]": 0.6,
            "PCM solid phase density [kg.m-3]": 1440,
            "PCM liquid phase density [kg.m-3]": 1280,
            "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2800,
            "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 3500,
            "PCM latent heat [J.kg-1]": 226e3,
            "PCM melting temperature [K]": 273.15 + 58,
            "PCM melting range [K]": 0.5,
            # Fins (aluminium)
            "Metal conductivity [W.m-1.K-1]": 237,
            "Metal density [kg.m-3]": 2700,
            "Metal specific heat capacity [J.kg-1.K-1]": 900,
            # Geometry
            "Number of pipes": 14,
            "Pipe radius [m]": 3.25e-3,
            "Pipe length [m]": 11.1,
            "Fin thickness [m]": 1.05e-4,
            "Fin spacing [m]": 1.95e-3,
            "PCM outer radius [m]": 1e-2,  # roughly pipes 2 cm apart
        }
    )
