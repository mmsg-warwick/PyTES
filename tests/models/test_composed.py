"""Models composed from submodels by the user (DESIGN D3)."""

import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes import conformance
from pytes.submodels import LedgerWallCoupling, NewtonCooling, SurfaceFluxLaw

T = np.linspace(0, 1800, 7)


def solve(model, mesh_model=None):
    mesh = var_pts(mesh_model or model)
    return pybamm.Simulation(model, var_pts=mesh).solve([0, 1800], t_interp=T)


class CubicFlux(SurfaceFluxLaw):
    """A nonlinear law, ``c (T_f - T_s)**3``, with ``c`` from the default coefficient"""

    def heat_flux(self, fluid, h_f, T_f, T_s):
        return NewtonCooling().coefficient / 25 * (T_f - T_s) ** 3


def with_cubic_flux(base):
    storage = base.submodels["storage"]
    coupling = LedgerWallCoupling(
        base.param,
        base.param.fluid,
        storage.label,
        storage.storage_geometry,
        flux_law=CubicFlux(),
    )
    return pytes.ComposedModel(
        {**base.submodels, "coupling": coupling},
        base.param,
        name="Cubic flux",
        defaults_from=base,
    )


def test_same_submodels_give_the_same_model(model_class):
    base = model_class()
    composed = pytes.ComposedModel(base.submodels, base.param, defaults_from=base)
    assert list(composed.submodels) == list(base.submodels)
    np.testing.assert_array_equal(
        solve(composed, base)["Outlet temperature [K]"].entries,
        solve(base)["Outlet temperature [K]"].entries,
    )


def test_replacing_a_slot_leaves_the_base_model_unchanged():
    base = pytes.SharpFrontModel()
    before = solve(base)["Outlet temperature [K]"].entries
    with_cubic_flux(base)
    np.testing.assert_array_equal(solve(base)["Outlet temperature [K]"].entries, before)


def test_any_flux_law_conserves_energy_exactly():
    # The ledger takes the fluid's heat from the storage's energy balance, so conservation
    # does not depend on the flux law (DESIGN D6)
    base = pytes.SharpFrontModel()
    model = with_cubic_flux(base)
    solution = solve(model, base)
    conformance.check_energy_conservation(solution)
    # The law is used: the outlet temperature differs from Newton's law
    T_out = solution["Outlet temperature [K]"].entries[1:]
    T_default = solve(base)["Outlet temperature [K]"].entries[1:]
    assert np.all(np.abs(T_out - T_default) > 1e-3)


def test_composed_model_meets_the_contract():
    base = pytes.SharpFrontModel()
    model = with_cubic_flux(base)
    conformance.check_required_variables(model)
    conformance.check_submodels(model)
    conformance.check_controls(model)
    conformance.check_initial_state(model, var_pts=var_pts(base))


def test_explicit_defaults_override_defaults_from():
    base = pytes.SharpFrontModel()
    solver = pybamm.IDAKLUSolver(rtol=1e-9, atol=1e-11)
    model = pytes.ComposedModel(
        base.submodels, base.param, defaults_from=base, solver=solver, var_pts={"z": 7}
    )
    assert model.default_solver.rtol == 1e-9
    assert model.default_var_pts == {"z": 7}
    assert model.default_geometry.keys() == base.default_geometry.keys()


def test_from_scratch_needs_geometry():
    base = pytes.SharpFrontModel()
    with pytest.raises(ValueError, match="pass geometry= or defaults_from="):
        pytes.ComposedModel(base.submodels, base.param)
    # With every default given explicitly, it builds and solves
    model = pytes.ComposedModel(
        base.submodels,
        base.param,
        geometry=base.default_geometry,
        submesh_types=base.default_submesh_types,
        spatial_methods=base.default_spatial_methods,
        parameter_values=base.default_parameter_values,
    )
    assert solve(model, base)["Power [W]"].entries[-1] > 0


def test_wiring_is_checked():
    base = pytes.SharpFrontModel()
    submodels = {k: v for k, v in base.submodels.items() if k != "coupling"}
    with pytest.raises(pytes.WiringError, match="which no submodel provides"):
        pytes.ComposedModel(submodels, base.param, defaults_from=base)


def test_unknown_argument():
    base = pytes.SharpFrontModel()
    with pytest.raises(TypeError, match="mesh"):
        pytes.ComposedModel(base.submodels, base.param, mesh={})


def test_print_submodel_info(capsys):
    pytes.MushModel().print_submodel_info()
    out = capsys.readouterr().out
    assert "fins: EnthalpyStorage (Fin storage)" in out
    assert "        Fin enthalpy [J.m-3]" in out
    assert "    assumptions:" in out
