"""The limited, second-order upwind scheme for the fluid (issue #7, F-052)."""

import numpy as np
import pybamm
import pytest
from conftest import MODEL_CLASSES, var_pts
from test_submodels import Composition, Stub, fluid_submodel, z

from pytes import conformance
from pytes.compat import LimitedFiniteVolume, fluid_spatial_method
from pytes.submodels.fluid import HEAT_GAIN, INITIAL_TEMPERATURE

UNIFORM = pybamm.MeshGenerator(pybamm.Uniform1DSubMesh)
#: Cells shrinking towards the outlet, by a factor of about 6 from end to end
STRETCHED = pybamm.MeshGenerator(
    pybamm.Exponential1DSubMesh, {"side": "right", "stretch": 2}
)


def fluid_only(heat_gain, initial_temperature):
    """The fluid alone, with a given heat gain per unit length and initial temperature"""

    def make(param):
        source = Stub(
            param,
            lambda p, s: {
                HEAT_GAIN: pybamm.PrimaryBroadcast(heat_gain, "flow path"),
                INITIAL_TEMPERATURE: initial_temperature(p),
            },
        )
        return {"fluid": fluid_submodel(param), "source": source}

    return Composition(make)


def solve_fluid(model, spatial_method, submesh, n, t):
    sim = pybamm.Simulation(
        model,
        geometry={"flow path": {z: {"min": 0, "max": model.param.Z}}},
        submesh_types={"flow path": submesh},
        var_pts={z: n},
        spatial_methods={"flow path": spatial_method},
        solver=pybamm.IDAKLUSolver(rtol=1e-9, atol=1e-9),
    )
    solution = sim.solve([0, t[-1]], t_interp=t)
    return sim, solution


@pytest.mark.parametrize("submesh", [UNIFORM, STRETCHED], ids=["uniform", "stretched"])
def test_steady_linear_profile_is_exact(submesh):
    # A uniform heat gain q' gives a linear steady enthalpy, which the scheme reconstructs
    # exactly on any mesh: the cells hold the exact value at their centres (first-order
    # upwinding holds the value at their downstream faces), apart from the last cell,
    # which advects its value out (the outflow is first order), and the outlet is exact
    q = 50.0  # [W.m-1]
    model = fluid_only(q, lambda p: p.T_in)
    sim, solution = solve_fluid(model, fluid_spatial_method(), submesh, 20, [0, 1200])
    pv = model.default_parameter_values
    c_p = pv["Heat transfer fluid specific heat capacity [J.kg-1.K-1]"]
    mdot = pv["Mass flow rate [kg.s-1]"] / pv["Number of tubes"]
    T_in = pv["Inlet temperature [K]"]
    centres = sim.mesh["flow path"].nodes
    T = solution["Heat transfer fluid temperature [K]"].entries[:, -1]
    np.testing.assert_allclose(
        T[:-1], T_in + q * centres[:-1] / (mdot * c_p), atol=1e-6
    )
    assert solution["Outlet temperature [K]"].entries[-1] == pytest.approx(
        T_in + q * pv["Tube length [m]"] / (mdot * c_p), abs=1e-6
    )


def advect_a_step(spatial_method, submesh, n=40):
    """
    The fluid temperature after a step in the inlet temperature has travelled half the
    flow path, scaled from 0 (initial) to 1 (inlet), and the cell centres over the length
    """
    model = fluid_only(0, lambda p: p.T_in - 20)
    pv = model.default_parameter_values
    area, Z = pv["Tube radius [m]"] ** 2 * np.pi, pv["Tube length [m]"]
    rho = pv["Heat transfer fluid density [kg.m-3]"]
    mdot = pv["Mass flow rate [kg.s-1]"] / pv["Number of tubes"]
    t_half = 0.5 * Z * rho * area / mdot
    sim, solution = solve_fluid(
        model, spatial_method, submesh, n, np.linspace(0, t_half, 41)
    )
    T = solution["Heat transfer fluid temperature [K]"].entries
    theta = (T - (pv["Inlet temperature [K]"] - 20)) / 20
    return theta, sim.mesh["flow path"].nodes / Z


@pytest.mark.parametrize("submesh", [UNIFORM, STRETCHED], ids=["uniform", "stretched"])
def test_a_step_stays_bounded_and_sharper(submesh):
    first, centres = advect_a_step(fluid_spatial_method("first order"), submesh)
    limited, _ = advect_a_step(fluid_spatial_method(), submesh)
    # No new extremum: the temperature stays between the initial and inlet ones
    assert limited.min() > -1e-6 and limited.max() < 1 + 1e-6
    # The front is at mid-length: the limited scheme is closer to the exact step
    exact = (centres < 0.5).astype(float)
    assert np.mean(np.abs(limited[:, -1] - exact)) < 0.7 * np.mean(
        np.abs(first[:, -1] - exact)
    )


@pytest.mark.parametrize("model_class", MODEL_CLASSES, ids=lambda cls: cls.__name__)
def test_energy_is_conserved_on_a_stretched_mesh(model_class):
    model = model_class()
    sim = pybamm.Simulation(
        model,
        submesh_types={**model.default_submesh_types, "flow path": STRETCHED},
        spatial_methods={
            **model.default_spatial_methods,
            "flow path": fluid_spatial_method(),
        },
        var_pts=var_pts(model),
    )
    conformance.check_energy_conservation(sim.solve([0, 1800]))


def test_downwinding_is_not_implemented():
    model = pybamm.BaseModel()
    c = pybamm.Variable("c", domain="flow path")
    model.rhs = {c: -pybamm.div(pybamm.downwind(c))}
    model.boundary_conditions = {c: {"right": (pybamm.Scalar(0), "Dirichlet")}}
    model.initial_conditions = {c: pybamm.Scalar(1)}
    geometry = {"flow path": {z: {"min": 0, "max": 1}}}
    mesh = pybamm.Mesh(geometry, {"flow path": UNIFORM}, {z: 5})
    disc = pybamm.Discretisation(mesh, {"flow path": LimitedFiniteVolume()})
    with pytest.raises(NotImplementedError, match="only implements upwinding"):
        disc.process_model(model)


def test_unknown_scheme():
    with pytest.raises(ValueError, match="Scheme 'third order' not recognised"):
        fluid_spatial_method("third order")


def test_models_use_the_second_order_scheme_by_default():
    for model_class in MODEL_CLASSES:
        method = model_class().default_spatial_methods["flow path"]
        assert isinstance(method, LimitedFiniteVolume)
