"""Aggregate moisture accounting, CIE308 course and strict SSD conventions.

Masses are kg (or consistently scaled kg/m3); MC and absorption are percentages
of oven-dry mass. Free water is signed: dry aggregate absorbs mixing water.
"""
from dataclasses import dataclass

from concretecalc.flags import Flag
from concretecalc.schemas import WeightBasis, MoistureConvention
from concretecalc.validation import _choice, _number
from concretecalc.tables.lookups import input_validation_limits


def _moisture_limits(absorption_pct: float, mc_pct: float) -> None:
    limits = input_validation_limits()
    for name, value in (('absorption_pct', absorption_pct), ('mc_pct', mc_pct)):
        _number(value, name)
        if value > limits[f'hard.{name}.max']:
            raise ValueError(f'{name} exceeds hard maximum')


@dataclass(frozen=True)
class AggregateMoisture:
    """Entered and derived aggregate masses, kg, and effective moisture, %."""
    label: str
    entered_kg: float
    basis: WeightBasis
    oven_dry_kg: float
    ssd_kg: float
    effective_mc_pct: float
    free_water_kg: float
    flags: tuple[Flag, ...]


def oven_dry_mass_kg(weight_kg: float, basis: WeightBasis, absorption_pct: float, mc_pct: float) -> float:
    """Return OD kg: entered/(1+MC/100), or /(1+Abs/100) for SSD."""
    _number(weight_kg, 'weight_kg')
    _choice(basis, WeightBasis, 'basis')
    _moisture_limits(absorption_pct, mc_pct)
    if basis == 'ssd':
        return weight_kg / (1 + absorption_pct / 100)
    if basis == 'as_received':
        return weight_kg / (1 + mc_pct / 100)
    return weight_kg


def ssd_mass_kg(oven_dry_kg: float, absorption_pct: float) -> float:
    """SSD kg = OD kg * (1 + Abs/100), CIE308 moisture definition."""
    _number(oven_dry_kg, 'oven_dry_kg')
    _moisture_limits(absorption_pct, 0)
    return oven_dry_kg * (1 + absorption_pct / 100)


def free_water_kg(oven_dry_kg: float, mc_pct: float, absorption_pct: float) -> float:
    """Signed free kg = OD kg * (MC - Abs)/100; negative means absorption."""
    _number(oven_dry_kg, 'oven_dry_kg')
    _moisture_limits(absorption_pct, mc_pct)
    return oven_dry_kg * (mc_pct - absorption_pct) / 100


def aggregate_moisture(label: str, weight_kg: float, basis: WeightBasis,
                       absorption_pct: float, mc_pct: float) -> AggregateMoisture:
    """Resolve an explicit mass basis; SSD uses effective MC=Abs (A-37)."""
    dry_kg = oven_dry_mass_kg(weight_kg, basis, absorption_pct, mc_pct)
    flags: list[Flag] = []
    effective_mc_pct = mc_pct
    if basis == 'ssd':
        effective_mc_pct = absorption_pct
        if mc_pct != absorption_pct:
            flags.append(Flag('SSD_MC_MISMATCH', 'warning', f'{label}: SSD basis uses absorption as effective MC.'))
    free_kg = free_water_kg(dry_kg, effective_mc_pct, absorption_pct)
    if free_kg < 0:
        flags.append(Flag('NEGATIVE_FREE_WATER', 'warning', f'{label}: aggregate absorbs {-free_kg} kg water.'))
    return AggregateMoisture(label, weight_kg, basis, dry_kg,
        ssd_mass_kg(dry_kg, absorption_pct), effective_mc_pct, free_kg, tuple(flags))


@dataclass(frozen=True)
class WaterBreakdown:
    """Added and signed aggregate free water, kg; effective = their sum."""
    added_water_kg: float
    free_water_ca_kg: float
    free_water_fa_kg: float
    effective_water_kg: float


def effective_water(added_water_kg: float, coarse: AggregateMoisture,
                    fine: AggregateMoisture) -> WaterBreakdown:
    """Effective kg = added kg + CA free kg + FA free kg, CIE308 step 1."""
    _number(added_water_kg, 'added_water_kg')
    return WaterBreakdown(added_water_kg, coarse.free_water_kg, fine.free_water_kg,
                          added_water_kg + coarse.free_water_kg + fine.free_water_kg)


@dataclass(frozen=True)
class FieldWeights:
    """Moisture-corrected field aggregate and added-water masses, kg."""
    convention: MoistureConvention
    coarse_wet_kg: float
    fine_wet_kg: float
    water_adjusted_kg: float
    coarse_free_water_kg: float
    fine_free_water_kg: float


def field_weights_course(water_kg: float, coarse_dry_kg: float, fine_dry_kg: float,
                         coarse_mc_pct: float, coarse_absorption_pct: float,
                         fine_mc_pct: float, fine_absorption_pct: float) -> FieldWeights:
    """Course: wet=W*(1+MC/100); added=water-sum(W*(MC-Abs)/100).

    The slides apply these expressions directly to design masses (Q25). The
    parameter names retain that course convention; strict SSD is separate.
    """
    _number(water_kg, 'water_kg')
    coarse_free_kg = free_water_kg(coarse_dry_kg, coarse_mc_pct, coarse_absorption_pct)
    fine_free_kg = free_water_kg(fine_dry_kg, fine_mc_pct, fine_absorption_pct)
    return FieldWeights('course', coarse_dry_kg * (1 + coarse_mc_pct / 100),
        fine_dry_kg * (1 + fine_mc_pct / 100), water_kg - coarse_free_kg - fine_free_kg,
        coarse_free_kg, fine_free_kg)


def field_weights_strict(water_kg: float, coarse_ssd_kg: float, fine_ssd_kg: float,
                         coarse_mc_pct: float, coarse_absorption_pct: float,
                         fine_mc_pct: float, fine_absorption_pct: float) -> FieldWeights:
    """Strict: wet=SSD*(1+MC/100)/(1+Abs/100); subtract signed free kg."""
    coarse_dry_kg = oven_dry_mass_kg(coarse_ssd_kg, 'ssd', coarse_absorption_pct, coarse_mc_pct)
    fine_dry_kg = oven_dry_mass_kg(fine_ssd_kg, 'ssd', fine_absorption_pct, fine_mc_pct)
    course = field_weights_course(water_kg, coarse_dry_kg, fine_dry_kg,
        coarse_mc_pct, coarse_absorption_pct, fine_mc_pct, fine_absorption_pct)
    return FieldWeights('strict', course.coarse_wet_kg, course.fine_wet_kg,
        course.water_adjusted_kg, course.coarse_free_water_kg, course.fine_free_water_kg)
