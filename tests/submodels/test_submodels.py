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
from pytes.submodels.storage import INITIAL_LIQUID_FRACTION


class Composition(pytes.BaseModel):
    """A model made of given submodels, for testing them in isolation"""

    def __init__(self, make_submodels, geometry_variables):
        self._make_submodels = make_submodels
        self._geometry_variables = geometry_variables
        super().__init__("Composition", operating_mode=None)

    def get_parameters(self):
        return FinnedPipeParameters()

    def set_submodels(self):
        self.submodels.update(self._make_submodels(self.param))

    @property
    def default_parameter_values(self):
        return pytes.models.finned_pipe.get_parameter_values()


class Stub(BaseSubModel):
    """Provides fixed variables"""

    def __init__(self, param, values, requires=(), name="stub"):
        super().__init__(param, name)
        self.values = values
        self.provides = tuple(values)
        self.requires = tuple(requires)

    def get_coupled_variables(self, variables):
        variables.update(self.values(self.param) if callable(self.values) else {})
        return variables


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


def stub(names, values):
    class _Stub(BaseSubModel):
        provides = tuple(names)

        def get_coupled_variables(self, variables):
            variables.update(values(self.param))
            return variables

    return _Stub


def test_fluid_steady_state_with_uniform_heat_gain():
    # With a uniform heat gain q' per unit length, the steady outlet temperature is
    # T_in + n q' Z / (mdot c_p), exactly (the upwind scheme telescopes), provided the
    # inflow is exactly at T_in (pytes.compat.upwind_inlet_value)
    q = 50.0  # [W.m-1]

    def make(param):
        Source = stub(
            [HEAT_GAIN, INITIAL_TEMPERATURE],
            lambda p: {
                HEAT_GAIN: pybamm.PrimaryBroadcast(q, "pipe"),
                INITIAL_TEMPERATURE: p.T_in,
            },
        )
        return {"fluid": fluid_submodel(param), "source": Source(param)}

    model = Composition(make, [z])
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

        class Insulation(BaseSubModel):
            provides = (
                INITIAL_TEMPERATURE,
                INITIAL_LIQUID_FRACTION,
                "Outlet temperature [K]",
            )

            def get_coupled_variables(self, variables):
                variables.update(
                    {
                        INITIAL_TEMPERATURE: self.param.T_m,
                        INITIAL_LIQUID_FRACTION: pybamm.Scalar(0.4),
                        # Read by the base model's events (none in operating mode None)
                        "Outlet temperature [K]": self.param.T_m,
                    }
                )
                return variables

            def set_boundary_conditions(self, variables):
                self.boundary_conditions[storage.T] = {
                    "left": (pybamm.Scalar(0), "Neumann")
                }

        return {"storage": storage, "insulation": Insulation(param)}

    model = Composition(make, [y, z])
    storage = model.submodels["storage"]
    assert storage.states == [storage.H]
    geometry = {
        "PCM vertical": {y: {"min": model.param.R_f, "max": model.param.H}},
        "pipe": {z: {"min": 0, "max": model.param.Z}},
    }
    sim = pybamm.Simulation(
        model,
        geometry=geometry,
        submesh_types={d: pybamm.Uniform1DSubMesh for d in geometry},
        var_pts={y: 5, z: 3},
        spatial_methods={d: pybamm.FiniteVolume() for d in geometry},
    )
    solution = sim.solve([0, 600])
    E = solution["Phase-change material thermal energy [J]"].entries
    np.testing.assert_allclose(E, E[0], rtol=1e-12)
    # Constant in time; 0.4 up to the smoothing of the melting point, which shifts the
    # liquid fraction by about width**2 / (4 phi) with width = rho_c_p dT_m / rho_L
    phi = solution["Average liquid fraction"].entries
    np.testing.assert_allclose(phi, phi[0], rtol=1e-9)
    assert phi[0] == pytest.approx(0.4, abs=1e-4)


class BrokenSharpFront(pytes.SharpFrontModel):
    """Sharp-front model with its submodels altered by ``alter``"""

    def __init__(self, alter):
        self._alter = alter
        super().__init__(operating_mode=None)

    def set_submodels(self):
        super().set_submodels()
        self._alter(self.submodels, self.param)


def test_missing_provider_is_detected():
    def alter(submodels, param):
        del submodels["coupling"]

    with pytest.raises(pytes.WiringError, match="which no submodel provides"):
        BrokenSharpFront(alter)


def test_duplicate_provider_is_detected():
    def alter(submodels, param):
        Extra = stub([HEAT_GAIN], lambda p: {HEAT_GAIN: pybamm.Scalar(0)})
        submodels["extra"] = Extra(param)

    with pytest.raises(pytes.WiringError, match="provided by both"):
        BrokenSharpFront(alter)


def test_undeclared_read_is_detected():
    class Sneaky(BaseSubModel):
        provides = ("Sneaky variable",)

        def get_coupled_variables(self, variables):
            variables["Sneaky variable"] = 2 * variables["Power [W]"]
            return variables

    def alter(submodels, param):
        submodels["sneaky"] = Sneaky(param)

    with pytest.raises(pytes.WiringError, match="without declaring it"):
        BrokenSharpFront(alter)


def test_declared_but_not_provided_is_detected():
    class Liar(BaseSubModel):
        provides = ("Promised variable",)

    def alter(submodels, param):
        submodels["liar"] = Liar(param)

    with pytest.raises(pytes.WiringError, match="does not provide"):
        BrokenSharpFront(alter)
