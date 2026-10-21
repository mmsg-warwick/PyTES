"""Surface flux laws: the flow-dependent heat transfer coefficients (issue #6)."""

import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes.experiments import Experiment, run_experiment, step
from pytes.submodels import (
    FluidState,
    Gnielinski,
    NusseltCorrelation,
    SurfaceFluxLaw,
    WakaoKaguei,
)


def gnielinski_turbulent(Re, Pr):
    f = (0.79 * np.log(Re) - 1.64) ** -2
    return (
        (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
    )


@pytest.mark.parametrize(
    "Re, expected",
    [
        (500, 3.66),
        (2300, 3.66),
        (6150, 0.5 * 3.66 + 0.5 * gnielinski_turbulent(1e4, 7)),
        (1e4, gnielinski_turbulent(1e4, 7)),
        (1e5, gnielinski_turbulent(1e5, 7)),
    ],
)
def test_gnielinski_nusselt(Re, expected):
    Nu = Gnielinski(1).nusselt(pybamm.Scalar(Re), pybamm.Scalar(7)).evaluate()
    np.testing.assert_allclose(Nu, expected, rtol=1e-12)


def test_wakao_kaguei_nusselt():
    Nu = WakaoKaguei(1, 1).nusselt(pybamm.Scalar(100), pybamm.Scalar(7)).evaluate()
    np.testing.assert_allclose(Nu, 2 + 1.1 * 100**0.6 * 7 ** (1 / 3), rtol=1e-12)


def test_nusselt_must_be_implemented():
    with pytest.raises(NotImplementedError):
        NusseltCorrelation(1, 1).nusselt(1, 1)


def test_a_law_adds_no_variables_by_default():
    assert SurfaceFluxLaw().variables(None, None) == {}


def coefficient(law, mass_flow_rate):
    """The law's coefficient [W.m-2.K-1] for water in the default finned-tube battery"""
    parameter_values = pytes.SharpFrontModel().default_parameter_values
    fluid = pytes.fluids.ConstantPropertyLiquid()
    state = FluidState(h=pybamm.Scalar(0), T=None, mass_flow_rate=mass_flow_rate)
    symbol = law.heat_transfer_coefficient(fluid, state)
    return parameter_values.process_symbol(symbol).evaluate()


def test_gnielinski_coefficient_from_the_flow():
    # Re = 4 mdot / (pi d mu) per tube and h = Nu k / d, with the properties of water
    pv = pytes.SharpFrontModel().default_parameter_values
    R, mu = pv["Tube radius [m]"], pv["Heat transfer fluid viscosity [Pa.s]"]
    k = pv["Heat transfer fluid conductivity [W.m-1.K-1]"]
    Pr = mu * pv["Heat transfer fluid specific heat capacity [J.kg-1.K-1]"] / k
    law = Gnielinski(pybamm.Parameter("Tube radius [m]"), n_tubes=2)
    mdot = 4e-1
    Re = 4 * mdot / 2 / (np.pi * 2 * R * mu)
    assert Re > 1e4
    expected = gnielinski_turbulent(Re, Pr) * k / (2 * R)
    np.testing.assert_allclose(coefficient(law, mdot), expected, rtol=1e-12)
    # The flow's direction does not matter
    np.testing.assert_allclose(coefficient(law, -mdot), expected, rtol=1e-12)


@pytest.mark.parametrize(
    "cls, option",
    [
        (pytes.SharpFrontModel, "Gnielinski"),
        (pytes.MushModel, "Gnielinski"),
        (pytes.PackedBedModel, "Wakao-Kaguei"),
    ],
)
def test_the_option_chooses_the_flux_law(cls, option):
    law = cls(options={"heat transfer coefficient": option}).submodels["coupling"]
    assert type(law.flux_law).__name__ == option.replace("-", "")
    assert "Heat transfer coefficient [W.m-2.K-1]" not in law.parameters
    law = cls().submodels["coupling"]
    assert "Heat transfer coefficient [W.m-2.K-1]" in law.parameters


@pytest.mark.parametrize(
    "cls, option",
    [(pytes.SharpFrontModel, "Gnielinski"), (pytes.PackedBedModel, "Wakao-Kaguei")],
)
def test_the_coefficient_rises_with_the_flow(cls, option):
    model = cls(options={"heat transfer coefficient": option})
    coefficients = []
    for factor in (1, 4):
        parameter_values = model.default_parameter_values
        parameter_values["Mass flow rate [kg.s-1]"] *= factor
        solution = pybamm.Simulation(
            model, parameter_values=parameter_values, var_pts=var_pts(model)
        ).solve([0, 60])
        coefficients.append(
            solution["Heat transfer coefficient [W.m-2.K-1]"].entries.ravel()[-1]
        )
    assert coefficients[1] > 1.5 * coefficients[0]


def test_constant_power_adjusts_the_flow_through_the_coefficient():
    # With a correlation, the coefficient follows the flow rate an experiment adjusts
    model = pytes.SharpFrontModel(options={"heat transfer coefficient": "Gnielinski"})
    experiment = Experiment(
        [step.ConstantPower(4000, inlet_temperature=283.15, duration=300)]
    )
    solution = run_experiment(model, experiment, var_pts=var_pts(model))
    mdot = solution["Mass flow rate [kg.s-1]"].entries
    h = solution["Heat transfer coefficient [W.m-2.K-1]"].entries
    np.testing.assert_allclose(solution["Power [W]"].entries, 4000, rtol=1e-4)
    assert np.ptp(mdot) > 0
    assert np.ptp(h) > 0
