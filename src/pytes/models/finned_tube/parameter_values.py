#
# Parameter values of the finned-tube family
#
"""Default parameter values of the finned-tube family."""

from pytes import parameter_layers


def get_parameter_values(parameter_set=None):
    """
    Return parameter values for the finned-tube models.

    The default set is the composition "Finned tube default" of
    :mod:`pytes.parameter_layers`: an illustrative heat battery of one tube with
    0.02 kg/s of water, aluminium fins, and "PCM 60", which melts over 59 °C to 61 °C. The
    battery starts uniform at 70 °C (liquid) and is discharged with water at 10 °C.
    Energies are zero at the uniform state at the reference temperature, 10 °C. See
    :class:`pytes.models.finned_tube.FinnedTubeParameters` for the meaning of each parameter
    and the geometry, and :func:`pytes.parameter_layers.swap` to replace a part of the set,
    e.g. the PCM.

    The corners of the melting range are smoothed over "PCM smoothing width [K]" = 0.01 K.
    A wider smoothing makes the models faster, at the cost of accuracy near the melting
    range; set it to 0 for exact corners.

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
    return parameter_layers.compose_set("Finned tube default")
