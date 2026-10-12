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
    Geometry of a storage region.

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
    def primary_domain(self):
        """The primary domain of the storage variables"""
        return self.domains["primary"]

    @property
    def boundary_domain(self):
        """The primary domain of quantities on the inner boundary (the secondary domain)"""
        return self.domains["secondary"]

    @property
    def volume(self):
        """Volume of the storage in the whole device [m3]"""
        ones = pybamm.FullBroadcast(1, broadcast_domains=self.domains)
        return self.integrate(ones)

    def gradient_from_heat_flux(self, heat_flux, k):
        """
        Normal gradient condition for a heat flux ``heat_flux`` [W.m-2] into the storage
        through the inner side, with conductivity ``k`` [W.m-1.K-1] there: ``-k dT/dn``
        equals the flux, with ``n`` pointing into the storage.
        """
        gradient = -heat_flux / k
        return gradient if self.inner == "left" else -gradient


class EnthalpyStorage(BaseSubModel):
    """
    Conduction in a storage material, by the enthalpy method.

    Enthalpy ``H`` per unit volume, with ``T = H2T(H, states)`` from the material:

    - ``dH/dt = div(k(H) grad T)`` in the storage,
    - zero flux on the outer side (a symmetry plane),
    - on the inner side, either a heat flux into the storage, ``"<label> boundary heat
      flux [W.m-2]"``, or a temperature, ``"<label> boundary temperature [K]"``, from a
      coupling (``inner_condition``).

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
    inner_condition : str, optional
        "heat flux" (default) or "temperature".
    """

    assumptions = (
        "Heat flows by conduction only (no convection in the liquid).",
        "Heat flows along the primary spatial variable only.",
        "The volume change on melting is neglected.",
    )

    def __init__(
        self,
        param,
        material,
        geometry,
        label="Phase-change material",
        inner_condition="heat flux",
    ):
        if inner_condition not in ("heat flux", "temperature"):
            raise ValueError(f"Inner condition '{inner_condition}' not recognised")
        self.material = material
        self.storage_geometry = geometry
        self.label = label
        self.inner_condition = inner_condition
        self.energy_variable = f"{label} thermal energy [J]"
        super().__init__(param, name=f"{label} storage")

    @property
    def states(self):
        """The state variables: the enthalpy, then the material's internal states"""
        return [self.H, *self.internal_states]

    def build(self):
        material = self.material
        geometry = self.storage_geometry
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
        H_surf = pybamm.boundary_value(H, geometry.inner)

        self.rhs = {H: dHdt}
        if self.inner_condition == "heat flux":
            heat_flux = self.coupled(
                f"{label} boundary heat flux [W.m-2]", geometry.boundary_domain
            )
            k_surf = material.k(H_surf, self.internal_states)
            inner = (geometry.gradient_from_heat_flux(heat_flux, k_surf), "Neumann")
        else:
            T_b = self.coupled(
                f"{label} boundary temperature [K]", geometry.boundary_domain
            )
            inner = (T_b, "Dirichlet")
        self.boundary_conditions = {
            T: {geometry.inner: inner, geometry.outer: (pybamm.Scalar(0), "Neumann")}
        }
        self.initial_conditions = {
            H: material.equilibrium_enthalpy(
                self.coupled(INITIAL_TEMPERATURE),
                self.coupled(INITIAL_LIQUID_FRACTION),
            )
        }

        liquid_fraction = material.liquid_fraction(H, self.internal_states)
        H_low = material.equilibrium_enthalpy(self.param.T_low, 0)
        variables = {
            f"{label} enthalpy [J.m-3]": H,
            f"{label} enthalpy rate of change [W.m-3]": dHdt,
            "Liquid fraction": liquid_fraction,
            "Phase": liquid_fraction >= 0.5,
            # Weighted by the volume of this material (DESIGN D13)
            "Average liquid fraction": geometry.integrate(liquid_fraction)
            / geometry.volume,
            # Above the uniform state at the lower temperature limit
            self.energy_variable: geometry.integrate(H - H_low),
        }
        self.variables = add_temperature_variables(
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
        return self.storage_geometry.volume * (
            material.equilibrium_enthalpy(T, phi) - H_low
        )


class SensibleConduction(BaseSubModel):
    """
    Conduction in a sensible material (such as a fin), with its temperature as the state.

    ``rho c_p dT/dt = k div(grad T) + S``, with ``S`` a volumetric heat source
    (``"<label> heat source [W.m-3]"``) and a heat flux into the inner side
    (``"<label> boundary heat flux [W.m-2]"``), both from couplings, and zero flux on the
    outer side.

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
        self.material = material
        self.storage_geometry = geometry
        self.label = label
        self.energy_variable = f"{label} thermal energy [J]"
        super().__init__(param, name=f"{label} conduction")

    def build(self):
        param = self.param
        material = self.material
        geometry = self.storage_geometry
        label = self.label
        T = pybamm.Variable(
            f"{label} temperature [K]",
            domains=geometry.domains,
            scale=param.temperature_scale,
            reference=param.temperature_reference,
        )
        self.T = T
        source = self.coupled(f"{label} heat source [W.m-3]", geometry.primary_domain)
        heat_flux = self.coupled(
            f"{label} boundary heat flux [W.m-2]", geometry.boundary_domain
        )
        self.rhs = {
            T: (material.k * pybamm.div(pybamm.grad(T)) + source) / material.rho_c_p
        }
        self.boundary_conditions = {
            T: {
                geometry.inner: (
                    geometry.gradient_from_heat_flux(heat_flux, material.k),
                    "Neumann",
                ),
                geometry.outer: (pybamm.Scalar(0), "Neumann"),
            }
        }
        self.initial_conditions = {T: self.coupled(INITIAL_TEMPERATURE)}
        variables = {
            self.energy_variable: geometry.integrate(
                material.rho_c_p * (T - param.T_low)
            )
        }
        self.variables = add_temperature_variables(
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
        return (
            self.storage_geometry.volume
            * self.material.rho_c_p
            * (T - self.param.T_low)
        )
