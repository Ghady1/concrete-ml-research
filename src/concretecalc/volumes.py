"""Absolute volumes and packing indicators, CIE308 / ACI 211.1 (PLAN M07).

Inputs are per m3. Aggregate mass and specific gravity both use SSD basis;
dry-rodded packing instead uses OD mass and OD specific gravity (A-09).
"""
from dataclasses import dataclass

from concretecalc.flags import Flag, flags_from_lookup
from concretecalc.schemas import Binder, CoarseAggregateProperties, FineAggregateProperties
from concretecalc.tables.interpolate import Policy
from concretecalc.tables.lookups import (bulk_volume_ratio, fresh_unit_weight_kg_m3,
                                         input_validation_limits)
from concretecalc.tables.models import Status
from concretecalc.validation import _number


def absolute_volume_m3(mass_kg: float, sg: float) -> float:
    """Absolute m3 = kg/(specific gravity*1000 kg/m3), water reference."""
    _number(mass_kg, 'mass_kg')
    _number(sg, 'sg', strict=True)
    return mass_kg / (sg * 1000)


@dataclass(frozen=True)
class VolumeCheck:
    """Per-m3 component volumes and signed closure error, all m3; air in %."""
    cement_m3: float
    scm_m3: float
    water_m3: float
    coarse_m3: float
    fine_m3: float
    air_m3: float
    total_m3: float
    closure_error_m3: float
    implied_air_pct: float
    flags: tuple[Flag, ...]


def volume_check(binders: tuple[Binder, ...], effective_water_kg: float,
                 coarse_ssd_kg: float, coarse_sg_ssd: float, fine_ssd_kg: float,
                 fine_sg_ssd: float, air_pct: float) -> VolumeCheck:
    """Sum W/(SG*1000) and air/100; closure=sum-1; implied air from solids."""
    cement_m3 = 0.0
    scm_m3 = 0.0
    for binder in binders:
        volume_m3 = absolute_volume_m3(binder.weight_kg, binder.sg)
        if binder.kind == 'cement':
            cement_m3 += volume_m3
        elif binder.kind == 'scm':
            scm_m3 += volume_m3
        else:
            raise ValueError('binder.kind must be cement or scm')
    _number(air_pct, 'air_pct')
    if air_pct >= 100:
        raise ValueError('air_pct must be less than 100')
    water_m3 = absolute_volume_m3(effective_water_kg, 1)
    coarse_m3 = absolute_volume_m3(coarse_ssd_kg, coarse_sg_ssd)
    fine_m3 = absolute_volume_m3(fine_ssd_kg, fine_sg_ssd)
    air_m3 = air_pct / 100
    solids_water_m3 = cement_m3 + scm_m3 + water_m3 + coarse_m3 + fine_m3
    total_m3 = solids_water_m3 + air_m3
    limits = input_validation_limits()
    flags: list[Flag] = []
    # Compare totals to bounds directly: subtracting 1 first magnifies floating
    # cancellation at exactly the declared 0.02/0.05 m3 boundaries.
    for level in ('error', 'warning'):
        limit_m3 = limits[f'volume_closure.{level}_m3']
        if total_m3 > 1 + limit_m3 or total_m3 < 1 - limit_m3:
            flags.append(Flag('VOLUME_CLOSURE', level,
                f'Absolute volume closure error {total_m3 - 1} m3 exceeds {limit_m3} m3.'))
            break
    return VolumeCheck(cement_m3, scm_m3, water_m3, coarse_m3, fine_m3,
        air_m3, total_m3, total_m3 - 1, (1 - solids_water_m3) * 100, tuple(flags))


@dataclass(frozen=True)
class UnitWeightCheck:
    """Mass sum per m3 and reference density comparison (%)."""
    computed_kg_m3: float
    aci_kg_m3: float | None
    deviation_pct: float | None
    status: Status
    flags: tuple[Flag, ...]


def unit_weight_check(binders: tuple[Binder, ...], effective_water_kg: float,
                      coarse_ssd_kg: float, fine_ssd_kg: float, nmas_mm: float,
                      air_entrained: bool, policy: Policy = 'clamp') -> UnitWeightCheck:
    """Computed density=sum constituent kg/m3; deviation=100*(sum-ACI)/ACI."""
    masses = [binder.weight_kg for binder in binders]
    masses.extend((effective_water_kg, coarse_ssd_kg, fine_ssd_kg))
    for mass_kg in masses:
        _number(mass_kg, 'mass_kg')
    computed_kg_m3 = sum(masses)
    lookup = fresh_unit_weight_kg_m3(nmas_mm, air_entrained, policy)
    flags = list(flags_from_lookup(lookup, 'UNIT_WEIGHT_TABLE'))
    deviation_pct = None
    if lookup.value is not None:
        deviation_pct = 100 * (computed_kg_m3 - lookup.value) / lookup.value
        if abs(deviation_pct) > input_validation_limits()['unit_weight.deviation_pct']:
            flags.append(Flag('UNIT_WEIGHT_DEVIATION', 'warning', f'Computed unit weight differs from ACI by {deviation_pct}%.'))
    return UnitWeightCheck(computed_kg_m3, lookup.value, deviation_pct, lookup.status, tuple(flags))


@dataclass(frozen=True)
class PackingIndicators:
    """Dimensionless void/bulk/fine ratios and paste volume m3 per m3."""
    coarse_void_content: float
    coarse_bulk_ratio_actual: float
    coarse_bulk_ratio_table: float | None
    coarse_bulk_ratio_deviation_pct: float | None
    paste_volume_m3: float
    fine_fraction_by_mass: float
    fine_fraction_by_volume: float
    flags: tuple[Flag, ...]


def packing_indicators(coarse_dry_kg: float, coarse_ssd_kg: float,
                        coarse: CoarseAggregateProperties, fine_ssd_kg: float,
                        fine: FineAggregateProperties, nmas_mm: float,
                        volumes: VolumeCheck, policy: Policy = 'extrapolate') -> PackingIndicators:
    """OD void=1-DRD/(SG_OD*1000); actual bulk=OD/DRD (A-09)."""
    _number(coarse_dry_kg, 'coarse_dry_kg')
    _number(coarse.drd_kg_m3, 'coarse.drd_kg_m3', strict=True)
    _number(coarse.sg_ssd, 'coarse.sg_ssd', strict=True)
    _number(coarse.absorption_pct, 'coarse.absorption_pct')
    sg_od = coarse.sg_ssd / (1 + coarse.absorption_pct / 100)
    void_content = 1 - coarse.drd_kg_m3 / (sg_od * 1000)
    actual = coarse_dry_kg / coarse.drd_kg_m3
    lookup = bulk_volume_ratio(nmas_mm, fine.fm, policy)
    flags = list(flags_from_lookup(lookup, 'BULK_RATIO_TABLE'))
    deviation_pct = None
    if lookup.value is not None:
        if lookup.value <= 0:
            flags.append(Flag('BULK_RATIO_UNPHYSICAL', 'error', 'Extrapolated bulk ratio is nonpositive.'))
        else:
            deviation_pct = 100 * (actual - lookup.value) / lookup.value
            if abs(deviation_pct) > input_validation_limits()['bulk_ratio.deviation_pct']:
                flags.append(Flag('BULK_RATIO_DEVIATION', 'warning', f'Actual b/b0 differs from table by {deviation_pct}%.'))
    if not 0 <= void_content < 1:
        flags.append(Flag('COARSE_VOID_UNPHYSICAL', 'error', 'Dry-rodded void fraction is outside [0, 1).'))
    coarse_m3 = absolute_volume_m3(coarse_ssd_kg, coarse.sg_ssd)
    fine_m3 = absolute_volume_m3(fine_ssd_kg, fine.sg_ssd)
    _number(coarse_ssd_kg + fine_ssd_kg, 'aggregate_mass_kg', strict=True)
    return PackingIndicators(void_content, actual, lookup.value, deviation_pct,
        volumes.cement_m3 + volumes.scm_m3 + volumes.water_m3 + volumes.air_m3,
        fine_ssd_kg / (fine_ssd_kg + coarse_ssd_kg), fine_m3 / (fine_m3 + coarse_m3), tuple(flags))
