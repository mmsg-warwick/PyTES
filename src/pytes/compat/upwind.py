"""
Inflow value of :func:`pybamm.upwind`.

Upstream: pybamm-team/PyBaMM#5860 (the inflow bug below), fixed by PR #5861 (PyBaMM 26.11);
earlier, #3526 and PR #3979 (upwinding in finite volumes).

Problem: before the fix, upwinding imposes a Dirichlet condition ``T_bc`` through a ghost
node of value ``2 T_bc - T_1`` (``T_1`` is the value in the first cell) and advects that
ghost value into the domain, so the fluid flowing in is not at ``T_bc``.

Workaround: on a PyBaMM without the fix, set ``T_bc = (T_in + T_1) / 2``, so that the ghost
node is exactly ``T_in``, with boundary values on the flow domain taken from the end cells
(constant extrapolation, see :func:`pytes.compat.fluid_spatial_method`). On a PyBaMM with
the fix (detected by :func:`upwind_uses_boundary_value`), ``T_bc = T_in``. Both advect
exactly ``T_in`` into the domain, so the results do not depend on the installed PyBaMM.

Remove when: the oldest supported PyBaMM has the fix (``fixed_in`` in
:data:`pytes.compat.SHIMS`). Then use ``T_in`` as the boundary condition, and check
whether the extrapolation options of :func:`pytes.compat.fluid_spatial_method` are still
needed: the outlet value must stay the value in the last cell.
"""

import functools

import numpy as np
import pybamm


@functools.cache
def upwind_uses_boundary_value():
    """
    Whether :func:`pybamm.upwind` takes the Dirichlet value itself as the inflow value
    (pybamm-team/PyBaMM#5860, fixed in 26.11).

    Discretises the upwinded value of a variable on two cells with an inflow value of 1, and
    evaluates it where the variable is 0: the inflow face is 1 with the fix, and the ghost
    node ``2 * 1 - 0 = 2`` without it. The answer is cached.

    Returns
    -------
    bool
    """
    x = pybamm.SpatialVariable("x", domain="probe", coord_sys="cartesian")
    geometry = {"probe": {x: {"min": 0, "max": 1}}}
    mesh = pybamm.Mesh(
        geometry,
        {"probe": pybamm.MeshGenerator(pybamm.Uniform1DSubMesh)},
        {x: 2},
    )
    c = pybamm.Variable("c", domain="probe")
    disc = pybamm.Discretisation(mesh, {"probe": pybamm.FiniteVolume()})
    disc.bcs = {c: {"left": (pybamm.Scalar(1), "Dirichlet")}}
    disc.set_variable_slices([c])
    faces = disc.process_symbol(pybamm.upwind(c)).evaluate(y=np.zeros(2))
    return bool(np.isclose(faces.flatten()[0], 1))


def upwind_inlet_value(T, T_in):
    """
    Dirichlet value that makes :func:`pybamm.upwind` advect exactly ``T_in`` into the domain.

    Parameters
    ----------
    T : pybamm.Variable
        The advected variable, on the flow domain.
    T_in : pybamm.Symbol
        The value of the inflowing fluid.

    Returns
    -------
    pybamm.Symbol
        ``T_in`` on a PyBaMM whose upwinding uses the Dirichlet value at the inflow;
        otherwise ``(T_in + T_1) / 2``, with ``T_1`` the value in the first cell, which
        needs constant extrapolation on the flow domain (see
        :func:`pytes.compat.fluid_spatial_method`).
    """
    if upwind_uses_boundary_value():
        return T_in
    T_1 = pybamm.boundary_value(T, "left")
    return (T_in + T_1) / 2
