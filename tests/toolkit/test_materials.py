"""Tests for the enthalpy-temperature relations of the phase-change materials."""

import numpy as np
import pybamm
import pytest

from pytes.models.finned_pipe import FinnedPipeParameters, get_parameter_values

param = FinnedPipeParameters()
T_m = get_parameter_values()["PCM melting temperature [K]"]


def evaluate(symbol, dT_m=0):
    parameter_values = get_parameter_values()
    parameter_values["PCM melting range [K]"] = dT_m
    return np.asarray(parameter_values.evaluate(symbol)).squeeze()


@pytest.fixture(params=["pcm", "composite"])
def material(request):
    return getattr(param, request.param)


@pytest.mark.parametrize("dT_m", [0, 0.5])
@pytest.mark.parametrize("T", [T_m - 30, T_m - 5, T_m + 5, T_m + 30])
def test_temperature_enthalpy_round_trip(material, T, dT_m):
    # T2H is exact, so with smoothing H2T only inverts it up to dT_m^2 / 4|T - T_m|
    tol = dT_m**2 / (2 * abs(T - T_m)) + 1e-9
    assert evaluate(material.H2T(material.T2H(T)), dT_m) == pytest.approx(T, abs=tol)


def test_round_trip_close_to_melting_temperature(material):
    for T in [T_m - 1e-3, T_m + 1e-3]:
        assert evaluate(material.H2T(material.T2H(T))) == pytest.approx(T)


def test_melting_temperature_is_solid(material):
    assert evaluate(material.T2H(T_m)) == pytest.approx(evaluate(material.H_solidus))
    assert evaluate(material.liquid_fraction(material.T2H(T_m))) == pytest.approx(
        0, abs=1e-9
    )


def test_latent_band(material):
    H_s, H_l = evaluate(material.H_solidus), evaluate(material.H_liquidus)
    H_mid = (H_s + H_l) / 2
    # Temperature stays at T_m while melting
    assert evaluate(material.H2T(H_mid)) == pytest.approx(T_m)
    assert evaluate(material.liquid_fraction(H_mid)) == pytest.approx(0.5)
    assert evaluate(material.liquid_fraction(H_s - 1e6)) == pytest.approx(0, abs=1e-9)
    assert evaluate(material.liquid_fraction(H_l + 1e6)) == pytest.approx(1)
    # Conductivity is continuous at the solidus and the liquidus
    k_s, k_l = evaluate(material.k_s), evaluate(material.k_l)
    for H, k in [(H_s, k_s), (H_l, k_l)]:
        assert evaluate(material.k(H - 1)) == pytest.approx(k, rel=1e-6)
        assert evaluate(material.k(H + 1)) == pytest.approx(k, rel=1e-6)
    assert evaluate(material.k(H_mid)) == pytest.approx((k_s + k_l) / 2)


def enthalpy_grid(material, dT_m, n=4001):
    """Enthalpies spanning the latent band plus 10 dT_m of sensible heat each side"""
    H_s, H_l = evaluate(material.H_solidus), evaluate(material.H_liquidus)
    margin = 10 * dT_m * evaluate(material.rho_c_p_s)
    return pybamm.Vector(np.linspace(H_s - margin, H_l + margin, n))


def test_smoothed_relations_are_monotonic_and_bounded(material):
    dT_m = 0.5
    H = enthalpy_grid(material, dT_m)
    T = evaluate(material.H2T(H), dT_m)
    phi = evaluate(material.liquid_fraction(H), dT_m)
    k = evaluate(material.k(H), dT_m)
    assert np.all(np.diff(T) > 0)
    assert np.all(np.diff(phi) >= 0)
    # Overshoot outside [0, 1] of order (rho_c_p * dT_m / rho_L)^2
    eps = (evaluate(material.rho_c_p_l) * dT_m / evaluate(material.rho_L)) ** 2
    assert np.all(phi >= -eps) and np.all(phi <= 1 + eps)
    k_s, k_l = evaluate(material.k_s), evaluate(material.k_l)
    dk = abs(k_l - k_s)
    assert np.all(k >= min(k_s, k_l) - eps * dk)
    assert np.all(k <= max(k_s, k_l) + eps * dk)


@pytest.mark.parametrize("dT_m, smooth", [(0, False), (0.5, True)])
def test_smoothing_rounds_the_corners(material, dT_m, smooth):
    # The slope dT/dH drops from 1 / rho_c_p_s to 0 at the solidus: sharply (in one
    # grid step) without smoothing, gradually over many steps with it
    H = enthalpy_grid(material, 0.5)
    T = evaluate(material.H2T(H), dT_m)
    slope = np.diff(T) / np.diff(H.entries.squeeze())
    largest_jump = np.max(np.abs(np.diff(slope))) * evaluate(material.rho_c_p_s)
    assert (largest_jump < 0.1) == smooth


def test_composite_includes_fins():
    # The metal raises the conductivity and lowers the latent heat per volume
    assert evaluate(param.composite.k_s) > 10 * evaluate(param.pcm.k_s)
    assert evaluate(param.composite.rho_L) < evaluate(param.pcm.rho_L)
