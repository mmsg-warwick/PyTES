"""Variable conventions: Celsius twins and temperature differences (DESIGN D12)."""

import pybamm
import pytest

import pytes
from pytes import conformance
from pytes.variables import (
    add_temperature_difference_variables,
    add_temperature_variables,
    is_temperature_difference,
)

DIFFERENCE = "Inlet-outlet temperature difference [K]"


def test_is_temperature_difference():
    assert is_temperature_difference(DIFFERENCE)
    assert is_temperature_difference("Approach temperature difference [K]")
    assert not is_temperature_difference("Outlet temperature [K]")


def test_temperatures_get_a_twin_and_differences_do_not():
    T, dT = pybamm.Scalar(300), pybamm.Scalar(5)
    variables = add_temperature_variables({}, {"Outlet temperature [K]": T})
    assert set(variables) == {"Outlet temperature [K]", "Outlet temperature [degC]"}
    variables = add_temperature_difference_variables({}, {DIFFERENCE: dT})
    assert set(variables) == {DIFFERENCE}


@pytest.mark.parametrize(
    "add, name, match",
    [
        (add_temperature_variables, DIFFERENCE, "has no \\[degC\\] twin"),
        (add_temperature_variables, "Outlet temperature [degC]", "must end in"),
        (
            add_temperature_difference_variables,
            "Outlet temperature [K]",
            "must contain",
        ),
        (
            add_temperature_difference_variables,
            "Inlet-outlet temperature difference [degC]",
            "must contain",
        ),
    ],
)
def test_helpers_reject_the_wrong_names(add, name, match):
    with pytest.raises(ValueError, match=match):
        add({}, {name: pybamm.Scalar(1)})


def test_check_required_variables_handles_differences():
    model = pytes.SharpFrontModel()
    T_in = model.variables["Inlet temperature [K]"]
    T_out = model.variables["Outlet temperature [K]"]
    model.variables[DIFFERENCE] = T_in - T_out
    conformance.check_required_variables(model)
    # A difference with a twin, or a temperature without one, fails
    model.variables["Inlet-outlet temperature difference [degC]"] = T_in - T_out
    with pytest.raises(AssertionError, match="differences with a \\[degC\\] twin"):
        conformance.check_required_variables(model)
    del model.variables["Inlet-outlet temperature difference [degC]"]
    model.variables["Wall temperature [K]"] = T_in
    with pytest.raises(AssertionError, match="without a \\[degC\\] twin"):
        conformance.check_required_variables(model)
