"""Foundational slump estimate from the mixing-water table (task section 6).

Placeholder uncertainty is not a statistical confidence interval. Admixture
effects are not modeled; the calling report must flag any supplied admixtures.
"""
from dataclasses import dataclass
from concretecalc.flags import Flag, flags_from_lookup
from concretecalc.schemas import AggregateShape, ElementType
from concretecalc.tables.interpolate import Policy
from concretecalc.tables.lookups import slump_for_water_mm, slump_limits_mm, input_validation_limits
from concretecalc.tables.models import Status
from concretecalc.validation import _number


@dataclass(frozen=True)
class SlumpEstimate:
    """Slump and placeholder uncertainty endpoints in mm, with lookup status."""
    slump_mm: float | None
    status: Status
    band_mm: float
    lower_mm: float | None
    upper_mm: float | None
    trial_tolerance_mm: float
    flags: tuple[Flag, ...]


def estimate_slump_mm(effective_water_kg_m3: float, nmas_mm: float,
                       air_entrained: bool, shape: AggregateShape,
                       element: ElementType | None = None,
                       policy: Policy = 'extrapolate') -> SlumpEstimate:
    """Invert water kg/m3 to midpoint slump mm; floor negative extrapolation at 0."""
    _number(effective_water_kg_m3, 'effective_water_kg_m3')
    lookup = slump_for_water_mm(effective_water_kg_m3, nmas_mm, air_entrained, shape, policy)
    flags = list(flags_from_lookup(lookup, 'SLUMP_TABLE'))
    limits = input_validation_limits()
    band_mm = limits['slump_estimate.band_mm']
    trial_mm = limits['trial_batch.slump_tolerance_mm']
    value_mm = lookup.value
    lower_mm = upper_mm = None
    if value_mm is not None:
        if value_mm < 0:
            value_mm = 0.0
            flags.append(Flag('NEGATIVE_SLUMP_CLAMPED', 'warning', 'Negative extrapolated slump floored at 0 mm.'))
        lower_mm, upper_mm = max(0, value_mm-band_mm), value_mm+band_mm
    if element is not None:
        low, high = slump_limits_mm(element)
        if value_mm is not None and not low.value <= value_mm <= high.value:
            flags.append(Flag('SLUMP_OUTSIDE_ELEMENT_RANGE', 'warning', 'Estimated slump outside the element reference range.'))
    return SlumpEstimate(value_mm, lookup.status, band_mm, lower_mm, upper_mm, trial_mm, tuple(flags))


def slump_delta_from_water_delta_mm(water_delta_kg_m3: float) -> float:
    """Slide rule: delta slump mm = 25*delta water kg/m3 / 6; product-specific."""
    if not isinstance(water_delta_kg_m3, (int,float)):
        raise ValueError('water_delta_kg_m3 must be finite')
    _number(abs(water_delta_kg_m3), 'water_delta_kg_m3')
    limits = input_validation_limits()
    return limits['slide_rule.slump_mm'] * water_delta_kg_m3 / limits['slide_rule.per_water_kg_m3']
