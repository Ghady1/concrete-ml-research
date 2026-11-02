"""Shared pure strength-model inputs and outputs (SI, PLAN M09)."""
from dataclasses import dataclass
from typing import Callable
import math

from concretecalc.schemas import CementType, Curing, DISCLAIMER
from concretecalc.flags import Flag
from concretecalc.tables.models import Status
from concretecalc.tables.lookups import input_validation_limits


@dataclass(frozen=True)
class MixState:
    """Per-m3 state: kg/m3, dimensionless ratios, percent air, m3 volumes, days."""
    cement_kg_m3: float
    binder_kg_m3: float
    effective_water_kg_m3: float
    wc: float
    wcm: float
    air_pct: float
    air_entrained: bool
    cement_volume_m3: float
    water_volume_m3: float
    air_volume_m3: float
    cement_type: CementType
    curing: Curing
    age_days: float


@dataclass(frozen=True)
class ModelConstants:
    """Calibratable parameters with explicit provenance and age basis."""
    model_name: str
    preset: str
    values: dict[str, float]
    source: str
    calibrated: bool
    air_entrained: bool | None
    age_basis_days: float
    material_set_id: str | None = None


@dataclass(frozen=True)
class StrengthPrediction:
    """Research mean at 28 days, MPa, retaining all parameters and warnings."""
    model_name: str
    mean_28d_mpa: float | None
    status: Status
    warnings: tuple[str, ...]
    flags: tuple[Flag, ...]
    constants_used: dict[str, float]
    constants_source: str
    calibrated: bool
    disclaimer: str = DISCLAIMER


StrengthModel = Callable[[MixState, ModelConstants], StrengthPrediction]


def check_model_inputs(mix: MixState, constants: ModelConstants, name: str) -> None:
    """Reject mismatched parameter sets, invalid ratios and non-28-day presets."""
    if constants.model_name != name:
        raise ValueError(f'constants.model_name must be {name}')
    if constants.age_basis_days != 28:
        raise ValueError('Only 28-day constants may produce a 28-day mean; 7-day presets are stored only.')
    if constants.air_entrained is not None and constants.air_entrained != mix.air_entrained:
        raise ValueError('constants.air_entrained does not match the mix')
    if not math.isfinite(mix.wc) or mix.wc <= 0:
        raise ValueError('wc must be finite and positive')
    for key, value in constants.values.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'constants.{key} must be finite and positive')


def prediction(name: str, value_mpa: float | None, mix: MixState,
               constants: ModelConstants, status: Status = Status.OK,
               warnings: tuple[str, ...] = ()) -> StrengthPrediction:
    """Attach shared research applicability flags without changing the value."""
    limits = input_validation_limits()
    flags: list[Flag] = []
    if not constants.calibrated:
        flags.append(Flag('UNCALIBRATED_MODEL', 'warning', f'{name}: provisional parameters; not calibrated to these materials.'))
    if constants.preset.startswith('lit_'):
        flags.append(Flag('UNVERIFIED_LITERATURE_PRESET', 'warning', 'Literature alternative has unresolved primary-source verification.'))
    if not limits['strength_model.wc_min'] <= mix.wc <= limits['strength_model.wc_max']:
        flags.append(Flag('WC_MODEL_RANGE', 'warning', f'{name}: w/c outside research model range.'))
    if mix.wc < limits['strength_model.wc_min']:
        flags.append(Flag('HYDRATION_LIMIT', 'warning', 'Low w/c may prevent full hydration.'))
    # The table's strength bounds are supplied through the lookup layer.
    if value_mpa is not None and not limits['strength.table_min_mpa'] <= value_mpa <= limits['strength.table_max_mpa']:
        flags.append(Flag('STRENGTH_TABLE_RANGE', 'warning', f'{name}: estimated mean outside reference strength range.'))
    if value_mpa is not None and (not math.isfinite(value_mpa) or value_mpa <= 0):
        flags.append(Flag('UNPHYSICAL_STRENGTH', 'error', f'{name}: extrapolation gives a nonpositive or nonfinite strength.'))
    for message in warnings:
        flags.append(Flag('STRENGTH_LOOKUP', 'error' if status == Status.UNAVAILABLE else 'warning', message))
    return StrengthPrediction(name, value_mpa, status, warnings, tuple(flags),
        dict(constants.values), constants.source, constants.calibrated)
