"""ACI 209R-92 literal age equation, with explicit optional normalisation."""
from dataclasses import dataclass
from concretecalc.schemas import CementType, Curing
from concretecalc.flags import Flag
from concretecalc.tables.lookups import age_coefficients, input_validation_limits
from concretecalc.validation import _number, _choice


@dataclass(frozen=True)
class AgeAdjusted:
    """Age-adjusted research strength, MPa, days and coefficient provenance."""
    f28_mpa: float
    age_days: float
    strength_mpa: float
    factor: float
    a_days: float
    b: float
    normalised: bool
    coefficient_type: CementType
    flags: tuple[Flag, ...]


def age_factor(age_days: float, cement_type: CementType, curing: Curing,
               normalise_to_28d: bool = False) -> tuple[float, float, float, tuple[Flag, ...]]:
    """Factor=t/(a+b*t); optional division by its value at 28 days (Q5/Q20)."""
    _number(age_days, 'age_days', input_validation_limits()['hard.age_days.min'])
    _choice(cement_type, CementType, 'cement_type')
    _choice(curing, Curing, 'curing')
    flags: tuple[Flag, ...] = ()
    coefficient_type = cement_type
    if cement_type not in ('I', 'III'):
        coefficient_type = 'I'
        flags = (Flag('CEMENT_TYPE_APPROXIMATION', 'warning', 'Using Type I age coefficients for cement type '+cement_type),)
    a_days, b = age_coefficients(coefficient_type, curing)
    factor = age_days / (a_days + b*age_days)
    if normalise_to_28d:
        factor /= 28/(a_days+b*28)
    return factor, a_days, b, flags


def strength_at_age_mpa(f28_mpa: float, age_days: float, cement_type: CementType,
                       curing: Curing, normalise_to_28d: bool = False) -> AgeAdjusted:
    """Research strength MPa=f28*age factor; warn outside stated 20-70 MPa basis."""
    _number(f28_mpa, 'f28_mpa', strict=True)
    factor, a_days, b, flags = age_factor(age_days, cement_type, curing, normalise_to_28d)
    limits = input_validation_limits()
    if not limits['age_model.valid_min_mpa'] <= f28_mpa <= limits['age_model.valid_max_mpa']:
        flags += (Flag('AGE_MODEL_RANGE', 'warning', '28-day strength outside age-equation validity range.'),)
    coefficient_type = cement_type if cement_type in ('I', 'III') else 'I'
    return AgeAdjusted(f28_mpa, age_days, f28_mpa*factor, factor, a_days, b,
                        normalise_to_28d, coefficient_type, flags)
