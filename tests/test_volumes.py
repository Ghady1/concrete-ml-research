"""Hand volumes, threshold boundaries and aggregate packing checks."""
import pytest
from hypothesis import given, strategies as st

from concretecalc.schemas import Binder, CoarseAggregateProperties, FineAggregateProperties
from concretecalc.volumes import volume_check, unit_weight_check, packing_indicators, absolute_volume_m3

BINDERS = (Binder('cement', 315, 3.15, 'cement'),)


def test_hand_volumes_and_density():
    v = volume_check(BINDERS, 200, 1060, 2.65, 728, 2.6, 2)
    assert (v.cement_m3, v.water_m3, v.coarse_m3, v.fine_m3, v.air_m3) == pytest.approx((.1, .2, .4, .28, .02), abs=1e-12)
    assert v.total_m3 == pytest.approx(1, abs=1e-12)
    assert v.implied_air_pct == pytest.approx(2, abs=1e-12)
    assert v.flags == ()
    density = unit_weight_check(BINDERS, 200, 1060, 728, 19, True)
    assert density.computed_kg_m3 == 2303
    assert density.aci_kg_m3 == 2276
    assert density.deviation_pct == pytest.approx(100 * (2303 - 2276) / 2276, abs=1e-12)


@pytest.mark.parametrize('closure,severity', [(0.02, None), (0.020001, 'warning'),
    (0.05, 'warning'), (0.050001, 'error'), (-0.020001, 'warning'), (-0.050001, 'error')])
def test_closure_boundaries(closure, severity):
    # Binary-exact component volumes isolate the decimal threshold comparison.
    v = volume_check((Binder('cement', 250, 2, 'cement'),),
                     250, 500, 2, (0.375 + closure) * 2000, 2, 0)
    if severity is None:
        assert v.flags == ()
    else:
        assert v.flags[0].severity == severity


def test_packing_hand_values():
    coarse = CoarseAggregateProperties(2.65, 1600, 1, 1, 'angular')
    fine = FineAggregateProperties(2.6, 1, 1, 2.6)
    v = volume_check(BINDERS, 200, 1060, 2.65, 728, 2.6, 2)
    p = packing_indicators(1060/1.01, 1060, coarse, 728, fine, 19, v)
    assert p.coarse_void_content == pytest.approx(1 - 1600 / (2.65 / 1.01 * 1000), abs=1e-12)
    assert p.coarse_bulk_ratio_actual == pytest.approx(1060/1.01/1600, abs=1e-12)
    assert p.coarse_bulk_ratio_table == pytest.approx(.64, abs=1e-12)
    assert p.paste_volume_m3 == pytest.approx(.32, abs=1e-12)
    assert p.fine_fraction_by_mass == pytest.approx(728/1788, abs=1e-12)
    assert p.fine_fraction_by_volume == pytest.approx(.28/.68, abs=1e-12)


@given(st.floats(100, 500), st.floats(100, 250), st.floats(0, 10))
def test_volume_identity(cement_kg, water_kg, air_pct):
    v = volume_check((Binder('cement', cement_kg, 3.15, 'cement'),), water_kg,
                     1000, 2.65, 750, 2.6, air_pct)
    assert v.total_m3 - v.air_m3 == pytest.approx(1 - v.implied_air_pct/100, abs=1e-12)


@pytest.mark.parametrize('mass,sg', [(-1, 2.6), (1, 0), (float('nan'), 2.6)])
def test_invalid_absolute_volume(mass, sg):
    with pytest.raises(ValueError):
        absolute_volume_m3(mass, sg)


def test_scm_and_off_node_density():
    v = volume_check(BINDERS + (Binder('ash', 24, 2.4, 'scm'),),
                     200, 1060, 2.65, 702, 2.6, 2)
    assert v.scm_m3 == pytest.approx(.01, abs=1e-12)
    assert v.total_m3 == pytest.approx(1, abs=1e-12)
    left = unit_weight_check(BINDERS, 200, 1060, 728, 19, True)
    right = unit_weight_check(BINDERS, 200, 1060, 728, 25, True)
    middle = unit_weight_check(BINDERS, 200, 1060, 728, 22, True)
    assert middle.aci_kg_m3 == pytest.approx((left.aci_kg_m3 + right.aci_kg_m3)/2, abs=1e-12)
    low = unit_weight_check(BINDERS, 100, 100, 100, 19, True)
    assert low.flags[0].code == 'UNIT_WEIGHT_DEVIATION'
