"""Submodels in isolation, and the automatic wiring checks (DESIGN D3)."""

import copy

import numpy as np
import pybamm
import pytest

import pytes
from pytes import conformance
from pytes.models.finned_tube import FinnedTubeParameters
from pytes.submodels import (
    AdvectedFluid,
    BaseSubModel,
    EnthalpyStorage,
    FlowPath,
    StorageGeometry,
)
from pytes.submodels.fluid import HEAT_GAIN, INITIAL_TEMPERATURE


class Composition(pytes.BaseModel):
    """A model made of given submodels, for testing them in isolation"""

    def __init__(self, make_submodels):
        self._make_submodels = make_submodels
        super().__init__("Composition")

    def get_parameters(self):
        return FinnedTubeParameters()

    def set_submodels(self):
        self.submodels.update(self._make_submodels(self.param))

    @property
    def default_parameter_values(self):
        return pytes.models.finned_tube.get_parameter_values()


class Stub(BaseSubModel):
    """Provides the variables returned by ``make(param, stub)``"""

    def __init__(self, param, make, name="stub"):
        self.make = make
        super().__init__(param, name)

    def build(self):
        self.variables = self.make(self.param, self)


z = pybamm.SpatialVariable("z", domains={"primary": "flow path"}, coord_sys="cartesian")
y = pybamm.SpatialVariable(
    "y",
    domains={"primary": "storage depth", "secondary": "flow path"},
    coord_sys="cylindrical polar",
)


def fluid_submodel(param):
    return AdvectedFluid(
        param, param.fluid, FlowPath(z, param.Z, param.area, param.N_tubes)
    )


def test_requires_and_provides_come_from_the_code():
    model = pytes.SharpFrontModel()
    fluid = model.submodels["fluid"]
    assert set(fluid.requires) == {HEAT_GAIN, INITIAL_TEMPERATURE}
    assert "Outlet temperature [K]" in fluid.provides
    assert all(
        isinstance(v, pybamm.CoupledVariable) for v in fluid.coupled_variables.values()
    )
    # Resolved when the model is built: the model itself has no coupled variables left
    for equation in [*model.rhs.values(), *model.initial_conditions.values()]:
        assert not any(
            isinstance(node, pybamm.CoupledVariable) for node in equation.pre_order()
        )


def test_fluid_steady_state_with_uniform_heat_gain():
    # With a uniform heat gain q' per unit length, the steady outlet temperature is
    # T_in + n q' Z / (mdot c_p), exactly (the upwind scheme telescopes), provided the
    # inflow is exactly at T_in (pytes.compat.upwind_inlet_value)
    q = 50.0  # [W.m-1]

    def make(param):
        source = Stub(
            param,
            lambda p, s: {
                HEAT_GAIN: pybamm.PrimaryBroadcast(q, "flow path"),
                INITIAL_TEMPERATURE: p.T_in,
            },
        )
        return {"fluid": fluid_submodel(param), "source": source}

    model = Composition(make)
    pv = model.default_parameter_values
    geometry = {"flow path": {z: {"min": 0, "max": model.param.Z}}}
    sim = pybamm.Simulation(
        model,
        parameter_values=pv,
        geometry=geometry,
        submesh_types={"flow path": pybamm.Uniform1DSubMesh},
        var_pts={z: 20},
        spatial_methods={"flow path": pytes.compat.fluid_spatial_method()},
        solver=pybamm.IDAKLUSolver(rtol=1e-9, atol=1e-9),
    )
    solution = sim.solve([0, 600])
    expected = pv["Inlet temperature [K]"] + pv["Number of tubes"] * q * pv[
        "Tube length [m]"
    ] / (
        pv["Mass flow rate [kg.s-1]"]
        * pv["Heat transfer fluid specific heat capacity [J.kg-1.K-1]"]
    )
    assert solution["Outlet temperature [K]"].entries[-1] == pytest.approx(
        expected, abs=1e-6
    )


def test_insulated_storage_keeps_its_energy():
    def make(param):
        def integrate(symbol):
            return param.N_tubes * pybamm.Integral(pybamm.Integral(symbol, y), z)

        geometry = StorageGeometry(y, integrate, lambda s: pybamm.Integral(s, y))
        storage = EnthalpyStorage(param, param.composite, geometry)
        insulation = Stub(
            param,
            lambda p, s: {
                "Phase-change material boundary heat flux [W.m-2]": (
                    pybamm.PrimaryBroadcast(0, "flow path")
                ),
                # Inside a 2 K melting range: liquid fraction (T - T_solidus) / 2 K = 0.4
                INITIAL_TEMPERATURE: p.T_m - 0.2,
                # Read by the base model's events (none in operating mode None)
                "Outlet temperature [K]": p.T_m,
            },
        )
        return {"storage": storage, "insulation": insulation}

    model = Composition(make)
    storage = model.submodels["storage"]
    assert storage.states == [storage.H]
    geometry = {
        "storage depth": {y: {"min": model.param.R_f, "max": model.param.H}},
        "flow path": {z: {"min": 0, "max": model.param.Z}},
    }
    parameter_values = model.default_parameter_values
    parameter_values["PCM melting range [K]"] = 2
    sim = pybamm.Simulation(
        model,
        parameter_values=parameter_values,
        geometry=geometry,
        submesh_types={d: pybamm.Uniform1DSubMesh for d in geometry},
        var_pts={y: 5, z: 3},
        spatial_methods={d: pybamm.FiniteVolume() for d in geometry},
    )
    solution = sim.solve([0, 600])
    E = solution["Phase-change material thermal energy [J]"].entries
    np.testing.assert_allclose(E, E[0], rtol=1e-12)
    # Constant in time; 0.4 up to the smoothing of the corners, which shifts the liquid
    # fraction by about w**2 / (4 phi), with w the smoothing width in liquid fraction
    phi = solution["Average liquid fraction"].entries
    np.testing.assert_allclose(phi, phi[0], rtol=1e-9)
    assert phi[0] == pytest.approx(0.4, abs=1e-4)


class AlteredSharpFront(pytes.SharpFrontModel):
    """Sharp-front model with its submodels altered by ``alter``"""

    def __init__(self, alter):
        self._alter = alter
        super().__init__()

    def set_submodels(self):
        super().set_submodels()
        self._alter(self.submodels, self.param)


def test_missing_provider_is_detected():
    def alter(submodels, param):
        del submodels["coupling"]

    with pytest.raises(pytes.WiringError, match="which no submodel provides"):
        AlteredSharpFront(alter)


def test_duplicate_provider_is_detected():
    def alter(submodels, param):
        submodels["extra"] = Stub(param, lambda p, s: {HEAT_GAIN: pybamm.Scalar(0)})

    with pytest.raises(pytes.WiringError, match="provided by both"):
        AlteredSharpFront(alter)


def test_domain_mismatch_is_detected():
    def alter(submodels, param):
        submodels["extra"] = Stub(
            param,
            lambda p, s: {
                "Twice the power [W]": 2 * s.coupled("Power [W]", "flow path")
            },
        )

    with pytest.raises(pytes.WiringError, match="provides it on"):
        AlteredSharpFront(alter)


def test_circular_dependency_is_detected():
    def alter(submodels, param):
        submodels["a"] = Stub(param, lambda p, s: {"A [W]": s.coupled("B [W]")}, "a")
        submodels["b"] = Stub(param, lambda p, s: {"B [W]": s.coupled("A [W]")}, "b")

    with pytest.raises(pytes.WiringError, match="Circular dependency"):
        AlteredSharpFront(alter)


def test_parameters_are_read_from_the_code():
    model = pytes.PackedBedModel()
    submodels = model.submodels
    assert "PCM latent heat [J.kg-1]" in submodels["storage"].parameters
    assert "PCM latent heat [J.kg-1]" not in submodels["coupling"].parameters
    assert "Heat transfer coefficient [W.m-2.K-1]" in submodels["coupling"].parameters
    assert submodels["device energy"].parameters == ("Initial temperature [K]",)
    # Domain lengths enter through the geometry, not the equations
    assert model.geometry_parameters == ("Bed length [m]", "Capsule radius [m]")


def test_every_parameter_is_attributed(model_class):
    # Each parameter of the default set that the model uses belongs to a submodel or to
    # the geometry
    model = model_class()
    attributed = set(model.geometry_parameters).union(
        *(submodel.parameters for submodel in model.submodels.values())
    )
    # "citations" lists the sources of the values, as in PyBaMM's own parameter sets
    unused = set(model.default_parameter_values.keys()) - attributed - {"citations"}
    # Parameters kept as hooks, used by no model yet (DESIGN D8, deferred items)
    assert unused <= {
        "Heat transfer fluid conductivity [W.m-1.K-1]",
        "Heat transfer fluid viscosity [Pa.s]",
    }


def test_coupled_variable_is_created_once():
    stub = Stub(FinnedTubeParameters(), lambda p, s: {"A [W]": s.coupled("B [W]")})
    assert stub.coupled("B [W]") is stub.coupled("B [W]")
    assert stub.requires == ("B [W]",)
    assert repr(stub) == "Stub(name='stub')"


def test_invalid_inner_condition():
    model = pytes.SharpFrontModel()
    geometry = model.submodels["storage"].storage_geometry
    with pytest.raises(ValueError, match="Inner condition 'radiation' not recognised"):
        EnthalpyStorage(
            model.param, model.param.composite, geometry, inner_condition="radiation"
        )


class SecondEquation(BaseSubModel):
    """Sets an equation for a variable that another submodel already owns"""

    def __init__(self, param, variable):
        self.variable = variable
        super().__init__(param, "Second equation")

    def build(self):
        self.rhs = {self.variable: pybamm.Scalar(0)}
        self.variables = {"Second equation [W]": pybamm.Scalar(0)}


def test_two_equations_for_one_variable_are_detected():
    def alter(submodels, param):
        submodels["extra"] = SecondEquation(param, submodels["storage"].H)

    with pytest.raises(pytes.WiringError):
        AlteredSharpFront(alter)


def test_conformance_skips_materials_with_internal_states():
    # A material with internal states may make the temperature depend on more than the
    # enthalpy, so the "T depends on H alone" check does not apply (DESIGN D7)
    model = pytes.SharpFrontModel()
    storage = model.submodels["storage"]
    storage.T = storage.T + pybamm.Variable("Internal state")
    with pytest.raises(AssertionError):
        conformance.check_stateless_materials(model)
    storage.material = copy.copy(storage.material)
    storage.material.internal_states = ("Internal state",)
    conformance.check_stateless_materials(model)
