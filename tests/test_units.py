"""Tests for units.py: exact conversion factors (task section 8) and round trips."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from concretecalc import units


def test_exact_definitions():
    assert units.KG_PER_LB == 0.45359237
    assert units.MM_PER_IN == 25.4
    assert units.M_PER_YD == 0.9144
    assert units.MPA_PER_PSI == 0.00689475729
    assert units.KG_M3_PER_PCF == 16.01846337
    assert units.M3_PER_YD3 == 0.764554857984


def test_cubic_yard_is_the_cube_of_a_yard():
    assert units.M3_PER_YD3 == pytest.approx(0.9144**3, rel=1e-15)


def test_lb_per_yd3_factor():
    assert units.KG_M3_PER_LB_YD3 == pytest.approx(0.45359237 / 0.764554857984, rel=1e-15)
    assert units.KG_M3_PER_LB_YD3 == pytest.approx(0.593276, abs=1e-6)


def test_pcf_factor_is_consistent_with_lb_and_ft():
    # 1 pcf = 1 lb / (0.3048 m)^3; the task's 16.01846337 is that value to 10 significant digits.
    assert units.KG_M3_PER_PCF == pytest.approx(0.45359237 / 0.3048**3, rel=1e-9)


@pytest.mark.parametrize(
    "function, value, expected",
    [
        (units.lb_to_kg, 1.0, 0.45359237),
        (units.kg_to_lb, 0.45359237, 1.0),
        (units.in_to_mm, 1.5, 38.1),
        (units.mm_to_in, 25.4, 1.0),
        (units.psi_to_mpa, 3000.0, 20.68427187),
        (units.mpa_to_psi, 0.00689475729, 1.0),
        (units.pcf_to_kg_m3, 105.0, 1681.9386538500),
        (units.kg_m3_to_pcf, 16.01846337, 1.0),
        (units.lb_yd3_to_kg_m3, 580.0, 580.0 * 0.45359237 / 0.764554857984),
        (units.kg_m3_to_lb_yd3, 0.45359237 / 0.764554857984, 1.0),
        (units.yd3_to_m3, 1.0, 0.764554857984),
        (units.m3_to_yd3, 0.764554857984, 1.0),
    ],
)
def test_hand_values(function, value, expected):
    assert function(value) == pytest.approx(expected, rel=1e-12)


PAIRS = [
    (units.lb_to_kg, units.kg_to_lb),
    (units.in_to_mm, units.mm_to_in),
    (units.psi_to_mpa, units.mpa_to_psi),
    (units.pcf_to_kg_m3, units.kg_m3_to_pcf),
    (units.lb_yd3_to_kg_m3, units.kg_m3_to_lb_yd3),
    (units.yd3_to_m3, units.m3_to_yd3),
]


@pytest.mark.parametrize("forward, backward", PAIRS)
@given(value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
def test_round_trips(forward, backward, value):
    assert backward(forward(value)) == pytest.approx(value, rel=1e-12, abs=1e-12)
