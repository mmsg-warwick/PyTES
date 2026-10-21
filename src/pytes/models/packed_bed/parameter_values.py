#
# Parameter values of the packed-bed family
#
"""Default parameter values of the packed-bed family."""

from pytes import parameter_layers


def get_parameter_values(parameter_set="Nallusamy2007"):
    """
    Return parameter values for the packed-bed models.

    Each set is the composition of the same name in :mod:`pytes.parameter_layers`, with
    the sources of its values in its ``"citations"``:

    - "Nallusamy2007" (default): the experiments of `Nallusamy, Sampath and Velraj (2007)
      <https://doi.org/10.1016/j.renene.2006.04.015>`__, a stainless-steel tank (360 mm
      diameter, 460 mm high) of paraffin in spherical capsules (55 mm diameter), charged
      with water at 70 °C and 2 l/min from 32 °C. The measured temperatures are in
      ``examples/data``.
    - "Raul2018": the experiments of `Raul et al. (2018)
      <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__, a bed (170 mm diameter,
      360 mm long) of capsules (31 mm diameter) of A164, which melts at 168.7 °C, charged
      with Hytherm 600 oil at 180 °C and 8.2 l/min from 400 K.

    The PCMs melt sharply, with corners smoothed over 0.01 K (DESIGN D7), and the heat
    transfer coefficient is an estimate. Energies are zero at the initial temperature.

    Parameters
    ----------
    parameter_set : str, optional
        The name of the parameter set (default "Nallusamy2007").

    Returns
    -------
    :class:`pybamm.ParameterValues`
    """
    if parameter_set not in ("Nallusamy2007", "Raul2018"):
        raise ValueError(f"Parameter set '{parameter_set}' not recognised")
    return parameter_layers.compose_set(parameter_set)
