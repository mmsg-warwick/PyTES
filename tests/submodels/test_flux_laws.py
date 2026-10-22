"""Surface flux laws: the flow-dependent heat transfer coefficients (issue #6)."""

import numpy as np
import pybamm
import pytest
from conftest import var_pts

import pytes
from pytes import conformance
from pytes.experiments import Experiment, run_experiment, step
from pytes.submodels import (
    CORRELATIONS,
    FluidState,
    Gnielinski,
    HeatTransferCoefficientOptions,
    NusseltCorrelation,
    PackedBedCorrelation,
    SurfaceFluxLaw,
    TubeCorrelation,
    WakaoKaguei,
    register_correlation,
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


# Registered correlations


@pytest.fixture
def registry(monkeypatch):
    """The registry, restored after the test"""
    for flow, correlations in CORRELATIONS.items():
        monkeypatch.setitem(CORRELATIONS, flow, dict(correlations))
    return CORRELATIONS


def dittus_boelter(Re, Pr):
    return 0.023 * Re**0.8 * Pr**0.4


def test_the_built_in_correlations_are_registered():
    assert CORRELATIONS == {
        "tube": {"Gnielinski": Gnielinski},
        "packed bed": {"Wakao-Kaguei": WakaoKaguei},
    }
    assert issubclass(Gnielinski, TubeCorrelation)
    assert issubclass(WakaoKaguei, PackedBedCorrelation)


def test_option_values_follow_the_registry(registry):
    values = pytes.SharpFrontModel.allowed_options["heat transfer coefficient"]
    assert list(values) == ["constant", "Gnielinski"]
    assert values[0] == "constant" and len(values) == 2
    assert "Gnielinski" in repr(values)
    register_correlation("Dittus-Boelter", dittus_boelter, flow="tube")
    assert list(values) == ["constant", "Gnielinski", "Dittus-Boelter"]
    # Only for its own flow geometry
    with pytest.raises(pytes.OptionError, match="Wakao-Kaguei"):
        pytes.PackedBedModel(options={"heat transfer coefficient": "Dittus-Boelter"})


def test_a_registered_function_runs_and_conserves_energy(registry):
    correlation = register_correlation("Dittus-Boelter", dittus_boelter, flow="tube")
    assert issubclass(correlation, TubeCorrelation)
    model = pytes.SharpFrontModel(
        options={"heat transfer coefficient": "Dittus-Boelter"}
    )
    assert isinstance(model.submodels["coupling"].flux_law, correlation)
    solution = conformance.check_model(model, var_pts=var_pts(model))
    # h = Nu k / d, with Nu from the registered function at the solved Re and Pr
    Re = solution["Surface Reynolds number"].entries
    Pr = solution["Surface Prandtl number"].entries
    pv = model.default_parameter_values
    k, d = pv["Heat transfer fluid conductivity [W.m-1.K-1]"], 2 * pv["Tube radius [m]"]
    np.testing.assert_allclose(
        solution["Heat transfer coefficient [W.m-2.K-1]"].entries,
        dittus_boelter(Re, Pr) * k / d,
        rtol=1e-10,
    )


def test_a_registered_class_runs(registry):
    class Ranz(PackedBedCorrelation):
        def nusselt(self, Re, Pr):
            return 2 + 0.6 * Re**0.5 * Pr ** (1 / 3)

    assert register_correlation("Ranz-Marshall", Ranz, flow="packed bed") is Ranz
    model = pytes.PackedBedModel(options={"heat transfer coefficient": "Ranz-Marshall"})
    assert isinstance(model.submodels["coupling"].flux_law, Ranz)
    conformance.check_model(model, var_pts=var_pts(model))


def test_registration_replaces_only_when_asked(registry):
    register_correlation("Mine", dittus_boelter, flow="tube")
    with pytest.raises(ValueError, match="replace=True"):
        register_correlation("Mine", dittus_boelter, flow="tube")
    replaced = register_correlation("Mine", lambda Re, Pr: 4, flow="tube", replace=True)
    assert registry["tube"]["Mine"] is replaced
    with pytest.raises(ValueError, match="cannot be replaced"):
        register_correlation("Gnielinski", dittus_boelter, flow="tube", replace=True)


@pytest.mark.parametrize(
    "name, nusselt, flow, error, match",
    [
        ("Mine", dittus_boelter, "duct", ValueError, "Unknown flow 'duct'"),
        ("", dittus_boelter, "tube", ValueError, "non-empty string"),
        (3, dittus_boelter, "tube", ValueError, "non-empty string"),
        ("constant", dittus_boelter, "tube", ValueError, "constant coefficient"),
        ("Mine", 3.66, "tube", TypeError, "function nusselt"),
        ("Mine", WakaoKaguei, "tube", TypeError, "must subclass TubeCorrelation"),
    ],
)
def test_invalid_registrations(registry, name, nusselt, flow, error, match):
    with pytest.raises(error, match=match):
        register_correlation(name, nusselt, flow=flow)
    assert registry["tube"] == {"Gnielinski": Gnielinski}


def test_options_for_an_unknown_flow():
    with pytest.raises(ValueError, match="Unknown flow"):
        HeatTransferCoefficientOptions("duct")
