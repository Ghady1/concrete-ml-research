"""Strength contracts and provisional-fit acceptance, PLAN M09."""
from dataclasses import replace
import json
from importlib.resources import files

import numpy as np
import pytest
from hypothesis import given, strategies as st

from concretecalc.strength import MixState
from concretecalc.strength.registry import MODEL_REGISTRY, default_constants, list_presets, strength_curve_mpa
from concretecalc.strength.age import age_factor, strength_at_age_mpa
from concretecalc.calibration.fit import fit_abrams, fit_bolomey, fit_feret
from concretecalc.tables.loader import load_series, load_presets


def state(wc=.5, ae=False):
    water = 184 if ae else 205
    cement = water/wc
    air = 5 if ae else 2
    return MixState(cement, cement, water, wc, wc, air, ae,
                    cement/3150, water/1000, air/100, 'I', 'moist', 28)


@pytest.mark.parametrize('name', ['aci_table', 'abrams', 'bolomey', 'feret'])
@pytest.mark.parametrize('ae', [False, True])
@given(st.floats(.25, .84), st.floats(.001, .01))
def test_monotonicity(name, ae, wc, delta):
    constants = default_constants(name, ae)
    lower = MODEL_REGISTRY[name](state(wc, ae), constants)
    higher = MODEL_REGISTRY[name](state(wc+delta, ae), constants)
    assert lower.mean_28d_mpa > higher.mean_28d_mpa
    assert not lower.calibrated
    assert lower.constants_source
    assert lower.disclaimer


@pytest.mark.parametrize('ae', [False, True])
def test_refit_and_pointwise_acceptance(ae):
    table = load_series('wc_vs_strength')
    wc_all = table.columns['ae' if ae else 'non_ae']
    mask = np.isfinite(wc_all)
    wc, strengths = wc_all[mask], table.x[mask]
    for name, fitted in [('abrams', fit_abrams(wc, strengths)),
                         ('bolomey', fit_bolomey(1/wc, strengths))]:
        constants = default_constants(name, ae)
        assert constants.values == pytest.approx(fitted.values, rel=1e-9)
    for name, tolerance in [('aci_table', 1e-9), ('abrams', 2.5), ('bolomey', 4.5), ('feret', 3.2)]:
        # Feret 3.2 MPa approved 2026-11-02; original 2.5 fails at AE 41 MPa.
        for ratio, measured in zip(wc, strengths):
            prediction = MODEL_REGISTRY[name](state(float(ratio), ae), default_constants(name, ae))
            assert prediction.mean_28d_mpa == pytest.approx(measured, abs=tolerance)


def test_feret_refit():
    ratios, strengths = [], []
    table = load_series('wc_vs_strength')
    for ae in (False, True):
        wc = table.columns['ae' if ae else 'non_ae']
        for ratio, strength in zip(wc, table.x):
            if np.isfinite(ratio):
                mix = state(float(ratio), ae)
                ratios.append(mix.cement_volume_m3/(mix.cement_volume_m3+mix.water_volume_m3+mix.air_volume_m3))
                strengths.append(strength)
    fit = fit_feret(np.array(ratios), np.array(strengths))
    assert default_constants('feret', False).values == pytest.approx(fit.values, rel=1e-9)


@pytest.mark.parametrize('curing,cement,tolerance', [('moist','I',.01), ('moist','III',.01),
    ('steam','I',.015), ('steam','III',.01)])
def test_age_at_28(curing, cement, tolerance):
    literal = strength_at_age_mpa(30, 28, cement, curing)
    assert literal.strength_mpa == pytest.approx(30, rel=tolerance)
    normalized = strength_at_age_mpa(30, 28, cement, curing, True)
    assert normalized.strength_mpa == pytest.approx(30, abs=1e-12)
    assert age_factor(7, cement, curing)[0] < age_factor(28, cement, curing)[0]


def test_age_fallback_and_flags():
    factor, a, b, flags = age_factor(28, 'II', 'moist')
    assert a == 4 and b == .85
    assert flags[0].code == 'CEMENT_TYPE_APPROXIMATION'
    assert strength_at_age_mpa(10, 7, 'I', 'moist').flags[0].code == 'AGE_MODEL_RANGE'
    with pytest.raises(ValueError):
        age_factor(0, 'I', 'moist')


def test_registry_presets_and_curve():
    assert set(MODEL_REGISTRY) == {'aci_table','abrams','bolomey','feret'}
    assert 'lit_63.45_14_7d' in list_presets('abrams')
    constants = default_constants('abrams', False, 'lit_63.45_14_7d')
    with pytest.raises(ValueError, match='28'):
        MODEL_REGISTRY['abrams'](state(), constants)
    curve = strength_curve_mpa('abrams', (.4,.5,.6), state(), default_constants('abrams', False))
    assert len(curve) == 3 and curve[0] > curve[1] > curve[2]
    with pytest.raises(ValueError):
        default_constants('unknown', False)
    assert load_presets()
    raw = json.loads((files('concretecalc')/'data'/'model_constants.json').read_text())
    assert raw['meta']['source'] and not raw['meta']['verified_against_primary']


def test_model_range_and_constant_checks():
    constants = default_constants('abrams', False)
    result = MODEL_REGISTRY['abrams'](state(.9), constants)
    assert 'WC_MODEL_RANGE' in {f.code for f in result.flags}
    with pytest.raises(ValueError):
        MODEL_REGISTRY['abrams'](state(), replace(constants, values={'A': 0, 'B': 7}))


@pytest.mark.parametrize('fit,x', [(fit_abrams, [.3,.4]), (fit_bolomey, [2,3]), (fit_feret, [.4,.5])])
def test_fit_requires_three_rows(fit, x):
    with pytest.raises(ValueError):
        fit(np.array(x), np.array([30,40]))


def test_fit_exact_synthetic_and_statistics():
    wc = np.array([.3,.4,.5,.6])
    abrams = fit_abrams(wc, 100/10**wc)
    assert abrams.values == pytest.approx({'A':100,'B':10}, rel=1e-12)
    assert abrams.r2_space == 'log'
    assert abrams.r2 == pytest.approx(1, abs=1e-12)
    assert abrams.rmse_mpa == pytest.approx(0, abs=1e-12)
    assert fit_bolomey(1/wc, 20*(1/wc-.5)).values['K'] == pytest.approx(20, abs=1e-12)
    assert fit_feret(wc, 230*wc**2).values['K'] == pytest.approx(230, abs=1e-12)
    for x, y in [(wc, np.array([1,2,3,np.nan])), (wc, np.array([1,2,3,0]))]:
        with pytest.raises(ValueError):
            fit_abrams(x,y)


def test_preset_loader_rejects_bad_data(monkeypatch):
    import concretecalc.tables.loader as loader
    raw = json.loads((files('concretecalc')/'data'/'model_constants.json').read_text())
    raw['presets'][0]['values']['A'] = -1
    monkeypatch.setattr(loader, '_read_json', lambda table_id: raw)
    with pytest.raises(ValueError, match='positive'):
        loader.load_presets()


def test_presets_are_independent():
    first = default_constants('abrams', False)
    first.values['A'] = -1
    assert default_constants('abrams', False).values['A'] > 0
