#
# Storage submodels
#
"""Storage submodels: the storage slot of DESIGN D5."""

import pybamm

from .base_submodel import BaseSubModel

INITIAL_TEMPERATURE = "Initial uniform temperature [K]"


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
    flow_path : :class:`pytes.submodels.FlowPath`, optional
        Given for a storage averaged along the flow path (``"storage along flow path":
        "averaged"``, DESIGN D4): one storage cross-section stands for all of them,
        exchanging heat with the fluid averaged along the flow path. Its domains then
        exclude the flow path, and ``integrate`` multiplies by the flow path length.
    """

    def __init__(
        self,
        variable,
        integrate,
        cross_section_integral,
        inner="left",
        flow_path=None,
    ):
        self.variable = variable
        self.domains = variable.domains
        self.integrate = integrate
        self.cross_section_integral = cross_section_integral
        self.inner = inner
        self.outer = "right" if inner == "left" else "left"
        self.flow_path = flow_path

    @property
    def averaged(self):
        """Whether the storage is averaged along the flow path"""
        return self.flow_path is not None

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


class LumpedGeometry:
    """
    Geometry of a lumped storage: each storage element (e.g. a capsule) has a uniform
    temperature, so the storage has no spatial variable of its own (issue #5). It lives on
    the flow path, or nowhere when it is averaged along the flow path too.

    Parameters
    ----------
    integrate : callable
        Maps a symbol on the storage domains to its integral over the storage in the whole
        device [symbol units times m3].
    cross_section_integral : callable
        Maps a symbol on the storage domains to its integral over the storage per unit
        length of flow path, for one flow path [symbol units times m2]. Used by ledger
        couplings.
    surface_to_volume : pybamm.Symbol
        Surface area of a storage element over its volume [m-1], e.g. ``3 / R`` for a
        sphere of radius ``R``.
    flow_path : :class:`pytes.submodels.FlowPath`
        The flow path.
    averaged : bool, optional
        Whether the storage is also averaged along the flow path (``"storage along flow
        path": "averaged"``, DESIGN D4; default False): one element then stands for all of
        them, exchanging heat with the fluid averaged along the flow path.
    """

    def __init__(
        self,
        integrate,
        cross_section_integral,
        surface_to_volume,
        flow_path,
        averaged=False,
    ):
        self.integrate = integrate
        self.cross_section_integral = cross_section_integral
        self.surface_to_volume = surface_to_volume
        self.flow_path = flow_path if averaged else None
        self.domains = {} if averaged else {"primary": "flow path"}

    @property
    def averaged(self):
        """Whether the storage is averaged along the flow path"""
        return self.flow_path is not None

    @property
    def primary_domain(self):
        """The domain of the storage variables: the flow path, or none when averaged"""
        return self.domains.get("primary", [])

    @property
    def boundary_domain(self):
        """The domain of quantities on the element surface, that of the storage"""
        return self.primary_domain

    @property
    def volume(self):
        """Volume of the storage in the whole device [m3]"""
        if self.averaged:
            return self.integrate(pybamm.Scalar(1))
        return self.integrate(pybamm.PrimaryBroadcast(1, self.primary_domain))


class EnthalpyStorage(BaseSubModel):
    """
    Conduction in a storage material, by the enthalpy method.

    Enthalpy ``H`` per unit volume, with ``T = H2T(H, states)`` from the material:

    - ``dH/dt = div(k(H) grad T) + S`` in the storage, with ``S`` an optional volumetric
      heat source, ``"<label> heat source [W.m-3]"``, from a coupling (``heat_source``),
    - zero flux on the outer side (a symmetry plane),
    - on the inner side, either a heat flux into the storage, ``"<label> boundary heat
      flux [W.m-2]"``, or a temperature, ``"<label> boundary temperature [K]"``, from a
      coupling (``inner_condition``).

    The same submodel holds phase-change and sensible materials (DESIGN D5); only the
    former provide liquid-fraction variables. The state list is ``[H]`` plus the
    material's internal states (none for the current materials, DESIGN D7).

    It also provides its conductivity, "<label> thermal conductivity [W.m-1.K-1]".

    Ledger couplings (DESIGN D6) take the heat that crossed the storage's boundaries from
    ``"<label> conduction heating rate [W.m-3]"``, ``div(k grad T)``: its integral over the
    storage telescopes to the discrete boundary fluxes, with or without a heat source.

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_ref`` (reference temperature).
    material : :class:`pytes.materials.PhaseChangeMaterial` or \
:class:`pytes.materials.SensibleMaterial`
        The storage material.
    geometry : :class:`StorageGeometry`
        The geometry of the storage.
    label : str, optional
        Name of the material in variable names (default "Phase-change material"), e.g.
        "<label> enthalpy [J.m-3]".
    inner_condition : str, optional
        "heat flux" (default) or "temperature".
    heat_source : bool, optional
        Whether the storage has a volumetric heat source (default False).
    H_scale, H_reference : pybamm.Symbol, optional
        Scale and reference of the enthalpy variable (default: the material's).
    """

    def __init__(
        self,
        param,
        material,
        geometry,
        label="Phase-change material",
        inner_condition="heat flux",
        heat_source=False,
        H_scale=None,
        H_reference=None,
    ):
        if inner_condition not in ("heat flux", "temperature"):
            raise ValueError(f"Inner condition '{inner_condition}' not recognised")
        self.material = material
        self.storage_geometry = geometry
        self.label = label
        self.inner_condition = inner_condition
        self.heat_source = heat_source
        self.H_scale = material.H_scale if H_scale is None else H_scale
        self.H_reference = material.H_reference if H_reference is None else H_reference
        self.energy_variable = f"{label} thermal energy [J]"
        self.assumptions = ("Heat flows along the primary spatial variable only.",)
        if material.changes_phase:
            self.assumptions += (
                "Heat flows by conduction only (no convection in the liquid).",
                "The volume change on melting is neglected.",
            )
        super().__init__(param, name=f"{label} storage")

    @property
    def states(self):
        """The state variables, the enthalpy and then the material's internal states"""
        return [self.H, *self.internal_states]

    def build(self):
        material = self.material
        geometry = self.storage_geometry
        label = self.label
        H = pybamm.Variable(
            f"{label} enthalpy [J.m-3]",
            domains=geometry.domains,
            scale=self.H_scale,
            reference=self.H_reference,
        )
        self.H = H
        # No current material has internal states (DESIGN D7)
        self.internal_states = ()
        T = material.H2T(H, self.internal_states)
        self.T = T
        k = material.k(H, self.internal_states)
        conduction = pybamm.div(k * pybamm.grad(T))
        dHdt = conduction
        if self.heat_source:
            dHdt = dHdt + self.coupled(
                f"{label} heat source [W.m-3]", geometry.primary_domain
            )
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
        self.initial_conditions = {H: material.T2H(self.coupled(INITIAL_TEMPERATURE))}

        H_ref = material.T2H(self.param.T_ref)
        variables = {
            f"{label} enthalpy [J.m-3]": H,
            f"{label} enthalpy rate of change [W.m-3]": dHdt,
            f"{label} conduction heating rate [W.m-3]": conduction,
            # Above the uniform state at the reference temperature
            self.energy_variable: geometry.integrate(H - H_ref),
        }
        if material.changes_phase:
            liquid_fraction = material.liquid_fraction(H, self.internal_states)
            variables.update(
                {
                    "Liquid fraction": liquid_fraction,
                    "Phase": liquid_fraction >= 0.5,
                    # Weighted by the volume of this material (DESIGN D13)
                    "Average liquid fraction": geometry.integrate(liquid_fraction)
                    / geometry.volume,
                }
            )
        variables[f"{label} temperature [K]"] = T
        variables[f"{label} surface temperature [K]"] = pybamm.boundary_value(
            T, geometry.inner
        )
        variables[f"{label} thermal conductivity [W.m-1.K-1]"] = k
        self.variables = variables

    def uniform_energy(self, T):
        """
        Energy of this storage in the whole device [J] at a uniform temperature ``T`` [K],
        above the uniform state at the reference temperature.
        """
        material = self.material
        H_ref = material.T2H(self.param.T_ref)
        return self.storage_geometry.volume * (material.T2H(T) - H_ref)


class LumpedStorage(EnthalpyStorage):
    """
    A storage whose elements each have a uniform temperature (a lumped capacitance, issue
    #5), by the enthalpy method.

    Enthalpy ``H`` per unit volume, one value per element, with ``T = H2T(H, states)`` from
    the material: ``dH/dt = (S / V) q``, with ``q`` the heat flux into an element through
    its surface, ``"<label> boundary heat flux [W.m-2]"``, from a coupling, and ``S / V``
    the element's surface area over its volume.

    It provides the same variables as :class:`EnthalpyStorage`, so that the couplings and
    the device energy work on either. Its "conduction heating rate" is ``(S / V) q``, the
    volume average of ``div(k grad T)`` over an element, so a ledger coupling (DESIGN D6)
    takes exactly the heat the storage gains. The surface temperature is the element's
    temperature. A surface flux law may use its conductivity, "<label> thermal
    conductivity [W.m-1.K-1]", to correct for the conduction inside the element (e.g.
    :class:`pytes.submodels.Jeffreson`).

    Parameters
    ----------
    param : object
        The model's parameters. Uses ``T_ref`` (reference temperature).
    material : :class:`pytes.materials.PhaseChangeMaterial` or \
:class:`pytes.materials.SensibleMaterial`
        The storage material.
    geometry : :class:`LumpedGeometry`
        The geometry of the storage.
    label : str, optional
        Name of the material in variable names (default "Phase-change material").
    H_scale, H_reference : pybamm.Symbol, optional
        Scale and reference of the enthalpy variable (default: the material's).
    """

    def __init__(
        self,
        param,
        material,
        geometry,
        label="Phase-change material",
        H_scale=None,
        H_reference=None,
    ):
        super().__init__(
            param, material, geometry, label, H_scale=H_scale, H_reference=H_reference
        )
        self.assumptions = (
            "Each storage element has a uniform temperature (no conduction resistance "
            "inside it).",
            *self.assumptions[1:],
        )

    def build(self):
        material = self.material
        geometry = self.storage_geometry
        label = self.label
        H = pybamm.Variable(
            f"{label} enthalpy [J.m-3]",
            domains=geometry.domains,
            scale=self.H_scale,
            reference=self.H_reference,
        )
        self.H = H
        self.internal_states = ()
        T = material.H2T(H, self.internal_states)
        self.T = T
        heat_flux = self.coupled(
            f"{label} boundary heat flux [W.m-2]", geometry.boundary_domain
        )
        heating = geometry.surface_to_volume * heat_flux

        self.rhs = {H: heating}
        self.initial_conditions = {H: material.T2H(self.coupled(INITIAL_TEMPERATURE))}

        H_ref = material.T2H(self.param.T_ref)
        variables = {
            f"{label} enthalpy [J.m-3]": H,
            f"{label} enthalpy rate of change [W.m-3]": heating,
            f"{label} conduction heating rate [W.m-3]": heating,
            self.energy_variable: geometry.integrate(H - H_ref),
        }
        if material.changes_phase:
            liquid_fraction = material.liquid_fraction(H, self.internal_states)
            variables.update(
                {
                    "Liquid fraction": liquid_fraction,
                    "Phase": liquid_fraction >= 0.5,
                    "Average liquid fraction": geometry.integrate(liquid_fraction)
                    / geometry.volume,
                }
            )
        variables[f"{label} temperature [K]"] = T
        variables[f"{label} surface temperature [K]"] = T
        variables[f"{label} thermal conductivity [W.m-1.K-1]"] = material.k(
            H, self.internal_states
        )
        self.variables = variables
