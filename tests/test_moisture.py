"""Course exercise and physical mass-balance properties (PLAN M06)."""
import pytest
from hypothesis import given, strategies as st

from concretecalc.moisture import (aggregate_moisture, effective_water,
    field_weights_course, field_weights_strict, oven_dry_mass_kg)
from concretecalc.units import lb_yd3_to_kg_m3, kg_m3_to_lb_yd3


def test_course_exercise():
    result = field_weights_course(320, 1940, 1110, 2, 1, 6, 1.5)
    assert result.coarse_wet_kg == pytest.approx(1978.8, abs=1e-9)
    assert result.fine_wet_kg == pytest.approx(1176.6, abs=1e-9)
    assert result.water_adjusted_kg == pytest.approx(250.65, abs=1e-9)
    si = field_weights_course(*[lb_yd3_to_kg_m3(x) for x in (320, 1940, 1110)], 2, 1, 6, 1.5)
    assert kg_m3_to_lb_yd3(si.water_adjusted_kg) == pytest.approx(250.65, abs=1e-9)


def test_strict_exercise():
    result = field_weights_strict(320, 1940, 1110, 2, 1, 6, 1.5)
    assert result.coarse_wet_kg == pytest.approx(1940 * 1.02 / 1.01, abs=1e-9)
    assert result.fine_wet_kg == pytest.approx(1110 * 1.06 / 1.015, abs=1e-9)
    assert result.water_adjusted_kg == pytest.approx(320 - 1940 / 101 - 1110 * 4.5 / 101.5, abs=1e-9)


def test_ssd_overrides_moisture_and_negative_free_water():
    ssd = aggregate_moisture('CA', 1010, 'ssd', 1, 2)
    assert ssd.oven_dry_kg == pytest.approx(1000, abs=1e-12)
    assert ssd.effective_mc_pct == 1
    assert ssd.free_water_kg == 0
    assert ssd.flags[0].code == 'SSD_MC_MISMATCH'
    dry = aggregate_moisture('FA', 1000, 'oven_dry', 2, 0.5)
    assert dry.free_water_kg == -15
    assert dry.flags[0].code == 'NEGATIVE_FREE_WATER'


@given(st.floats(10, 2000), st.floats(0, 20), st.floats(0, 30))
def test_basis_invariance_and_balance(dry_kg, absorption_pct, mc_pct):
    wet_kg = dry_kg * (1 + mc_pct / 100)
    dry = aggregate_moisture('CA', dry_kg, 'oven_dry', absorption_pct, mc_pct)
    wet = aggregate_moisture('CA', wet_kg, 'as_received', absorption_pct, mc_pct)
    assert wet.ssd_kg == pytest.approx(dry.ssd_kg, rel=1e-12)
    assert wet.free_water_kg == pytest.approx(dry.free_water_kg, rel=1e-12, abs=1e-12)
    water = effective_water(180, wet, wet)
    assert 350 + 180 + 2 * wet_kg == pytest.approx(
        350 + water.effective_water_kg + 2 * wet.ssd_kg, rel=1e-12)
    field = field_weights_strict(180, dry.ssd_kg, dry.ssd_kg,
                                mc_pct, absorption_pct, mc_pct, absorption_pct)
    assert oven_dry_mass_kg(field.coarse_wet_kg, 'as_received', absorption_pct, mc_pct) == pytest.approx(dry_kg, rel=1e-12)


@pytest.mark.parametrize('weight,basis,absorption,mc', [
    (-1, 'ssd', 1, 1), (1, 'unknown', 1, 1), (1, 'ssd', -1, 1),
    (1, 'ssd', 1, float('nan')), (1, 'ssd', 21, 1), (1, 'ssd', 1, 31)])
def test_invalid_inputs(weight, basis, absorption, mc):
    with pytest.raises(ValueError):
        aggregate_moisture('CA', weight, basis, absorption, mc)
