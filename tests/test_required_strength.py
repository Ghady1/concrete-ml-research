"""Forward/inverse course strength rules, including documented slide differences."""
import pytest
from hypothesis import given, strategies as st
from concretecalc.required_strength import required_average_strength_mpa, estimated_characteristic_strength_mpa


@pytest.mark.parametrize('fc,sigma,n,expected', [(31, None, None, 39.5),
    (31, 3.6, 17, 37.011664), (31, 2.4, 30, 34.216), (31, 3.8, 30, 36.404),
    (20.99, None, None, 27.99), (21, None, None, 29.5),
    (35, None, None, 43.5), (35.01, None, None, 45.01)])
def test_hand_values(fc, sigma, n, expected):
    result = required_average_strength_mpa(fc, sigma, n)
    assert result.fcr_mpa == pytest.approx(expected, abs=1e-9)


def test_slide_discrepancies():
    # Slides show 37.1 / 34.3; literal arithmetic gives 37.011664 / 34.216.
    assert required_average_strength_mpa(31, 3.6, 17).fcr_mpa == pytest.approx(37.1, abs=.1)
    assert required_average_strength_mpa(31, 2.4, 30).fcr_mpa == pytest.approx(34.3, abs=.1)


def test_insufficient_or_missing_sample_count():
    result = required_average_strength_mpa(31, 2.4, 12)
    assert result.method == 'no_data'
    assert result.fcr_mpa == 39.5
    assert result.flags[0].code == 'INSUFFICIENT_SAMPLES'
    missing = required_average_strength_mpa(31, 2.4, None)
    assert missing.f_factor == 1
    assert missing.flags[0].code == 'SAMPLE_COUNT_ASSUMED'


@pytest.mark.parametrize('mean,expected', [(28, 19.5), (29, 20.5), (44, 34), (45, 35)])
def test_inverse_gap(mean, expected):
    result = estimated_characteristic_strength_mpa(mean, None, None)
    assert result.fc_est_mpa == expected
    assert result.flags[0].code == 'INVERSE_BAND_GAP'


@given(st.floats(1, 100), st.floats(0, 10), st.integers(15, 50))
def test_statistical_inverse(fc, sigma, n):
    forward = required_average_strength_mpa(fc, sigma, n)
    inverse = estimated_characteristic_strength_mpa(forward.fcr_mpa, sigma, n)
    assert inverse.fc_est_mpa == pytest.approx(fc, abs=1e-10)


@given(st.floats(1, 100))
def test_no_data_inverse(fc):
    forward = required_average_strength_mpa(fc, None, None)
    inverse = estimated_characteristic_strength_mpa(forward.fcr_mpa, None, None)
    assert inverse.fc_est_mpa == pytest.approx(fc, abs=1e-10)


@pytest.mark.parametrize('fc,sigma,n', [(0, None, None), (31, -1, 30),
    (31, 2, 0), (31, 2, 1.5), (float('inf'), None, None)])
def test_invalid(fc, sigma, n):
    with pytest.raises(ValueError):
        required_average_strength_mpa(fc, sigma, n)
