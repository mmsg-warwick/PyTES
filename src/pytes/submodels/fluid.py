#
# Heat transfer fluid submodels
#
"""Heat transfer fluid (HTF) submodels: the fluid slot of DESIGN D5."""

import pybamm

from .. import compat
from .base_submodel import BaseSubModel

HEAT_GAIN = "Heat transfer fluid heat gain per unit length [W.m-1]"
INITIAL_TEMPERATURE = "Initial uniform temperature [K]"
FLUID_ENTHALPY = "Heat transfer fluid specific enthalpy [J.kg-1]"
FLUID_TEMPERATURE = "Heat transfer fluid temperature [K]"


class FlowPath:
    """
    Geometry of the flow paths, as the fluid submodel sees it.

    The device has ``n_paths`` identical flow paths in parallel, each of length ``length``
    and flow area ``area``. The fluid submodel describes one of them, on the domain
    ``"flow path"`` with coordinate ``z`` (DESIGN D12). Device totals are multiplied by
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
    Heat transfer fluid advected along the flow path, with its specific enthalpy ``h`` as
    the state (DESIGN D5). Per flow path,

    ``A_flow rho dh/dt + mdot_path dh/dz = q'``,  for ``0 < z < Z``,

    where ``mdot_path`` is the mass flow rate per path and ``q'`` the heat the fluid gains
    per unit length of flow path (``"Heat transfer fluid heat gain per unit length
    [W.m-1]"``, from the coupling). The inflow is at the inlet enthalpy ``h(T_in)``, and the
    outlet enthalpy is the value upwinding advects out of the last cell. Temperatures and
    other properties come from the fluid-property object at the state: ``T = T(h)``, and the
    outlet temperature is ``T(h_out)``.

    The enthalpy flux ``mdot_path h`` is upwinded, at second order with the default spatial
    method (:func:`pytes.compat.fluid_spatial_method`, F-052). The inflow uses
    :func:`pytes.compat.upwind_inlet_value`.

    It also provides the flow as it is usually measured (issue #14): the volume flow rate
    of the whole device at the inlet density, ``mdot / rho(h_in)``, and its time integral,
    the pumped volume (a solver state, zero at the start); the mean velocity along the
    flow path, ``mdot_path / (A_flow rho(h))`` (in a packed bed, the interstitial
    velocity); and the inlet-outlet temperature difference, ``T_in - T_out``.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_in`` (inlet temperature), ``mdot`` (mass flow rate
        of the whole device), ``T_ref``, ``temperature_scale`` and ``temperature_reference``
        (to scale the enthalpy like a temperature).
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object.
    flow_path : :class:`FlowPath`
        The geometry of the flow paths.
    """

    assumptions = (
        "The fluid is incompressible, with constant density.",
        "Axial conduction and dispersion in the fluid are neglected.",
        "The flow is the same in every flow path.",
    )

    #: Name of this submodel's energy variable (see :class:`DeviceEnergy`)
    energy_variable = "Heat transfer fluid thermal energy [J]"

    def __init__(self, param, fluid, flow_path, name="Heat transfer fluid"):
        self.fluid = fluid
        self.flow_path = flow_path
        super().__init__(param, name)

    def build(self):
        param = self.param
        path = self.flow_path
        fluid = self.fluid
        # Scaled like a temperature: for a constant-c_p liquid the scaled enthalpy equals
        # the scaled temperature
        h_f = pybamm.Variable(
            FLUID_ENTHALPY,
            domains={"primary": "flow path"},
            scale=fluid.h(param.T_ref + param.temperature_scale) - fluid.h(param.T_ref),
            reference=fluid.h(param.temperature_reference),
        )
        self.h_f = h_f
        T_in = param.T_in
        h_in = fluid.h(T_in)
        # With constant extrapolation (compat.fluid_spatial_method) this is the value in
        # the last cell, which is the enthalpy at which upwinding advects the fluid out
        h_out = pybamm.boundary_value(h_f, "right")

        mdot_path = param.mdot / path.n_paths
        mdot_edge = pybamm.PrimaryBroadcastToEdges(mdot_path, ["flow path"])
        enthalpy_flux = mdot_edge * pybamm.upwind(h_f)
        heat_gain = self.coupled(HEAT_GAIN, "flow path")
        self.rhs = {
            h_f: (-pybamm.div(enthalpy_flux) + heat_gain) / (path.area * fluid.rho(h_f))
        }
        self.boundary_conditions = {
            h_f: {"left": (compat.upwind_inlet_value(h_f, h_in), "Dirichlet")}
        }
        self.initial_conditions = {h_f: fluid.h(self.coupled(INITIAL_TEMPERATURE))}

        E_f = path.n_paths * path.area * pybamm.Integral(fluid.rho(h_f) * h_f, path.z)

        volume_flow_rate = param.mdot / fluid.rho(h_in)
        # Scaled by the fluid volume of the device: the number of times it was replaced
        pumped = pybamm.Variable(
            "Pumped volume [m3]", scale=path.n_paths * path.area * path.length
        )
        self.rhs = {**self.rhs, pumped: volume_flow_rate}
        self.initial_conditions = {**self.initial_conditions, pumped: pybamm.Scalar(0)}
        # The mass flux along the flow path over the local density
        velocity = pybamm.PrimaryBroadcast(mdot_path / path.area, "flow path") / (
            fluid.rho(h_f)
        )

        variables = {
            FLUID_ENTHALPY: h_f,
            "Inlet specific enthalpy [J.kg-1]": h_in,
            "Outlet specific enthalpy [J.kg-1]": h_out,
            "Mass flow rate [kg.s-1]": param.mdot,
            # The enthalpy is zero at the reference temperature, so this is the energy
            # above the uniform state at that temperature
            self.energy_variable: E_f,
        }
        variables.update(
            {
                FLUID_TEMPERATURE: fluid.T(h_f),
                "Inlet temperature [K]": T_in,
                "Outlet temperature [K]": fluid.T(h_out),
                "Inlet-outlet temperature difference [K]": T_in - fluid.T(h_out),
                "Heat transfer fluid velocity [m.s-1]": velocity,
                "Volume flow rate [m3.s-1]": volume_flow_rate,
                "Pumped volume [m3]": pumped,
            }
        )
        self.variables = variables

    def uniform_energy(self, T):
        """
        Energy of the fluid in the whole device [J] at a uniform temperature ``T`` [K],
        relative to the fluid's enthalpy reference.
        """
        path = self.flow_path
        h = self.fluid.h(T)
        return path.n_paths * path.area * path.length * self.fluid.rho(h) * h
