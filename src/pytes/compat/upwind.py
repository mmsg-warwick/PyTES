"""
Inflow value of :func:`pybamm.upwind`.

Upstream: pybamm-team/PyBaMM#3526 and PR #3979 (upwinding in finite volumes). The inflow bug
below is not yet filed as its own issue; the write-up is in the ``heat_batteries`` repository,
``notes/pybamm_upwind_handoff.md``.

Problem: upwinding imposes a Dirichlet condition ``T_bc`` through a ghost node of value
``2 T_bc - T_1`` (``T_1`` is the value in the first cell) and advects that ghost value into
the domain, so the fluid flowing in is not at ``T_bc``.

Workaround: set ``T_bc = (T_in + T_1) / 2``, so that the ghost node is exactly ``T_in``, with
boundary values on the flow domain taken from the end cells (constant extrapolation).

Remove when: PyBaMM's upwinding uses the Dirichlet value itself as the inflow value. Then
use ``T_in`` as the boundary condition and drop :func:`fluid_spatial_method`'s extrapolation
options, checking that the outlet value is still the value in the last cell.
"""

import pybamm


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
        ``(T_in + T_1) / 2``, with ``T_1`` the value in the first cell. This needs constant
        extrapolation on the flow domain (see :func:`fluid_spatial_method`).
    """
    T_1 = pybamm.boundary_value(T, "left")
    return (T_in + T_1) / 2


def fluid_spatial_method():
    """
    Finite volumes whose boundary values are the values in the end cells (constant
    extrapolation, ignoring boundary conditions), as :func:`upwind_inlet_value` needs. The
    outlet value is then the value upwinding advects out of the domain.

    Returns
    -------
    pybamm.FiniteVolume
    """
    return pybamm.FiniteVolume(
        {
            "extrapolation": {
                "order": {"gradient": "quadratic", "value": "constant"},
                "use bcs": False,
            }
        }
    )
