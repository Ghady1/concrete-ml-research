"""Mode A steps and Mode A -> Mode B physical round trips."""
from dataclasses import replace
import pytest
from hypothesis import given, strategies as st
from concretecalc.schemas import ModeAInputs, CoarseAggregateProperties, FineAggregateProperties
from concretecalc.mix_design import (design_mix, to_mode_b_inputs, step2_nmas,
    step1_slump, step3_water_air, step4_wc, step5_cement, step6_coarse,
    step7_fine, step8_moisture, step9_proportions, step10_batch)
from concretecalc.mode_b import run_mode_b


def inputs(**changes):
    return ModeAInputs(25,'building_columns','moderate',False,3.15,
        CoarseAggregateProperties(2.65,1600,1,2,'angular'),
        FineAggregateProperties(2.6,1,3,2.6),nmas_mm=19,**changes)


def test_nmas_example():
    step = step2_nmas(200,40,40,None,None)
    assert step.limit_mm == 30 and step.max_size_mm == 25 and step.nmas_mm == 19
    assert step2_nmas(None,None,None,None,22).nmas_mm == 22
    assert step2_nmas(10,None,None,None,None).flags[0].severity == 'error'


@pytest.mark.parametrize('convention', ['course','strict'])
def test_hand_steps_and_round_trip(convention):
    report = design_mix(inputs(moisture_convention=convention))
    assert report.slump.target_mm == 100
    assert report.water_air.water_kg_m3 == 205
    assert report.wc.fcr.fcr_mpa == 33.5
    assert report.wc.wc == pytest.approx(.57+(33.5-28)/7*(.48-.57), abs=1e-12)
    assert report.coarse.coarse_dry_kg_m3 == pytest.approx(1600*.64, abs=1e-12)
    assert sum(report.fine.volumes_m3.values())+report.fine.fine_volume_m3 == pytest.approx(1, abs=1e-12)
    predicted = run_mode_b(to_mode_b_inputs(report))
    assert predicted.water.effective_water_kg == pytest.approx(205, rel=1e-12)
    assert predicted.predictions['aci_table'].mean_28d_mpa == pytest.approx(33.5, abs=.5)
    if convention == 'strict':
        assert predicted.coarse.ssd_kg == pytest.approx(report.coarse.coarse_ssd_kg_m3, rel=1e-12)
        assert predicted.fine.ssd_kg == pytest.approx(report.fine.fine_ssd_kg_m3, rel=1e-12)
    assert report.field.convention != report.field_other_convention.convention
    assert report.disclaimer
    for name in ('abrams','bolomey','feret'):
        assert predicted.predictions[name].mean_28d_mpa == pytest.approx(33.5, abs=4.5)


def test_governing_constraints():
    durability = design_mix(inputs(durability_class='corrosion_protection'))
    assert durability.governing_constraint == 'durability'
    predicted = run_mode_b(to_mode_b_inputs(durability))
    assert predicted.predictions['aci_table'].mean_28d_mpa > durability.wc.fcr.fcr_mpa
    cement = design_mix(replace(inputs(underwater=True),specified_fc_mpa=14))
    assert cement.governing_constraint == 'min_cement'
    assert cement.cement.cement_kg_m3 == 385
    assert 'MIN_CEMENT_GOVERNS' in {f.code for f in cement.flags}


@given(st.floats(15,35),st.floats(2.4,3))
def test_design_volume_property(fc, fm):
    report = design_mix(replace(inputs(moisture_convention='strict'),specified_fc_mpa=fc,
                                fine=replace(inputs().fine,fm=fm)))
    assert sum(report.fine.volumes_m3.values())+report.fine.fine_volume_m3 == pytest.approx(1, abs=1e-12)


def test_course_proportions_and_batch():
    from concretecalc.moisture import field_weights_course
    field = field_weights_course(320,1940,1110,2,1,6,1.5)
    proportions = step9_proportions(580,field)
    assert (proportions.cement,proportions.fine,proportions.coarse,proportions.water) == pytest.approx((1,2.03,3.41,.43),abs=.005)
    batch = step10_batch(580,field,.1)
    assert batch.cement_kg == 58 and batch.water_kg == pytest.approx(25.065,abs=1e-12)


def test_individual_steps():
    assert step1_slump('mass_concrete',None,True).max_mm == 100
    water = step3_water_air(75,19,False,'moderate','angular',10)
    assert water.water_table_kg_m3 == 205 and water.water_kg_m3 == 184.5
    wc = step4_wc(25,None,None,False,'freeze_thaw_moist')
    assert wc.wc == .45 and wc.governing == 'durability'
    assert 'DURABILITY_MIN_FC' in {f.code for f in wc.flags}
    cement = step5_cement(100,.5,'strength',19,'severe',True,True)
    assert cement.minimum_kg_m3 == 385 and cement.minimum_reason == 'underwater'
    assert cement.wc_final == pytest.approx(100/385,abs=1e-12)
    coarse = step6_coarse(19,2.6,1600,1,1)
    assert coarse.coarse_ssd_kg_m3 == pytest.approx(1024*1.01,abs=1e-12)
    fine = step7_fine(315,3.15,200,2,1060,2.65,2.6,19,False)
    assert fine.fine_ssd_kg_m3 == pytest.approx(728,abs=1e-9)
    assert fine.fine_weight_method_kg_m3 == 2347-315-200-1060


def test_policy_raise_and_impossible_volume():
    from concretecalc.tables.interpolate import OutOfRangeError
    with pytest.raises(OutOfRangeError):
        design_mix(replace(inputs(),fine=replace(inputs().fine,fm=3.2)),policy='raise')
    with pytest.raises(ValueError,match='fine_volume'):
        step7_fine(3150,3.15,200,2,1060,2.65,2.6,19,False)
