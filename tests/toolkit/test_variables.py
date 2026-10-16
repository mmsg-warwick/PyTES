"""Variable conventions: SI units and their generated twins (DESIGN D12)."""

import pybamm
import pytest

import pytes
from pytes import conformance
from pytes.variables import add_unit_twins, is_temperature_difference, unit_twins

DIFFERENCE = "Inlet-outlet temperature difference [K]"


def test_is_temperature_difference():
    assert is_temperature_difference(DIFFERENCE)
    assert is_temperature_difference("Approach temperature difference [K]")
    assert not is_temperature_difference("Outlet temperature [K]")


@pytest.mark.parametrize(
    "name, twins",
    [
        ("Outlet temperature [K]", ["Outlet temperature [degC]"]),
        ("Power [W]", ["Power [kW]"]),
        ("Discharged energy [J]", ["Discharged energy [kWh]"]),
        ("Time [s]", ["Time [min]", "Time [h]"]),
        (DIFFERENCE, []),
        ("Power per unit area [W.m-2]", []),
    ],
)
def test_twin_names(name, twins):
    assert list(unit_twins(name)) == twins


def test_twins_are_converted():
    variables = add_unit_twins(
        {
            "Outlet temperature [K]": pybamm.Scalar(300),
            "Power [W]": pybamm.Scalar(2500),
            "Discharged energy [J]": pybamm.Scalar(7.2e6),
            DIFFERENCE: pybamm.Scalar(5),
            "Time [s]": pybamm.Scalar(5400),
        }
    )
    assert variables["Outlet temperature [degC]"].evaluate() == pytest.approx(26.85)
    assert variables["Power [kW]"].evaluate() == pytest.approx(2.5)
    assert variables["Discharged energy [kWh]"].evaluate() == pytest.approx(2)
    assert "Inlet-outlet temperature difference [degC]" not in variables
    assert variables["Time [min]"].evaluate() == pytest.approx(90)
    assert variables["Time [h]"].evaluate() == pytest.approx(1.5)


def test_twins_are_never_written_by_hand():
    with pytest.raises(ValueError, match="must not be written by hand"):
        add_unit_twins({"Power [W]": pybamm.Scalar(1), "Power [kW]": pybamm.Scalar(0)})


def test_every_model_gets_its_twins():
    variables = pytes.PackedBedModel().variables
    for name in (
        "Power [kW]",
        "Total thermal energy [kWh]",
        "Outlet temperature [degC]",
    ):
        assert name in variables


def test_check_required_variables_handles_twins():
    model = pytes.SharpFrontModel()
    T_in = model.variables["Inlet temperature [K]"]
    T_out = model.variables["Outlet temperature [K]"]
    # A difference without a twin passes
    model.variables[DIFFERENCE] = T_in - T_out
    conformance.check_required_variables(model)
    # A difference with a twin, or a temperature without one, fails
    model.variables["Inlet-outlet temperature difference [degC]"] = T_in - T_out
    with pytest.raises(AssertionError, match="differences with a \\[degC\\] twin"):
        conformance.check_required_variables(model)
    del model.variables["Inlet-outlet temperature difference [degC]"]
    model.variables["Wall temperature [K]"] = T_in
    with pytest.raises(AssertionError, match="without a unit twin"):
        conformance.check_required_variables(model)
