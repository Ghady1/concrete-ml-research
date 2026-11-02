"""Input boundary tests: invalid data must not reach engineering calculations."""
from dataclasses import replace, FrozenInstanceError, fields

import pytest

from concretecalc.schemas import (Binder, CoarseAggregateProperties,
    FineAggregateProperties, MixInputs, ModeAInputs, Admixtures, binders)
from concretecalc.validation import validate_mode_a, validate_mode_b
from concretecalc.flags import flags_from_lookup, count_by_severity
from concretecalc.tables.models import Lookup, Status


@pytest.fixture
def mix():
    return MixInputs(Binder('Portland', 350, 3.15, 'cement'), 180, 1000,
        CoarseAggregateProperties(2.65, 1600, 1, 1, 'angular'), 750,
        FineAggregateProperties(2.6, 1, 1, 2.6), 19, 'ssd', False, 'moderate')


@pytest.mark.parametrize('field,value', [
    ('water_kg', 0), ('coarse_kg', -1), ('fine_kg', float('nan')),
    ('age_days', 0.5), ('nmas_mm', 0), ('batch_volume_m3', 0),
    ('air_pct', float('inf')), ('sigma_mpa', -1), ('n_samples', 0),
    ('n_samples', 1.5), ('cube_to_cylinder_factor', 0),
    ('aggregate_weight_basis', 'wet'), ('curing', 'dry'), ('specimen', 'cube'),
    ('cement_type', 'unknown'), ('exposure', 'unknown'), ('element', 'unknown'),
])
def test_bad_mix_fields(mix, field, value):
    with pytest.raises(ValueError, match=field):
        validate_mode_b(replace(mix, **{field: value}))


@pytest.mark.parametrize('field,value', [('sg_ssd', 0), ('drd_kg_m3', 0),
    ('absorption_pct', 21), ('mc_pct', 31), ('shape', 'unknown')])
def test_bad_coarse(mix, field, value):
    with pytest.raises(ValueError, match=field):
        validate_mode_b(replace(mix, coarse=replace(mix.coarse, **{field: value})))


def test_valid_normalized_batch(mix):
    assert validate_mode_b(mix) == ()
    batch = replace(mix, cement=replace(mix.cement, weight_kg=35), water_kg=18,
        coarse_kg=100, fine_kg=75, batch_volume_m3=0.1)
    assert validate_mode_b(batch) == ()


@pytest.mark.parametrize('field,value,code', [
    ('water_kg', 99, 'SOFT_LIMIT_WATER'), ('air_pct', 11, 'SOFT_LIMIT_AIR'),
    ('age_days', 2, 'SOFT_LIMIT_AGE'), ('nmas_mm', 22, 'NONSTANDARD_NMAS'),
    ('cement_type', 'II', 'CEMENT_TYPE_APPROXIMATION'),
    ('specimen', 'cube_150', 'CUBE_FACTOR_MISSING')])
def test_soft_flags(mix, field, value, code):
    assert [f.code for f in validate_mode_b(replace(mix, **{field: value}))] == [code]


def test_nested_flags_and_binders(mix):
    scm = Binder('ash', 20, 2.4, 'scm')
    changed = replace(mix, scm=(scm,), coarse=replace(mix.coarse, mc_pct=2),
        fine=replace(mix.fine, fm=3.2), admixtures=Admixtures(water_reducer_pct=10))
    codes = {f.code for f in validate_mode_b(changed)}
    assert {'SCM_NOT_SUPPORTED', 'SSD_MC_MISMATCH_COARSE', 'FM_EXTRAPOLATION',
            'WATER_REDUCER_NOT_MODELED'} <= codes
    assert binders(changed) == (mix.cement, scm)
    with pytest.raises(FrozenInstanceError):
        mix.water_kg = 1


def test_mode_a_geometry(mix):
    a = ModeAInputs(25, 'building_columns', 'moderate', False, 3.15, mix.coarse, mix.fine)
    with pytest.raises(ValueError, match='nmas_mm'):
        validate_mode_a(a)
    assert validate_mode_a(replace(a, nmas_mm=19)) == ()
    assert validate_mode_a(replace(a, cover_mm=40)) == ()
    with pytest.raises(ValueError, match='cover_mm'):
        validate_mode_a(replace(a, cover_mm=-1))


def test_flag_translation():
    assert flags_from_lookup(Lookup(1, Status.OK), 'TABLE') == ()
    flags = flags_from_lookup(Lookup(None, Status.UNAVAILABLE, ('missing',)), 'TABLE')
    assert flags[0].severity == 'error'
    assert count_by_severity(flags) == {'info': 0, 'warning': 0, 'error': 1}
    assert flags_from_lookup(Lookup(1, Status.CLAMPED, ('clipped',)), 'TABLE')[0].severity == 'warning'


@pytest.mark.parametrize('field,value', [('weight_kg', 0), ('sg', 0), ('kind', 'scm')])
def test_bad_cement(mix, field, value):
    with pytest.raises(ValueError, match=field):
        validate_mode_b(replace(mix, cement=replace(mix.cement, **{field: value})))


@pytest.mark.parametrize('field,value', [('sg_ssd', -1), ('absorption_pct', -1),
    ('mc_pct', -1), ('fm', 0)])
def test_bad_fine(mix, field, value):
    with pytest.raises(ValueError, match=field):
        validate_mode_b(replace(mix, fine=replace(mix.fine, **{field: value})))


@pytest.mark.parametrize('field,value', [('water_reducer_pct', 100),
    ('water_reducer_pct', -1), ('superplasticizer_kg', -1),
    ('air_entrainer_ml_per_pct_per_100kg', float('nan'))])
def test_bad_admixture(mix, field, value):
    with pytest.raises(ValueError, match=field):
        validate_mode_b(replace(mix, admixtures=Admixtures(**{field: value})))


@pytest.mark.parametrize('field,value', [('specified_fc_mpa', 0), ('cement_sg', 0),
    ('slump_target_mm', -1), ('batch_volume_m3', 0), ('bb0_adjustment_factor', 0),
    ('durability_class', 'bad'), ('moisture_convention', 'bad'),
    ('water_reducer_pct', 100), ('element', None)])
def test_bad_mode_a(mix, field, value):
    a = ModeAInputs(25, 'building_columns', 'moderate', False, 3.15,
                    mix.coarse, mix.fine, nmas_mm=19)
    with pytest.raises(ValueError, match=field):
        validate_mode_a(replace(a, **{field: value}))


def test_explicit_basis_required(mix):
    values = {f.name: getattr(mix, f.name) for f in fields(mix)}
    del values['aggregate_weight_basis']
    with pytest.raises(TypeError, match='aggregate_weight_basis'):
        MixInputs(**values)


@pytest.mark.parametrize('material,field,value,code', [
    ('cement', 'weight_kg', 149, 'SOFT_LIMIT_CEMENT'),
    ('cement', 'sg', 2.8, 'SOFT_LIMIT_CEMENT_SG'),
    ('coarse', 'sg_ssd', 2.2, 'SOFT_LIMIT_COARSE_SG'),
    ('coarse', 'drd_kg_m3', 1199, 'SOFT_LIMIT_COARSE_DRD'),
    ('coarse', 'absorption_pct', 7, 'SOFT_LIMIT_COARSE_ABSORPTION_PCT'),
    ('coarse', 'mc_pct', 16, 'SOFT_LIMIT_COARSE_MC_PCT'),
    ('fine', 'sg_ssd', 3, 'SOFT_LIMIT_FINE_SG'),
    ('fine', 'absorption_pct', 9, 'SOFT_LIMIT_FINE_ABSORPTION_PCT'),
    ('fine', 'mc_pct', 21, 'SOFT_LIMIT_FINE_MC_PCT'),
    ('fine', 'fm', 3.6, 'SOFT_LIMIT_FINE_FM'),
])
def test_each_material_soft_limit(mix, material, field, value, code):
    changed = replace(mix, **{material: replace(getattr(mix, material), **{field: value})})
    assert [f.code for f in validate_mode_b(changed)].count(code) == 1
