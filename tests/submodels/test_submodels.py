"""Submodels in isolation, and the automatic wiring checks (DESIGN D3)."""

import numpy as np
import pybamm
import pytest

import pytes
from pytes.models.finned_pipe import FinnedPipeParameters
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
        return FinnedPipeParameters()

    def set_submodels(self):
        self.submodels.update(self._make_submodels(self.param))

    @property
    def default_parameter_values(self):
        return pytes.models.finned_pipe.get_parameter_values()


class Stub(BaseSubModel):
    """Provides the variables returned by ``make(param, stub)``"""

    def __init__(self, param, make, name="stub"):
        self.make = make
        super().__init__(param, name)

    def build(self):
        self.variables = self.make(self.param, self)


z = pybamm.SpatialVariable("z", domains={"primary": "pipe"}, coord_sys="cartesian")
y = pybamm.SpatialVariable(
    "y",
    domains={"primary": "PCM vertical", "secondary": "pipe"},
    coord_sys="cylindrical polar",
)


def fluid_submodel(param):
    return AdvectedFluid(
        param, param.fluid, FlowPath(z, param.Z, param.area, param.N_pipes)
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
                HEAT_GAIN: pybamm.PrimaryBroadcast(q, "pipe"),
                INITIAL_TEMPERATURE: p.T_in,
            },
        )
        return {"fluid": fluid_submodel(param), "source": source}

    model = Composition(make)
    pv = model.default_parameter_values
    geometry = {"pipe": {z: {"min": 0, "max": model.param.Z}}}
    sim = pybamm.Simulation(
        model,
        parameter_values=pv,
        geometry=geometry,
        submesh_types={"pipe": pybamm.Uniform1DSubMesh},
        var_pts={z: 20},
        spatial_methods={"pipe": pytes.compat.fluid_spatial_method()},
        solver=pybamm.IDAKLUSolver(rtol=1e-9, atol=1e-9),
    )
    solution = sim.solve([0, 600])
    expected = pv["Inlet temperature [K]"] + pv["Number of pipes"] * q * pv[
        "Pipe length [m]"
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
            return param.N_pipes * pybamm.Integral(pybamm.Integral(symbol, y), z)

        geometry = StorageGeometry(y, integrate, lambda s: pybamm.Integral(s, y))
        storage = EnthalpyStorage(param, param.composite, geometry)
        insulation = Stub(
            param,
            lambda p, s: {
                "Phase-change material boundary heat flux [W.m-2]": (
                    pybamm.PrimaryBroadcast(0, "pipe")
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
        "PCM vertical": {y: {"min": model.param.R_f, "max": model.param.H}},
        "pipe": {z: {"min": 0, "max": model.param.Z}},
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
            lambda p, s: {"Twice the power [W]": 2 * s.coupled("Power [W]", "pipe")},
        )

    with pytest.raises(pytes.WiringError, match="provides it on"):
        AlteredSharpFront(alter)


def test_circular_dependency_is_detected():
    def alter(submodels, param):
        submodels["a"] = Stub(param, lambda p, s: {"A [W]": s.coupled("B [W]")}, "a")
        submodels["b"] = Stub(param, lambda p, s: {"B [W]": s.coupled("A [W]")}, "b")

    with pytest.raises(pytes.WiringError, match="Circular dependency"):
        AlteredSharpFront(alter)
