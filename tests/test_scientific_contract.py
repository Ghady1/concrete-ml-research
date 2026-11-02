"""Independently derived checks for claims made in the Studio interface."""
from dataclasses import replace
import pytest
from concretecalc.schemas import Binder, CoarseAggregateProperties, FineAggregateProperties, MixInputs, Admixtures
from concretecalc.mode_b import run_mode_b


def example() -> MixInputs:
    return MixInputs(Binder('Lab cement', 350, 3.15, 'cement'), 180, 1050,
        CoarseAggregateProperties(2.65, 1600, 2, 5, 'angular'), 700,
        FineAggregateProperties(2.6, 1, 3, 2.6), 19, 'as_received', False,
        'moderate', air_pct=2)


def test_hand_calculated_moisture_and_absolute_volumes():
    # CA: 1050/1.05=1000 dry; free=1000*(.05-.02)=30 kg.
    # FA: 700/1.03 dry; free=(700/1.03)*(.03-.01) kg.
    report = run_mode_b(example())
    effective = 180 + 30 + 1400/103
    assert report.coarse.oven_dry_kg == pytest.approx(1000, abs=1e-10)
    assert report.coarse.free_water_kg == pytest.approx(30, abs=1e-10)
    assert report.water.effective_water_kg == pytest.approx(effective, abs=1e-10)
    assert report.wc == pytest.approx(effective/350, abs=1e-12)
    expected_volume = 350/3150 + effective/1000 + 1020/2650 + (70700/103)/2600 + .02
    assert report.volumes.total_m3 == pytest.approx(expected_volume, abs=1e-12)


def test_added_cement_does_not_rebalance_declared_yield():
    inputs = replace(example(), batch_volume_m3=1)
    before = run_mode_b(inputs)
    after = run_mode_b(replace(inputs, cement=replace(inputs.cement, weight_kg=400)))
    # Exactly 50 kg / 3150 kg/m3 extra cement; aggregates are unchanged.
    assert after.volumes.total_m3-before.volumes.total_m3 == pytest.approx(1/63, abs=1e-12)
    assert after.inputs.batch_volume_m3 == 1
    assert after.fine.ssd_kg == before.fine.ssd_kg


def test_record_only_fields_do_not_select_material_constants():
    before = run_mode_b(example())
    inputs = replace(example(), cement=replace(example().cement, name='Another label'), cement_strength_class='42.5 N')
    after = run_mode_b(inputs)
    assert before.predictions == after.predictions
    assert before.volumes == after.volumes
    assert before.slump == after.slump


def test_ssd_ignores_entered_mc_but_reports_mismatch():
    inputs = replace(example(), aggregate_weight_basis='ssd')
    result = run_mode_b(inputs)
    assert result.water.effective_water_kg == 180
    assert result.coarse.free_water_kg == 0
    assert result.fine.free_water_kg == 0
    assert any('SSD_MC_MISMATCH' in flag.code for flag in result.flags)


def test_air_override_affects_feret_not_an_extra_abrams_penalty():
    before = run_mode_b(example())
    after = run_mode_b(replace(example(), air_pct=6))
    for model in ('aci_table', 'abrams', 'bolomey'):
        assert before.predictions[model] == after.predictions[model]
    assert after.predictions['feret'].mean_28d_mpa < before.predictions['feret'].mean_28d_mpa


def test_age_and_unmodeled_admixtures_do_not_change_28_day_means():
    before = run_mode_b(example())
    after = run_mode_b(replace(example(), age_days=7, cement_type='III',
        admixtures=Admixtures(water_reducer_pct=15, superplasticizer_kg=2)))
    assert before.predictions == after.predictions
    assert after.age_adjusted['abrams'].strength_mpa != before.age_adjusted['abrams'].strength_mpa
    assert after.water == before.water
    assert any(flag.code == 'SLUMP_IGNORES_ADMIXTURES' for flag in after.flags)
