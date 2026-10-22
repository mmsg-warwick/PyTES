#
# Device-level power and energy
#
"""Device-level power, energies and initial state (DESIGN D12 to D14)."""

import pybamm

from .base_submodel import BaseSubModel
from .storage import INITIAL_TEMPERATURE


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
    - Initial state: uniform at "Initial temperature [K]" (DESIGN D14). Each component
      starts at its equilibrium state at that temperature: for a sharp melting point,
      solid at the melting temperature; with a melting range, partly liquid inside it.

    There is no state of charge (DESIGN D13). The energy between two uniform states is
    post-processing: see :func:`pytes.energy_between`, which uses :meth:`uniform_energy`.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_init``.
    fluid_component : :class:`pytes.submodels.AdvectedFluid`
        The fluid.
    storage_components : list
        The storage submodels. Each has an ``energy_variable`` and a
        ``uniform_energy(T)`` method.
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
        """All the parts that hold heat, the storage components and then the fluid"""
        return [*self.storage_components, self.fluid_component]

    def uniform_energy(self, T):
        """
        Total thermal energy [J] of the uniform equilibrium state at ``T`` [K]. It contains
        integrals over the storage, so it must be discretised before it is evaluated.
        """
        E = self.components[0].uniform_energy(T)
        for component in self.components[1:]:
            E = E + component.uniform_energy(T)
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
        variables = {
            "Power [W]": power,
            "Discharged energy [J]": E_out,
            "Storage thermal energy [J]": E_storage,
            "Total thermal energy [J]": E_total,
            "Heat loss power [W]": pybamm.Scalar(0),
            INITIAL_TEMPERATURE: param.T_init,
        }
        self.variables = variables


class PerAreaTotals(BaseSubModel):
    """
    Device totals per unit of a reference area, as family-specific twins of the shared
    whole-device outputs (DESIGN D4): for each total ``"<name> [<unit>]"``, the variable
    ``"<name> per unit area [<unit>.m-2]"``.

    Parameters
    ----------
    param : object
        The model's parameters.
    area : pybamm.Symbol
        The reference area [m2], e.g. a bed cross-section.
    totals : iterable of str, optional
        Names of the totals, each ending in "[W]" or "[J]" (default: power, discharged
        energy, storage and total thermal energy).
    """

    def __init__(
        self,
        param,
        area,
        totals=(
            "Power [W]",
            "Discharged energy [J]",
            "Storage thermal energy [J]",
            "Total thermal energy [J]",
        ),
        name="Per-area totals",
    ):
        self.area = area
        self.totals = tuple(totals)
        super().__init__(param, name)

    def build(self):
        variables = {}
        for total in self.totals:
            stem, unit = total[: total.rindex("[")].strip(), total[total.rindex("[") :]
            per_area = f"{stem} per unit area {unit[:-1]}.m-2]"
            variables[per_area] = self.coupled(total) / self.area
        self.variables = variables
