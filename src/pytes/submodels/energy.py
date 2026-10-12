#
# Device-level power, energy and state of charge
#
"""Device-level power, energies, state of charge and initial state (DESIGN D12 to D14)."""

import pybamm

from ..variables import add_temperature_variables
from .base_submodel import BaseSubModel
from .storage import INITIAL_LIQUID_FRACTION, INITIAL_TEMPERATURE


class DeviceEnergy(BaseSubModel):
    """
    Power, energies and state of charge of the whole device, and its initial state.

    - Power: ``mdot (h_out - h_in)``, positive on discharge (DESIGN D8, D12).
    - Discharged energy: the time integral of the power, solved for by the solver so that
      it can be checked against the change in total thermal energy.
    - Energies: the storage thermal energy is the sum of the storage components' energies,
      and the total thermal energy adds the fluid. Every energy is zero at the uniform state
      at the lower temperature limit (DESIGN D14).
    - Heat loss power: zero (there is no casing yet), positive for loss.
    - State of charge: total thermal energy over the capacity, which is the total thermal
      energy at the uniform state at the upper temperature limit (DESIGN D13).
    - Initial state: the uniform state whose state of charge is "Initial state of charge"
      (DESIGN D14).

    The uniform states are parametrised by a temperature and a liquid fraction: below the
    melting temperature fully solid, above it fully liquid, and at it with any liquid
    fraction. Each component's energy is linear in each of the three pieces, so the initial
    state follows from the energies at the window limits and at the solidus and liquidus.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_low``, ``T_high``, ``T_m`` (the melting
        temperature that separates the pieces) and ``initial_soc``.
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

    def uniform_energy(self, T, phi):
        """Total thermal energy [J] of the uniform state at ``T`` [K] and ``phi``"""
        E = self.components[0].uniform_energy(T, phi)
        for component in self.components[1:]:
            E = E + component.uniform_energy(T, phi)
        return E

    def initial_state(self, soc):
        """
        The uniform state with state of charge ``soc``.

        Returns
        -------
        T, phi : pybamm.Symbol
            Its temperature [K] and liquid fraction.
        """
        param = self.param
        T_low, T_m, T_high = param.T_low, param.T_m, param.T_high
        E_solidus = self.uniform_energy(T_m, 0)
        E_liquidus = self.uniform_energy(T_m, 1)
        E_high = self.uniform_energy(T_high, 1)
        E = soc * E_high

        def fraction(E_start, E_end):
            # Fraction of the piece from E_start to E_end covered by E, clipped to
            # [0, 1] (a piece of zero width, e.g. no latent heat, gives 0 or 1)
            width = pybamm.maximum(E_end - E_start, 1e-12 * E_high)
            return pybamm.minimum(pybamm.maximum((E - E_start) / width, 0), 1)

        T = (
            T_low
            + fraction(0, E_solidus) * (T_m - T_low)
            + fraction(E_liquidus, E_high) * (T_high - T_m)
        )
        phi = fraction(E_solidus, E_liquidus)
        return T, phi

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
        capacity = self.uniform_energy(param.T_high, 1)
        T_0, phi_0 = self.initial_state(param.initial_soc)
        variables = {
            "Power [W]": power,
            "Power [kW]": power / 1e3,
            "Discharged energy [J]": E_out,
            "Discharged energy [kWh]": E_out / 3.6e6,
            "Storage thermal energy [J]": E_storage,
            "Total thermal energy [J]": E_total,
            "Heat loss power [W]": pybamm.Scalar(0),
            "Thermal capacity [J]": capacity,
            "State of charge": E_total / capacity,
            INITIAL_LIQUID_FRACTION: phi_0,
        }
        self.variables = add_temperature_variables(
            variables, {INITIAL_TEMPERATURE: T_0}
        )
