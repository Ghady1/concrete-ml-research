"""End-to-end Mode B invariants; no UI involved."""
from dataclasses import replace
import json
import pytest

from concretecalc.schemas import Binder, CoarseAggregateProperties, FineAggregateProperties, MixInputs
from concretecalc.mode_b import run_mode_b, report_to_dict


@pytest.fixture
def inputs():
    return MixInputs(Binder('cement',315,3.15,'cement'),200,1060,
        CoarseAggregateProperties(2.65,1600,1,1,'angular'),728,
        FineAggregateProperties(2.6,1,1,2.6),19,'ssd',False,'moderate',air_pct=2)


def test_hand_report(inputs):
    report = run_mode_b(inputs)
    assert report.water.effective_water_kg == 200
    assert report.wc == pytest.approx(200/315, abs=1e-12)
    assert report.volumes.total_m3 == pytest.approx(1, abs=1e-12)
    assert report.unit_weight.computed_kg_m3 == 2303
    assert report.air_source == 'user'
    assert set(report.predictions) == {'aci_table','abrams','bolomey','feret'}
    assert len(report.plot.model_curves['abrams']) == 61
    assert len(report.plot.aci_non_ae_points) == 6
    assert len(report.plot.aci_ae_points) == 5
    assert all(p.constants_source and p.disclaimer for p in report.predictions.values())
    assert all(v is None for v in report.characteristic.values())
    assert report.disclaimer
    json.dumps(report_to_dict(report), allow_nan=False)


def test_batch_and_basis_invariance(inputs):
    original = run_mode_b(inputs)
    batch = replace(inputs, cement=replace(inputs.cement, weight_kg=630),
        water_kg=400, coarse_kg=2120, fine_kg=1456, batch_volume_m3=2)
    report = run_mode_b(batch)
    assert report.per_m3_scale == .5
    assert report.wc == original.wc
    assert report.predictions == original.predictions
    for basis, coarse, fine in [('oven_dry',1060/1.01,728/1.01),
                                ('as_received',1060,728)]:
        report = run_mode_b(replace(inputs,aggregate_weight_basis=basis,coarse_kg=coarse,fine_kg=fine))
        assert report.wc == pytest.approx(original.wc, rel=1e-12)
        assert report.volumes.total_m3 == pytest.approx(original.volumes.total_m3, abs=1e-12)


def test_scm_cube_age_and_characteristic(inputs):
    report = run_mode_b(replace(inputs, scm=(Binder('ash',20,2.4,'scm'),),
        specimen='cube_150',cube_to_cylinder_factor=.8,sigma_mpa=2,n_samples=30,age_days=7))
    assert report.wcm == pytest.approx(200/335, abs=1e-12)
    assert 'SCM_NOT_SUPPORTED' in {f.code for f in report.flags}
    for name, prediction in report.predictions.items():
        assert report.cube_equivalent_mpa[name] == pytest.approx(prediction.mean_28d_mpa/.8, abs=1e-12)
        assert report.age_adjusted[name].strength_mpa < prediction.mean_28d_mpa
        assert report.characteristic[name].margin_mpa == pytest.approx(2.68, abs=1e-12)


def test_default_air_and_spread(inputs):
    report = run_mode_b(replace(inputs,air_pct=None,air_entrained=True),model_spread_threshold_mpa=0)
    assert report.air_pct == 5 and report.air_source == 'aci_table'
    assert report.air_entrainer_dosage_ml_m3 == pytest.approx(6.3*5*315/100, abs=1e-12)
    assert 'MODEL_SPREAD' in {f.code for f in report.flags}
    with pytest.raises(ValueError,match='water_kg'):
        run_mode_b(replace(inputs,water_kg=0))


def test_absorption_cannot_make_effective_water_nonpositive(inputs):
    with pytest.raises(ValueError,match='effective_water'):
        run_mode_b(replace(inputs, water_kg=1, aggregate_weight_basis='oven_dry',
            coarse=replace(inputs.coarse, absorption_pct=20, mc_pct=0)))
