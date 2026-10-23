"""
A second-order, limited upwind scheme for the advection of the heat transfer fluid.

Upstream: pybamm-team/PyBaMM#3526 and PR #3979 (upwinding in finite volumes), issue #7 here.
PyBaMM's :func:`pybamm.upwind` is first order, which smears a temperature front moving
through the flow path.

Feature: :class:`LimitedFiniteVolume` discretises :func:`pybamm.upwind` with a MUSCL
reconstruction and the van Albada limiter, on uniform or non-uniform meshes, the default
scheme for the fluid (:func:`fluid_spatial_method`, F-052). The fluid's equations are
unchanged, as the scheme only changes the value of the fluid on each cell face, so energy is
still conserved exactly.

Remove when: PyBaMM's finite volumes offer a limited upwind scheme. Then select it in
:func:`fluid_spatial_method`, checking that the inflow and outflow values are unchanged.
"""

import numpy as np
import pybamm
from scipy.sparse import coo_matrix

#: Boundary values on the flow path from the end cells (constant extrapolation, ignoring
#: boundary conditions), as :func:`pytes.compat.upwind_inlet_value` needs
FLUID_OPTIONS = {
    "extrapolation": {
        "order": {"gradient": "quadratic", "value": "constant"},
        "use bcs": False,
    }
}


class LimitedFiniteVolume(pybamm.FiniteVolume):
    """
    Finite volumes with a second-order, limited upwind scheme (MUSCL with the van Albada
    limiter) for :func:`pybamm.upwind`.

    First-order upwinding takes the value on a face from the cell upstream of it. This
    scheme adds a limited gradient: on the face ``j + 1/2`` downstream of cell ``j``,

    ``h_{j+1/2} = h_j + g_j (z_{j+1/2} - z_j)``,

    with ``g_j`` the van Albada average of the backward and forward gradients,

    ``a = (h_j - h_{j-1}) / (z_j - z_{j-1})``,  ``b = (h_{j+1} - h_j) / (z_{j+1} - z_j)``,

    ``g_j = (a + b) max(a b, 0) / (a^2 + b^2 + eps^2)``,

    so it works on non-uniform meshes. The limited gradient is zero at a local extremum,
    so no new extremum appears; it is continuous, but its derivative jumps at extrema, as
    any limiter that prevents oscillations must. ``eps`` keeps it defined where both
    gradients vanish: ``regularisation`` times the variable's scale over the domain length.

    At the ends the scheme is first order, as PyBaMM's: the inflow face takes the inflow
    value (the ghost node of :func:`pybamm.upwind`), and the outflow face takes the value
    in the last cell, so the outflow value is the boundary value with constant
    extrapolation (see :func:`fluid_spatial_method`). For the gradients, these two values
    sit on the inflow and outflow faces: the last cell, a first-order donor, holds the
    value it advects out. A steady linear profile is then reconstructed exactly.

    Parameters
    ----------
    options : dict, optional
        Options of :class:`pybamm.FiniteVolume`.
    regularisation : float, optional
        Relative size of ``eps`` (default 1e-6).
    """

    def __init__(self, options=None, regularisation=1e-6):
        super().__init__(options)
        self.regularisation = regularisation

    def upwind_or_downwind(self, symbol, discretised_symbol, bcs, direction):
        """
        The values on the cell faces, upwinded with a limited gradient (see the class
        docstring). Only upwinding is implemented.

        Parameters
        ----------
        symbol : pybamm.Symbol
            The advected variable.
        discretised_symbol : pybamm.Symbol
            The discretised variable.
        bcs : dict
            The boundary conditions; a Dirichlet condition on the left gives the inflow.
        direction : str
            "upwind".

        Raises
        ------
        NotImplementedError
            For downwinding.
        """
        if direction != "upwind":
            raise NotImplementedError(
                "LimitedFiniteVolume only implements upwinding, not downwinding"
            )
        # First-order face values: the inflow value, then the value in each cell
        faces = super().upwind_or_downwind(symbol, discretised_symbol, bcs, direction)
        submesh = self.mesh[symbol.domain]
        n = submesh.npts
        edges, nodes = submesh.edges, submesh.nodes
        repeats = self._get_auxiliary_domain_repeats(symbol.domains)

        # Where the values sit: the inflow face, the cell centres, and the outflow face
        # for the last cell (see the class docstring)
        positions = np.concatenate([[edges[0]], nodes[:-1], [edges[-1]]])
        spacing = np.diff(positions)
        # Rows 1 to n - 1 are the interior faces, downstream of cells 1 to n - 1 (the
        # rows of the inflow and outflow faces are zero, so they stay first order)
        rows = np.arange(1, n)

        def matrix(columns, values):
            sub = coo_matrix((values, (rows, columns)), shape=(n + 1, n + 1)).tocsr()
            return pybamm.Matrix(self._block_diagonal(sub, repeats))

        # Backward and forward gradients at each interior face
        backward = (
            matrix(rows, 1 / spacing[rows - 1]) @ faces
            - matrix(rows - 1, 1 / spacing[rows - 1]) @ faces
        )
        forward = (
            matrix(rows + 1, 1 / spacing[rows]) @ faces
            - matrix(rows, 1 / spacing[rows]) @ faces
        )

        scale = symbol.scale if isinstance(symbol, pybamm.Variable) else 1
        scale = scale.evaluate() if isinstance(scale, pybamm.Symbol) else scale
        eps = self.regularisation * np.abs(scale) / (edges[-1] - edges[0])
        gradient = (
            (backward + forward)
            * pybamm.maximum(backward * forward, 0)
            / (backward**2 + forward**2 + eps**2)
        )

        # Distance from each cell centre to the face downstream of it
        distance = np.zeros(n + 1)
        distance[rows] = edges[rows] - nodes[rows - 1]
        distance = pybamm.Vector(np.tile(distance, repeats))
        return faces + distance * gradient


def fluid_spatial_method(scheme="second order", regularisation=1e-6):
    """
    The spatial method for the fluid's flow path: finite volumes whose boundary values are
    the values in the end cells (constant extrapolation, ignoring boundary conditions), as
    :func:`pytes.compat.upwind_inlet_value` needs, so the outlet value is the value
    advected out of the domain.

    Parameters
    ----------
    scheme : str, optional
        "second order" (default), :class:`LimitedFiniteVolume` (F-052); or "first order",
        PyBaMM's own upwinding, e.g. ``pybamm.Simulation(model, spatial_methods={**
        model.default_spatial_methods, "flow path": fluid_spatial_method("first
        order")})``.
    regularisation : float, optional
        See :class:`LimitedFiniteVolume`.

    Returns
    -------
    pybamm.FiniteVolume

    Raises
    ------
    ValueError
        If the scheme is not recognised.
    """
    if scheme == "second order":
        return LimitedFiniteVolume(FLUID_OPTIONS, regularisation=regularisation)
    if scheme == "first order":
        return pybamm.FiniteVolume(FLUID_OPTIONS)
    raise ValueError(
        f"Scheme '{scheme}' not recognised; it must be 'second order' or 'first order'"
    )
