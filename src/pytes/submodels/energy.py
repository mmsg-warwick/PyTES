#
# Device-level power and energy
#
"""Device-level power, energies and initial state (DESIGN D12 to D14)."""

import pybamm

from ..variables import add_temperature_variables
from .base_submodel import BaseSubModel
from .storage import INITIAL_LIQUID_FRACTION, INITIAL_TEMPERATURE


class DeviceEnergy(BaseSubModel):
    """
    Power and energies of the whole device, and its initial state.

    - Power: ``mdot (h_out - h_in)``, positive on discharge (DESIGN D8, D12).
    - Discharged energy: the time integral of the power, solved for by the solver so that
      it can be checked against the change in total thermal energy.
    - Energies: the storage thermal energy is the sum of the storage components' energies,
      and the total thermal energy adds the fluid. Every energy is zero at the uniform state
      at the reference temperature (DESIGN D14).
    - Heat loss power: zero (there is no casing yet), positive for loss.
    - Initial state: uniform at "Initial temperature [K]", solid at the melting temperature
      (DESIGN D14).

    There is no state of charge (DESIGN D13). The energy between two uniform states is
    post-processing: see :func:`pytes.energy_between`, which uses :meth:`uniform_energy`.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_m`` (the melting temperature) and ``T_init``.
    fluid_component : :class:`pytes.submodels.AdvectedFluid`
        The fluid.
    storage_components : list
        The storage submodels. Each has an ``energy_variable`` and a
        ``uniform_energy(T, phi)`` method.
    """

    assumptions = ("There are no heat losses to the surroundings.",)

    def __init__(
        self, param, fluid_component, storage_components, name="Device energy"
    ):
        self.fluid_component = fluid_component
        self.storage_components = list(storage_components)
        super().__init__(param, name)

    @property
    def components(self):
        """All the parts that hold heat: the storage components, then the fluid"""
        return [*self.storage_components, self.fluid_component]

    def uniform_state(self, T):
        """
        The uniform state at temperature ``T`` [K]: solid up to the melting temperature,
        liquid above it.

        Returns
        -------
        T, phi : pybamm.Symbol
            Its temperature [K] and liquid fraction.
        """
        return T, T > self.param.T_m

    def uniform_energy(self, T):
        """
        Total thermal energy [J] of the uniform state at ``T`` [K] (see
        :meth:`uniform_state`). It contains integrals over the storage, so it must be
        discretised before it is evaluated.
        """
        T, phi = self.uniform_state(T)
        E = self.components[0].uniform_energy(T, phi)
        for component in self.components[1:]:
            E = E + component.uniform_energy(T, phi)
        return E

    def build(self):
        param = self.param
        power = self.coupled("Mass flow rate [kg.s-1]") * (
            self.coupled("Outlet specific enthalpy [J.kg-1]")
            - self.coupled("Inlet specific enthalpy [J.kg-1]")
        )
        E_out = pybamm.Variable("Discharged energy [J]", scale=1e6)
        self.rhs = {E_out: power}
        self.initial_conditions = {E_out: pybamm.Scalar(0)}

        E_storage = self.coupled(self.storage_components[0].energy_variable)
        for component in self.storage_components[1:]:
            E_storage = E_storage + self.coupled(component.energy_variable)
        E_total = E_storage + self.coupled(self.fluid_component.energy_variable)
        T_0, phi_0 = self.uniform_state(param.T_init)
        variables = {
            "Power [W]": power,
            "Power [kW]": power / 1e3,
            "Discharged energy [J]": E_out,
            "Discharged energy [kWh]": E_out / 3.6e6,
            "Storage thermal energy [J]": E_storage,
            "Total thermal energy [J]": E_total,
            "Heat loss power [W]": pybamm.Scalar(0),
            INITIAL_LIQUID_FRACTION: phi_0,
        }
        self.variables = add_temperature_variables(
            variables, {INITIAL_TEMPERATURE: T_0}
        )
