"""Hard input checks and soft applicability flags (PLAN M5, JSON limits).

Mass limits are evaluated per m3 after batch normalisation. This module does
not alter inputs or attempt to repair physically impossible values.
"""
import math
from dataclasses import fields, is_dataclass
from typing import get_args

from concretecalc.flags import Flag
from concretecalc import schemas as s
from concretecalc.tables.lookups import is_standard_nmas, input_validation_limits


def _finite_tree(value: object, path: str) -> None:
    if is_dataclass(value):
        for field in fields(value):
            _finite_tree(getattr(value, field.name), f"{path}.{field.name}")
    elif isinstance(value, tuple):
        for i, item in enumerate(value):
            _finite_tree(item, f"{path}[{i}]")
    elif isinstance(value, (int, float)) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")


def _number(value: float, name: str, minimum: float = 0, strict: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < minimum or (strict and value == minimum):
        raise ValueError(f"{name} must be {'greater than' if strict else 'at least'} {minimum}")


def _choice(value: str, alias: object, name: str) -> None:
    if value not in get_args(alias):
        raise ValueError(f"{name} must be one of {get_args(alias)}")


def _soft(value: float, key: str, code: str, flags: list[Flag]) -> None:
    limits = input_validation_limits()
    low, high = limits[f'soft.{key}.min'], limits[f'soft.{key}.max']
    if not low <= value <= high:
        flags.append(Flag(code, 'warning', f'{key}={value} outside research range [{low}, {high}]'))


def _common(inputs: s.MixInputs | s.ModeAInputs) -> list[Flag]:
    _finite_tree(inputs, 'inputs')
    flags: list[Flag] = []
    _choice(inputs.exposure, s.Exposure, 'exposure')
    _choice(inputs.cement_type, s.CementType, 'cement_type')
    _choice(inputs.curing, s.Curing, 'curing')
    if type(inputs.air_entrained) is not bool:
        raise ValueError('air_entrained must be bool')
    if inputs.element is not None:
        _choice(inputs.element, s.ElementType, 'element')
    if inputs.batch_volume_m3 is not None:
        _number(inputs.batch_volume_m3, 'batch_volume_m3', strict=True)
    if inputs.sigma_mpa is not None:
        _number(inputs.sigma_mpa, 'sigma_mpa')
    if inputs.n_samples is not None:
        if type(inputs.n_samples) is not int or inputs.n_samples < 1:
            raise ValueError('n_samples must be an integer >= 1')
    if inputs.nmas_mm is not None:
        _number(inputs.nmas_mm, 'nmas_mm', strict=True)
        if not is_standard_nmas(inputs.nmas_mm):
            flags.append(Flag('NONSTANDARD_NMAS', 'warning', 'nmas_mm is off a standard sieve node; interpolation applies.'))
    limits = input_validation_limits()
    for name, aggregate in (('coarse', inputs.coarse), ('fine', inputs.fine)):
        _number(aggregate.sg_ssd, f'{name}.sg_ssd', strict=True)
        _soft(aggregate.sg_ssd, f'{name}_sg_ssd', f'SOFT_LIMIT_{name.upper()}_SG', flags)
        for field in ('absorption_pct', 'mc_pct'):
            value = getattr(aggregate, field)
            _number(value, f'{name}.{field}')
            if value > limits[f'hard.{field}.max']:
                raise ValueError(f'{name}.{field} exceeds hard maximum')
            _soft(value, f'{name}_{field}', f'SOFT_LIMIT_{name.upper()}_{field.upper()}', flags)
    _number(inputs.coarse.drd_kg_m3, 'coarse.drd_kg_m3', strict=True)
    _soft(inputs.coarse.drd_kg_m3, 'coarse_drd_kg_m3', 'SOFT_LIMIT_COARSE_DRD', flags)
    _choice(inputs.coarse.shape, s.AggregateShape, 'coarse.shape')
    _number(inputs.fine.fm, 'fine.fm', strict=True)
    _soft(inputs.fine.fm, 'fine_fm', 'SOFT_LIMIT_FINE_FM', flags)
    if not limits['fm.table_min'] <= inputs.fine.fm <= limits['fm.table_max']:
        flags.append(Flag('FM_EXTRAPOLATION', 'warning', 'fine.fm outside b/b0 table range [2.4, 3.0].'))
    if inputs.cement_type in ('II', 'IV', 'V'):
        flags.append(Flag('CEMENT_TYPE_APPROXIMATION', 'warning', 'Type I age coefficients will approximate this cement type.'))
    return flags


def validate_mode_b(inputs: s.MixInputs) -> tuple[Flag, ...]:
    """Raise on invalid Mode B inputs; return research applicability flags."""
    flags = _common(inputs)
    _choice(inputs.aggregate_weight_basis, s.WeightBasis, 'aggregate_weight_basis')
    _choice(inputs.specimen, s.Specimen, 'specimen')
    _number(inputs.nmas_mm, 'nmas_mm', strict=True)
    volume_m3 = inputs.batch_volume_m3 if inputs.batch_volume_m3 is not None else 1.0
    for field in ('water_kg', 'coarse_kg', 'fine_kg'):
        _number(getattr(inputs, field), field, strict=True)
    for i, binder in enumerate(s.binders(inputs)):
        name = 'cement' if i == 0 else f'scm[{i-1}]'
        _number(binder.weight_kg, f'{name}.weight_kg', strict=True)
        _number(binder.sg, f'{name}.sg', strict=True)
        expected = 'cement' if i == 0 else 'scm'
        if binder.kind != expected:
            raise ValueError(f'{name}.kind must be {expected}')
    _soft(inputs.cement.weight_kg / volume_m3, 'cement_kg_m3', 'SOFT_LIMIT_CEMENT', flags)
    _soft(inputs.cement.sg, 'cement_sg', 'SOFT_LIMIT_CEMENT_SG', flags)
    _soft(inputs.water_kg / volume_m3, 'water_kg_m3', 'SOFT_LIMIT_WATER', flags)
    limits = input_validation_limits()
    _number(inputs.age_days, 'age_days', limits['hard.age_days.min'])
    _soft(inputs.age_days, 'age_days', 'SOFT_LIMIT_AGE', flags)
    if inputs.air_pct is not None:
        _number(inputs.air_pct, 'air_pct')
        if inputs.air_pct >= 100:
            raise ValueError('air_pct must be less than 100')
        _soft(inputs.air_pct, 'air_pct', 'SOFT_LIMIT_AIR', flags)
    if inputs.cube_to_cylinder_factor is not None:
        _number(inputs.cube_to_cylinder_factor, 'cube_to_cylinder_factor', strict=True)
    if inputs.specimen == 'cube_150' and inputs.cube_to_cylinder_factor is None:
        flags.append(Flag('CUBE_FACTOR_MISSING', 'warning', 'Cube equivalent unavailable without a user conversion factor.'))
    if inputs.scm:
        flags.append(Flag('SCM_NOT_SUPPORTED', 'warning', 'SCM volumes are included; strength effects are not modeled.'))
    if inputs.aggregate_weight_basis == 'ssd':
        for name, aggregate in (('coarse', inputs.coarse), ('fine', inputs.fine)):
            if aggregate.mc_pct != aggregate.absorption_pct:
                flags.append(Flag(f'SSD_MC_MISMATCH_{name.upper()}', 'warning', f'{name}: SSD basis uses absorption as effective moisture.'))
    for field in ('air_entrainer_ml_per_pct_per_100kg', 'superplasticizer_kg'):
        value = getattr(inputs.admixtures, field)
        if value is not None:
            _number(value, f'admixtures.{field}')
    if inputs.admixtures.superplasticizer_kg is not None:
        flags.append(Flag('SUPERPLASTICIZER_NOT_MODELED', 'warning', 'Superplasticizer effect is not modeled.'))
    _water_reducer(inputs.admixtures.water_reducer_pct)
    if inputs.admixtures.water_reducer_pct is not None:
        flags.append(Flag('WATER_REDUCER_NOT_MODELED', 'warning', 'Mode B uses entered water; reducer percentage is not applied again.'))
    return tuple(flags)


def _water_reducer(value: float | None) -> None:
    if value is not None:
        _number(value, 'water_reducer_pct')
        if value >= 100:
            raise ValueError('water_reducer_pct must be less than 100')


def validate_mode_a(inputs: s.ModeAInputs) -> tuple[Flag, ...]:
    """Check Mode A targets, aggregate properties and size-selection geometry."""
    flags = _common(inputs)
    _choice(inputs.element, s.ElementType, 'element')
    _choice(inputs.durability_class, s.DurabilityClass, 'durability_class')
    _choice(inputs.moisture_convention, s.MoistureConvention, 'moisture_convention')
    _number(inputs.specified_fc_mpa, 'specified_fc_mpa', strict=True)
    _number(inputs.cement_sg, 'cement_sg', strict=True)
    _number(inputs.batch_volume_m3, 'batch_volume_m3', strict=True)
    _soft(inputs.cement_sg, 'cement_sg', 'SOFT_LIMIT_CEMENT_SG', flags)
    _number(inputs.bb0_adjustment_factor, 'bb0_adjustment_factor', strict=True)
    _soft(inputs.bb0_adjustment_factor, 'bb0_adjustment', 'SOFT_LIMIT_BB0_ADJUSTMENT', flags)
    geometry = ('form_min_dimension_mm', 'rebar_clear_spacing_mm', 'cover_mm', 'slab_thickness_mm')
    if inputs.nmas_mm is None and all(getattr(inputs, field) is None for field in geometry):
        raise ValueError('nmas_mm or at least one geometry dimension is required')
    for field in geometry:
        value = getattr(inputs, field)
        if value is not None:
            _number(value, field, strict=True)
    if inputs.slump_target_mm is not None:
        _number(inputs.slump_target_mm, 'slump_target_mm')
    _water_reducer(inputs.water_reducer_pct)
    for field in ('hand_consolidated', 'underwater', 'flatwork'):
        if type(getattr(inputs, field)) is not bool:
            raise ValueError(f'{field} must be bool')
    return tuple(flags)
