"""Analytical benchmarks for the packed-bed family (DESIGN D1, §6; Stage B)."""

import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes import validation
from pytes.materials import SensibleMaterial
from pytes.submodels import (
    BaseSubModel,
    DeviceEnergy,
    EnthalpyStorage,
    LedgerWallCoupling,
    LumpedStorage,
)
from pytes.submodels.storage import INITIAL_TEMPERATURE


def test_schumann_solution_satisfies_its_equations():
    d = 1e-5
    for xi, eta in [(0.5, 0.3), (5, 4), (8, 12)]:
        f, s = validation.schumann(xi, eta)
        dfdxi = (
            validation.schumann(xi + d, eta)[0] - validation.schumann(xi - d, eta)[0]
        )
        dsdeta = (
            validation.schumann(xi, eta + d)[1] - validation.schumann(xi, eta - d)[1]
        )
        assert dfdxi / (2 * d) == pytest.approx(s - f, abs=1e-9)
        assert dsdeta / (2 * d) == pytest.approx(f - s, abs=1e-9)
    assert validation.schumann(0, 2)[0] == 1
    assert validation.schumann(3, 0) == (0, 0)


def sensible_bed(storage_element="resolved"):
    """
    The packed bed with capsules of a sensible material, conductive enough to be lumped
    (Biot number 0.008), as in Schumann's model. A lumped capsule (issue #5) is Schumann's
    model itself.
    """
    base = pytes.PackedBedModel(options={"storage element": storage_element})
    param = base.param
    geometry = base.submodels["storage"].storage_geometry
    fluid = base.submodels["fluid"]
    storage_class = LumpedStorage if storage_element == "lumped" else EnthalpyStorage
    storage = storage_class(
        param, SensibleMaterial("Capsule"), geometry, label="Capsule"
    )
    model = pytes.ComposedModel(
        {
            "fluid": fluid,
            "storage": storage,
            "coupling": LedgerWallCoupling(param, param.fluid, "Capsule", geometry),
            "device energy": DeviceEnergy(param, fluid, [storage]),
        },
        param,
        name="Sensible packed bed",
        defaults_from=base,
    )
    parameter_values = base.default_parameter_values
    parameter_values.update(
        {
            "Capsule conductivity [W.m-1.K-1]": 1e3,
            "Capsule density [kg.m-3]": 1000,
            "Capsule specific heat capacity [J.kg-1.K-1]": 2000,
            "Heat transfer coefficient [W.m-2.K-1]": 300,
        },
        check_already_exists=False,
    )
    return base, model, parameter_values


def schumann_outlet(parameter_values, t):
    """Schumann's outlet temperature, scaled, at times ``t`` [s]"""
    pv = parameter_values
    h = pv["Heat transfer coefficient [W.m-2.K-1]"]
    R, eps = pv["Capsule radius [m]"], pv["Bed porosity"]
    Z, A = pv["Bed length [m]"], pv["Bed cross-sectional area [m2]"]
    rho_f = pv["Heat transfer fluid density [kg.m-3]"]
    c_f = pv["Heat transfer fluid specific heat capacity [J.kg-1.K-1]"]
    rho_c_s = (
        pv["Capsule density [kg.m-3]"]
        * pv["Capsule specific heat capacity [J.kg-1.K-1]"]
    )
    a = 3 * (1 - eps) / R
    u = pv["Mass flow rate [kg.s-1]"] / (rho_f * eps * A)
    xi = h * a * Z / (eps * rho_f * c_f * u)
    rate = h * a / ((1 - eps) * rho_c_s)
    return np.array([validation.schumann(xi, rate * (ti - Z / u))[0] for ti in t])


@pytest.fixture(scope="module", params=["resolved", "lumped"])
def schumann_errors(request):
    """Largest error in the scaled outlet temperature, by number of cells along the bed"""
    base, model, parameter_values = sensible_bed(request.param)
    T_0 = parameter_values["Initial temperature [K]"]
    dT = parameter_values["Inlet temperature [K]"] - T_0
    t = np.linspace(0, 3000, 151)
    exact = schumann_outlet(parameter_values, t)
    errors = {}
    for n_z in (200, 400):
        solution = pybamm.Simulation(
            model,
            parameter_values=parameter_values,
            var_pts=var_pts(base, {"r": 5, "z": n_z}),
            solver=pybamm.IDAKLUSolver(rtol=1e-8, atol=1e-10),
        ).solve([0, t[-1]], t_interp=t)
        theta = (solution["Outlet temperature [K]"].entries - T_0) / dT
        errors[n_z] = np.max(np.abs(theta - exact))
    return errors


def test_sensible_bed_matches_schumann(schumann_errors):
    # Within 2 % of the temperature step on 400 cells
    assert schumann_errors[400] < 0.02


def test_sensible_bed_converges_to_schumann_at_first_order(schumann_errors):
    # First-order upwinding: the error halves with the cell size, so what is left is
    # discretisation error, not a modelling difference
    assert schumann_errors[200] / schumann_errors[400] == pytest.approx(2, rel=0.2)


class SurfaceAt(BaseSubModel):
    """Holds the PCM surface at a temperature, and sets the initial temperature"""

    def __init__(self, param, T_surface):
        self.T_surface = T_surface
        super().__init__(param, "Surface")

    def build(self):
        self.variables = {
            "Phase-change material boundary temperature [K]": pybamm.PrimaryBroadcast(
                self.T_surface, "flow path"
            ),
            INITIAL_TEMPERATURE: self.param.T_init,
        }


def test_capsule_melts_as_the_spherical_stefan_problem():
    # One capsule, solid at its melting temperature, with its surface held 1 K above it
    # (Stefan number 0.011), against the quasi-steady solution (exact as the Stefan
    # number tends to 0)
    base = pytes.PackedBedModel()
    param = base.param
    geometry = base.submodels["storage"].storage_geometry
    storage = EnthalpyStorage(param, param.pcm, geometry, inner_condition="temperature")
    dT = 1
    model = pytes.ComposedModel(
        {"storage": storage, "surface": SurfaceAt(param, param.T_m + dT)},
        param,
        name="Melting capsule",
        defaults_from=base,
    )
    pv = base.default_parameter_values
    pv["PCM smoothing width [K]"] = 0
    pv["Initial temperature [K]"] = pv["PCM melting temperature [K]"]
    R = pv["Capsule radius [m]"]
    tau = (
        pv["PCM solid phase density [kg.m-3]"]
        * pv["PCM latent heat [J.kg-1]"]
        * R**2
        / (6 * pv["PCM liquid phase conductivity [W.m-1.K-1]"] * dT)
    )
    t = np.linspace(0, 1.05 * tau, 2001)
    solution = pybamm.Simulation(
        model,
        parameter_values=pv,
        var_pts={base.r: 160, base.z: 1},
        solver=pybamm.IDAKLUSolver(rtol=1e-8, atol=1e-10),
    ).solve([0, t[-1]], t_interp=t)
    # From half melted: earlier, the melting front crosses the large outer cells of the
    # sphere one at a time, and the melted fraction rises in steps (enthalpy method)
    melted = np.array([0.5, 0.75, 0.9, 0.99])
    t_model = np.interp(melted, solution["Average liquid fraction"].entries, t)
    np.testing.assert_allclose(
        t_model, tau * validation.sphere_melting_time(melted), rtol=0.02
    )
