#
# Post-processing of models and solutions
#
"""
Post-processing (toolkit, DESIGN D15): quantities derived from a model and its parameter
values, rather than model outputs.
"""

import numpy as np
import pybamm

from .submodels import DeviceEnergy


def energy_between(model, T_a, T_b, parameter_values=None, var_pts=None):
    """
    Total thermal energy [J] between the uniform states at ``T_a`` and ``T_b`` (DESIGN D13).

    Each uniform state is solid up to the melting temperature and liquid above it, as for
    the initial state. The result is positive when ``T_b`` holds more energy than ``T_a``.
    It is derived from the materials and geometry on the model's mesh, so it equals the
    difference in the model's "Total thermal energy [J]" between those two states. For
    example, ``energy_between(model, T_cold, T_hot)`` is the energy a full charge from
    ``T_cold`` to ``T_hot`` stores.

    Parameters
    ----------
    model : :class:`pytes.BaseModel`
        The model. It must have a :class:`pytes.submodels.DeviceEnergy` submodel.
    T_a, T_b : float
        Temperatures of the two uniform states [K].
    parameter_values : pybamm.ParameterValues, optional
        Parameter values (default: the model's).
    var_pts : dict, optional
        Mesh points (default: the model's). Use the mesh of the simulation the result is
        compared with.

    Returns
    -------
    float
    """
    parameter_values = (parameter_values or model.default_parameter_values).copy()
    device = next(
        (s for s in model.submodels.values() if isinstance(s, DeviceEnergy)), None
    )
    if device is None:
        raise ValueError(f"{model.name} has no DeviceEnergy submodel")
    energy = device.uniform_energy(pybamm.Scalar(T_b)) - device.uniform_energy(
        pybamm.Scalar(T_a)
    )
    geometry = model.default_geometry
    parameter_values.process_geometry(geometry)
    mesh = pybamm.Mesh(
        geometry, model.default_submesh_types, var_pts or model.default_var_pts
    )
    disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
    energy = disc.process_symbol(parameter_values.process_symbol(energy))
    return np.asarray(energy.evaluate()).item()
