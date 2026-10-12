#
# Storage submodels
#
"""Storage submodels: the storage slot of DESIGN D5."""

import pybamm

from ..variables import add_temperature_variables
from .base_submodel import BaseSubModel

INITIAL_TEMPERATURE = "Initial uniform temperature [K]"
INITIAL_LIQUID_FRACTION = "Initial uniform liquid fraction"


class StorageGeometry:
    """
    Geometry of a storage region, as a storage submodel sees it.

    The storage conducts heat along its primary spatial variable only. Its coordinate
    system (cartesian, cylindrical or spherical) is the geometry switch of DESIGN D5: the
    equations are the same, and only the geometric factor in the divergence changes.

    Parameters
    ----------
    variable : pybamm.SpatialVariable
        The primary spatial variable. Its domains are those of the storage variables.
    integrate : callable
        Maps a symbol on the storage domains to its integral over the storage in the whole
        device [symbol units times m3].
    cross_section_integral : callable
        Maps a symbol on the storage domains to its integral over the storage per unit
        length of flow path, for one flow path [symbol units times m2]. Used by ledger
        couplings.
    inner : str, optional
        Side of the primary domain that exchanges heat ("left" or "right", default
        "left"). The other side is a symmetry plane (zero flux).
    """

    def __init__(self, variable, integrate, cross_section_integral, inner="left"):
        self.variable = variable
        self.domains = variable.domains
        self.integrate = integrate
        self.cross_section_integral = cross_section_integral
        self.inner = inner
        self.outer = "right" if inner == "left" else "left"

    @property
    def volume(self):
        """Volume of the storage in the whole device [m3]"""
        ones = pybamm.FullBroadcast(1, broadcast_domains=self.domains)
        return self.integrate(ones)


class EnthalpyStorage(BaseSubModel):
    """
    Conduction in a storage material, by the enthalpy method.

    Enthalpy ``H`` per unit volume, with ``T = H2T(H, states)`` from the material:

    - ``dH/dt = div(k(H) grad T)`` in the storage,
    - zero flux on the outer side (a symmetry plane),
    - on the inner side, the condition the coupling imposes.

    The state list is ``[H]`` plus the material's internal states (none for the current
    materials, DESIGN D7).

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_low`` (lower temperature limit).
    material : :class:`pytes.materials.PhaseChangeMaterial`
        The storage material.
    geometry : :class:`StorageGeometry`
        The geometry of the storage.
    label : str, optional
        Name of the material in variable names (default "Phase-change material"), e.g.
        "<label> enthalpy [J.m-3]".
    """

    assumptions = (
        "Heat flows by conduction only (no convection in the liquid).",
        "Heat flows along the primary spatial variable only.",
        "The volume change on melting is neglected.",
    )
    requires = (INITIAL_TEMPERATURE, INITIAL_LIQUID_FRACTION)

    def __init__(self, param, material, geometry, label="Phase-change material"):
        super().__init__(param, name=f"{label} storage")
        self.material = material
        self.geometry = geometry
        self.label = label
        self.energy_variable = f"{label} thermal energy [J]"
        self.provides = (
            f"{label} enthalpy [J.m-3]",
            f"{label} enthalpy rate of change [W.m-3]",
            f"{label} temperature [K]",
            f"{label} surface temperature [K]",
            f"{label} surface enthalpy [J.m-3]",
            "Liquid fraction",
            "Phase",
            "Average liquid fraction",
            self.energy_variable,
        )

    @property
    def states(self):
        """The state variables: the enthalpy, then the material's internal states"""
        return [self.H, *self.internal_states]

    def get_fundamental_variables(self):
        material = self.material
        geometry = self.geometry
        label = self.label
        H = pybamm.Variable(
            f"{label} enthalpy [J.m-3]",
            domains=geometry.domains,
            scale=material.H_scale,
            reference=material.H_reference,
        )
        self.H = H
        # No current material has internal states (DESIGN D7)
        self.internal_states = ()
        T = material.H2T(H, self.internal_states)
        self.T = T
        dHdt = pybamm.div(material.k(H, self.internal_states) * pybamm.grad(T))
        self.dHdt = dHdt

        liquid_fraction = material.liquid_fraction(H, self.internal_states)
        H_low = material.equilibrium_enthalpy(self.param.T_low, 0)
        variables = {
            f"{label} enthalpy [J.m-3]": H,
            f"{label} enthalpy rate of change [W.m-3]": dHdt,
            f"{label} surface enthalpy [J.m-3]": pybamm.boundary_value(
                H, geometry.inner
            ),
            "Liquid fraction": liquid_fraction,
            "Phase": liquid_fraction >= 0.5,
            # Weighted by the volume of this material (DESIGN D13)
            "Average liquid fraction": geometry.integrate(liquid_fraction)
            / geometry.volume,
            # Above the uniform state at the lower temperature limit
            self.energy_variable: geometry.integrate(H - H_low),
        }
        return add_temperature_variables(
            variables,
            {
                f"{label} temperature [K]": T,
                f"{label} surface temperature [K]": pybamm.boundary_value(
                    T, geometry.inner
                ),
            },
        )

    def uniform_energy(self, T, phi):
        """
        Energy of this storage in the whole device [J] at a uniform temperature ``T`` [K]
        with liquid fraction ``phi``, above the uniform state at the lower temperature
        limit.
        """
        material = self.material
        H_low = material.equilibrium_enthalpy(self.param.T_low, 0)
        return self.geometry.volume * (material.equilibrium_enthalpy(T, phi) - H_low)

    def set_rhs(self, variables):
        self.rhs[self.H] = self.dHdt

    def set_boundary_conditions(self, variables):
        self.boundary_conditions[self.T] = {
            self.geometry.outer: (pybamm.Scalar(0), "Neumann")
        }

    def set_initial_conditions(self, variables):
        self.initial_conditions[self.H] = self.material.equilibrium_enthalpy(
            variables[INITIAL_TEMPERATURE], variables[INITIAL_LIQUID_FRACTION]
        )


class SensibleConduction(BaseSubModel):
    """
    Conduction in a sensible material (such as a fin), with its temperature as the state.

    ``rho c_p dT/dt = k div(grad T) + S``, with ``S`` a volumetric heat source from another
    submodel ("<label> heat source [W.m-3]"), zero flux on the outer side, and on the inner
    side the condition the coupling imposes.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_low``, ``temperature_scale`` and
        ``temperature_reference``.
    material : :class:`pytes.materials.SensibleMaterial`
        The material.
    geometry : :class:`StorageGeometry`
        The geometry.
    label : str, optional
        Name of the part in variable names (default "Fin").
    """

    assumptions = (
        "Heat flows by conduction along the primary spatial variable only.",
        "The material properties are constant.",
    )

    def __init__(self, param, material, geometry, label="Fin"):
        super().__init__(param, name=f"{label} conduction")
        self.material = material
        self.geometry = geometry
        self.label = label
        self.energy_variable = f"{label} thermal energy [J]"
        self.source_variable = f"{label} heat source [W.m-3]"
        self.requires = (self.source_variable, INITIAL_TEMPERATURE)
        self.provides = (
            f"{label} temperature [K]",
            f"{label} surface temperature [K]",
            self.energy_variable,
        )

    def get_fundamental_variables(self):
        param = self.param
        geometry = self.geometry
        label = self.label
        T = pybamm.Variable(
            f"{label} temperature [K]",
            domains=geometry.domains,
            scale=param.temperature_scale,
            reference=param.temperature_reference,
        )
        self.T = T
        rho_c_p = self.material.rho_c_p
        variables = {
            self.energy_variable: geometry.integrate(rho_c_p * (T - param.T_low))
        }
        return add_temperature_variables(
            variables,
            {
                f"{label} temperature [K]": T,
                f"{label} surface temperature [K]": pybamm.boundary_value(
                    T, geometry.inner
                ),
            },
        )

    def uniform_energy(self, T, phi=0):
        """
        Energy of this part in the whole device [J] at a uniform temperature ``T`` [K],
        above the uniform state at the lower temperature limit. ``phi`` is ignored.
        """
        return self.geometry.volume * self.material.rho_c_p * (T - self.param.T_low)

    def set_rhs(self, variables):
        material = self.material
        self.rhs[self.T] = (
            material.k * pybamm.div(pybamm.grad(self.T))
            + variables[self.source_variable]
        ) / material.rho_c_p

    def set_boundary_conditions(self, variables):
        self.boundary_conditions[self.T] = {
            self.geometry.outer: (pybamm.Scalar(0), "Neumann")
        }

    def set_initial_conditions(self, variables):
        self.initial_conditions[self.T] = variables[INITIAL_TEMPERATURE]
