#
# Heat transfer fluid submodels
#
"""Heat transfer fluid (HTF) submodels: the fluid slot of DESIGN D5."""

import pybamm

from .. import compat
from ..variables import add_temperature_variables
from .base_submodel import BaseSubModel

HEAT_GAIN = "Heat transfer fluid heat gain per unit length [W.m-1]"
INITIAL_TEMPERATURE = "Initial uniform temperature [K]"


class FlowPath:
    """
    Geometry of the flow paths, as the fluid submodel sees it.

    The device has ``n_paths`` identical flow paths in parallel, each of length ``length``
    and flow area ``area``. The fluid submodel describes one of them, on the domain
    ``"pipe"`` with coordinate ``z`` (DESIGN D12). Device totals are multiplied by
    ``n_paths``.

    Parameters
    ----------
    z : pybamm.SpatialVariable
        Distance along the flow path from the inlet [m].
    length : pybamm.Symbol
        Length of the flow path [m].
    area : pybamm.Symbol
        Flow area of one path [m2] (for a porous bed, the porosity times the bed area).
    n_paths : pybamm.Symbol
        Number of flow paths.
    """

    def __init__(self, z, length, area, n_paths):
        self.z = z
        self.length = length
        self.area = area
        self.n_paths = n_paths


class AdvectedFluid(BaseSubModel):
    """
    Heat transfer fluid advected along the flow path, with its temperature as the state.

    Per flow path, with ``h`` the specific enthalpy from the fluid-property object,

    ``A_flow rho dh/dt + mdot_path dh/dz = q'``,  for ``0 < z < Z``,

    where ``mdot_path`` is the mass flow rate per path and ``q'`` the heat the fluid gains
    per unit length of flow path (``"Heat transfer fluid heat gain per unit length
    [W.m-1]"``, from the coupling). The inflow is at the inlet temperature, and the outlet
    temperature is the value upwinding advects out of the last cell.

    The enthalpy flux ``mdot_path h`` is upwinded (first order). The inflow uses
    :func:`pytes.compat.upwind_inlet_value`.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_in`` (inlet temperature), ``mdot`` (mass flow rate
        of the whole device), ``temperature_scale`` and ``temperature_reference``.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    flow_path : :class:`FlowPath`
        The geometry of the flow paths.
    """

    requires = (HEAT_GAIN, INITIAL_TEMPERATURE)
    provides = (
        "Heat transfer fluid temperature [K]",
        "Inlet temperature [K]",
        "Outlet temperature [K]",
        "Inlet specific enthalpy [J.kg-1]",
        "Outlet specific enthalpy [J.kg-1]",
        "Mass flow rate [kg.s-1]",
        "Heat transfer fluid thermal energy [J]",
    )
    assumptions = (
        "The fluid is incompressible, with constant density.",
        "Axial conduction and dispersion in the fluid are neglected.",
        "The flow is the same in every flow path.",
    )

    #: Name of this submodel's energy variable (see :class:`DeviceEnergy`)
    energy_variable = "Heat transfer fluid thermal energy [J]"

    def __init__(self, param, fluid, flow_path, name="Heat transfer fluid"):
        super().__init__(param, name)
        self.fluid = fluid
        self.flow_path = flow_path

    def get_fundamental_variables(self):
        param = self.param
        path = self.flow_path
        T_f = pybamm.Variable(
            "Heat transfer fluid temperature [K]",
            domains={"primary": "pipe"},
            scale=param.temperature_scale,
            reference=param.temperature_reference,
        )
        self.T_f = T_f
        # With constant extrapolation (compat.fluid_spatial_method) this is the value in
        # the last cell, which is the temperature at which upwinding advects the fluid out
        T_out = pybamm.boundary_value(T_f, "right")
        T_in = param.T_in
        fluid = self.fluid
        E_f = (
            path.n_paths
            * path.area
            * pybamm.Integral(fluid.rho(T_f) * fluid.h(T_f), path.z)
        )
        variables = {
            "Inlet specific enthalpy [J.kg-1]": fluid.h(T_in),
            "Outlet specific enthalpy [J.kg-1]": fluid.h(T_out),
            "Mass flow rate [kg.s-1]": param.mdot,
            # The enthalpy is zero at the lower temperature limit, so this is the energy
            # above the uniform state at that limit
            "Heat transfer fluid thermal energy [J]": E_f,
        }
        return add_temperature_variables(
            variables,
            {
                "Heat transfer fluid temperature [K]": T_f,
                "Inlet temperature [K]": T_in,
                "Outlet temperature [K]": T_out,
            },
        )

    def uniform_energy(self, T, phi=0):
        """
        Energy of the fluid in the whole device [J] at a uniform temperature ``T`` [K],
        relative to the fluid's enthalpy reference. ``phi`` is ignored.
        """
        path = self.flow_path
        return (
            path.n_paths * path.area * path.length * self.fluid.rho(T) * self.fluid.h(T)
        )

    def set_rhs(self, variables):
        param = self.param
        path = self.flow_path
        fluid = self.fluid
        T_f = self.T_f
        mdot_path = param.mdot / path.n_paths
        mdot_edge = pybamm.PrimaryBroadcastToEdges(mdot_path, ["pipe"])
        enthalpy_flux = mdot_edge * fluid.h(pybamm.upwind(T_f))
        heat_gain = variables[HEAT_GAIN]
        self.rhs[T_f] = (-pybamm.div(enthalpy_flux) + heat_gain) / (
            path.area * fluid.rho(T_f) * fluid.c_p(T_f)
        )

    def set_boundary_conditions(self, variables):
        T_f = self.T_f
        self.boundary_conditions[T_f] = {
            "left": (compat.upwind_inlet_value(T_f, self.param.T_in), "Dirichlet")
        }

    def set_initial_conditions(self, variables):
        self.initial_conditions[self.T_f] = variables[INITIAL_TEMPERATURE]
