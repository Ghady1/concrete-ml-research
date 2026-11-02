"""Course required-average and research characteristic estimates, MPa.

Rules are the approved course transcription, not a substituted design standard.
Professor questions Q6-Q8 and Q21 remain unresolved; no values are changed here.
"""
from dataclasses import dataclass
from typing import Literal

from concretecalc.flags import Flag
from concretecalc.tables.lookups import f_factor, required_strength_rules
from concretecalc.validation import _number


@dataclass(frozen=True)
class RequiredStrength:
    """Forward course calculation in MPa with both statistical candidates."""
    fc_mpa: float
    fcr_mpa: float
    method: Literal['statistical', 'no_data']
    f_factor: float | None
    sigma_mpa: float | None
    candidate_134_mpa: float | None
    candidate_233_mpa: float | None
    governing: str
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class CharacteristicEstimate:
    """Inverse research estimate, MPa; not a certified design strength."""
    fcr_mean_mpa: float
    fc_est_mpa: float
    margin_mpa: float
    method: Literal['statistical', 'no_data']
    label: str
    flags: tuple[Flag, ...]


def _factor(sigma_mpa: float | None, n_samples: int | None) -> tuple[float | None, tuple[Flag, ...]]:
    if sigma_mpa is not None:
        _number(sigma_mpa, 'sigma_mpa')
    if n_samples is not None:
        if type(n_samples) is not int or n_samples < 1:
            raise ValueError('n_samples must be an integer >= 1')
    if sigma_mpa is None:
        return None, ()
    if n_samples is None:
        return 1.0, (Flag('SAMPLE_COUNT_ASSUMED', 'warning', 'Sigma given without n_samples: assuming F=1 (A-11).'),)
    lookup = f_factor(n_samples)
    if lookup.value is None:
        return None, (Flag('INSUFFICIENT_SAMPLES', 'warning', 'Sample count below F-table minimum; sigma treated as unknown.'),)
    return lookup.value, ()


def _no_data_margin(fc_mpa: float, rules: dict[str, float]) -> float:
    if fc_mpa < rules['no_data.low_band_below_mpa']:
        return rules['no_data.margin_low_mpa']
    if fc_mpa <= rules['no_data.mid_band_up_to_mpa']:
        return rules['no_data.margin_mid_mpa']
    return rules['no_data.margin_high_mpa']


def required_average_strength_mpa(fc_mpa: float, sigma_mpa: float | None,
                                   n_samples: int | None) -> RequiredStrength:
    """fcr=max(fc+1.34*sF, fc+2.33*sF-3.45), or course no-data margins."""
    _number(fc_mpa, 'fc_mpa', strict=True)
    rules = required_strength_rules()
    factor, flags = _factor(sigma_mpa, n_samples)
    if factor is None:
        return RequiredStrength(fc_mpa, fc_mpa + _no_data_margin(fc_mpa, rules),
            'no_data', None, sigma_mpa, None, None, 'no_data_margin', flags)
    sigma_effective_mpa = sigma_mpa * factor
    first = fc_mpa + rules['statistical.coef_134'] * sigma_effective_mpa
    second = fc_mpa + rules['statistical.coef_233'] * sigma_effective_mpa - rules['statistical.offset_233_mpa']
    governing = 'candidate_134' if first >= second else 'candidate_233'
    return RequiredStrength(fc_mpa, max(first, second), 'statistical', factor,
                            sigma_mpa, first, second, governing, flags)


def estimated_characteristic_strength_mpa(fcr_mean_mpa: float, sigma_mpa: float | None,
                                          n_samples: int | None) -> CharacteristicEstimate:
    """Invert the same margins; choose conservative adjacent-band value in gaps."""
    _number(fcr_mean_mpa, 'fcr_mean_mpa', strict=True)
    rules = required_strength_rules()
    factor, flags = _factor(sigma_mpa, n_samples)
    label = 'estimated characteristic strength (research estimate)'
    if factor is not None:
        sigma_effective_mpa = sigma_mpa * factor
        margin_mpa = max(rules['statistical.coef_134'] * sigma_effective_mpa,
            rules['statistical.coef_233'] * sigma_effective_mpa - rules['statistical.offset_233_mpa'])
        return CharacteristicEstimate(fcr_mean_mpa, fcr_mean_mpa - margin_mpa,
                                      margin_mpa, 'statistical', label, flags)
    low_margin = rules['no_data.margin_low_mpa']
    mid_margin = rules['no_data.margin_mid_mpa']
    high_margin = rules['no_data.margin_high_mpa']
    low_edge = rules['no_data.low_band_below_mpa']
    high_edge = rules['no_data.mid_band_up_to_mpa']
    candidates = (fcr_mean_mpa - low_margin, fcr_mean_mpa - mid_margin,
                  fcr_mean_mpa - high_margin)
    if candidates[0] < low_edge:
        estimated_mpa = candidates[0]
    elif low_edge <= candidates[1] <= high_edge:
        estimated_mpa = candidates[1]
    elif candidates[2] > high_edge:
        estimated_mpa = candidates[2]
    else:
        # Discontinuous margins leave two gaps; lower adjacent candidate is
        # intentionally conservative and may lie outside its own forward band.
        estimated_mpa = candidates[1] if fcr_mean_mpa < low_edge + mid_margin else candidates[2]
        flags += (Flag('INVERSE_BAND_GAP', 'warning', 'Mean falls in a no-data band gap; lower adjacent estimate used (A-12).'),)
    if estimated_mpa <= 0:
        flags += (Flag('NONPOSITIVE_CHARACTERISTIC_ESTIMATE', 'warning', 'Inverse margin gives a nonpositive research estimate; not clamped.'),)
    return CharacteristicEstimate(fcr_mean_mpa, estimated_mpa, fcr_mean_mpa - estimated_mpa,
                                  'no_data', label, flags)
