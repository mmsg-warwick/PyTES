"""The fluid-property object (DESIGN D8)."""

import pybamm
import pytest

from pytes.fluids import ConstantPropertyLiquid

VALUES = pybamm.ParameterValues(
    {
        "Heat transfer fluid density [kg.m-3]": 1000,
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]": 4186,
        "Heat transfer fluid conductivity [W.m-1.K-1]": 0.6,
        "Heat transfer fluid viscosity [Pa.s]": 1e-3,
    }
)


def evaluate(symbol):
    return VALUES.evaluate(symbol)


def test_enthalpy_and_temperature_are_inverse():
    fluid = ConstantPropertyLiquid(T_ref=283.15)
    assert evaluate(fluid.h(283.15)) == 0
    assert evaluate(fluid.T(fluid.h(343.15))) == pytest.approx(343.15)


def test_properties_at_any_state():
    fluid = ConstantPropertyLiquid()
    h = pybamm.Scalar(2e5)
    assert evaluate(fluid.c_p(h)) == 4186
    assert evaluate(fluid.rho(h)) == 1000
    assert evaluate(fluid.k(h)) == 0.6
    assert evaluate(fluid.mu(h)) == 1e-3
    # The pressure is ignored by a liquid
    assert evaluate(fluid.c_p(h, p=2e5)) == evaluate(fluid.c_p(h))
