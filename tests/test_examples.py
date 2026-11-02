"""Independent arithmetic recorded first in docs/hand_calcs.md, not engine snapshots."""
from dataclasses import replace
import pytest
from concretecalc.schemas import ModeAInputs, CoarseAggregateProperties, FineAggregateProperties
from concretecalc.mix_design import design_mix

# SI answers independently evaluated before running concretecalc on the examples.
# Strength abs .01 MPa, mass abs .01 kg/m3 and w/c abs .001 as documented.
CASES = [
    (1,False,37.5,'moderate',314.803719,181,1227.815217,659.780922,153.070599,153.817521,.574961442),
    (1,False,38.1,'moderate',313.801912,180.424,1230.237209,660.381046,152.453533,153.201134,.574961442),
    (1,True,37.5,'moderate',340.233234,165,1227.815217,588.037837,138.505461,139.171164,.484961442),
    (1,True,38.1,'moderate',339.441419,164.616,1230.237209,587.952503,138.094103,138.759710,.484961442),
    (2,True,19,'moderate',348.888889,157,1075.84,693.831033,122.963167,123.139378,.45),
    (2,True,25,'moderate',328.888889,148,1159.89,663.352717,114.013923,114.182394,.45),
    (2,True,19,'severe',348.888889,157,1075.84,668.131033,123.785567,123.955251,.45),
    (2,True,25,'severe',334,148,1159.89,620.632699,115.380964,115.538585,.443113772),
]


def example_inputs(example, ae, nmas, exposure):
    if example == 1:
        return ModeAInputs(20.68427187,'reinforced_foundation_walls_footings',exposure,ae,3.15,
            CoarseAggregateProperties(2.69,1681.93865385,.8,2,'angular'),
            FineAggregateProperties(2.65,6,8,2.6),nmas_mm=nmas)
    return ModeAInputs(24.1,'building_columns',exposure,True,3.15,
        CoarseAggregateProperties(2.62,1681,.4,1.5,'round_gravel'),
        FineAggregateProperties(2.57,.8,4,2.6),sigma_mpa=2.4,n_samples=31,
        nmas_mm=nmas,durability_class='freeze_thaw_moist')


@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('convention',['course','strict'])
def test_examples(case, convention):
    example,ae,nmas,exposure,c,w,ca,fa,course_w,strict_w,wc = case
    inputs = replace(example_inputs(example,ae,nmas,exposure),moisture_convention=convention)
    report = design_mix(inputs)
    assert report.cement.cement_kg_m3 == pytest.approx(c,abs=.01)
    assert report.water_air.water_kg_m3 == pytest.approx(w,abs=.01)
    assert report.coarse.coarse_dry_kg_m3 == pytest.approx(ca,abs=.01)
    assert report.fine.fine_ssd_kg_m3 == pytest.approx(fa,abs=.01)
    assert report.cement.wc_final == pytest.approx(wc,abs=.001)
    expected_water = course_w if convention=='course' else strict_w
    assert report.field.water_adjusted_kg == pytest.approx(expected_water,abs=.01)
    assert report.batch.water_kg == pytest.approx(expected_water,abs=.01)
    assert report.proportions.water == pytest.approx(expected_water/c,abs=.001)
    expected_fcr = 27.68427187 if example==1 else 27.316
    assert report.wc.fcr.fcr_mpa == pytest.approx(expected_fcr,abs=.01)
    if example==2:
        assert 'DURABILITY_MIN_FC' in {f.code for f in report.flags}
        expected = 'min_cement' if nmas==25 and exposure=='severe' else 'durability'
        assert report.governing_constraint == expected


def test_rounded_21_mpa_band_is_separate():
    original = example_inputs(1,False,37.5,'moderate')
    rounded = design_mix(replace(original,specified_fc_mpa=21))
    assert rounded.wc.fcr.fcr_mpa == 29.5
    assert rounded.wc.wc == pytest.approx(.57+1.5*(.48-.57)/7,abs=1e-12)
