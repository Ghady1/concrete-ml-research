"""Water-table inversion and stated uncertainty rules."""
import pytest
from concretecalc.slump import estimate_slump_mm, slump_delta_from_water_delta_mm
from concretecalc.tables.lookups import mixing_water_kg_m3
from concretecalc.tables.models import Status


@pytest.mark.parametrize('nmas', [9.5,19,22,75,150])
@pytest.mark.parametrize('ae', [False,True])
@pytest.mark.parametrize('shape', ['angular','round_gravel'])
@pytest.mark.parametrize('slump', [37.5,87.5,162.5])
def test_inverse_midpoints(nmas, ae, shape, slump):
    water = mixing_water_kg_m3(slump,nmas,ae,shape)
    if water.value is None:
        assert nmas == 150 and slump == 162.5
        return
    result = estimate_slump_mm(water.value,nmas,ae,shape)
    assert result.slump_mm == pytest.approx(slump, abs=1e-9)
    assert result.band_mm == 25 and result.trial_tolerance_mm == 20


def test_extrapolation_and_floor():
    low = estimate_slump_mm(1,19,False,'angular')
    assert low.slump_mm == 0 and low.lower_mm == 0
    assert low.status == Status.EXTRAPOLATED
    assert 'NEGATIVE_SLUMP_CLAMPED' in {f.code for f in low.flags}
    high = estimate_slump_mm(300,19,False,'angular', 'pavements_slabs')
    assert high.status == Status.EXTRAPOLATED
    assert 'SLUMP_OUTSIDE_ELEMENT_RANGE' in {f.code for f in high.flags}
    assert slump_delta_from_water_delta_mm(6) == 25
    assert slump_delta_from_water_delta_mm(-6) == -25


def test_invalid_water():
    with pytest.raises(ValueError):
        estimate_slump_mm(float('nan'),19,False,'angular')
