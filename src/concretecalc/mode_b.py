"""Pure Mode B orchestration: SI batch inputs to a full research report."""
from dataclasses import dataclass, replace, asdict
from typing import Literal

from concretecalc.schemas import MixInputs, DISCLAIMER, binders
from concretecalc.flags import Flag, flags_from_lookup
from concretecalc.validation import validate_mode_b, _number
from concretecalc.moisture import AggregateMoisture, WaterBreakdown, aggregate_moisture, effective_water
from concretecalc.volumes import (VolumeCheck, UnitWeightCheck, PackingIndicators,
                                  volume_check, unit_weight_check, packing_indicators)
from concretecalc.strength import MixState, ModelConstants, StrengthPrediction
from concretecalc.strength.registry import MODEL_REGISTRY, default_constants, strength_curve_mpa
from concretecalc.strength.aci_table import predict_aci_table
from concretecalc.strength.age import AgeAdjusted, strength_at_age_mpa
from concretecalc.required_strength import CharacteristicEstimate, estimated_characteristic_strength_mpa
from concretecalc.slump import SlumpEstimate, estimate_slump_mm
from concretecalc.tables.interpolate import Policy
from concretecalc.tables.lookups import air_content_pct, input_validation_limits, strength_table_points


@dataclass(frozen=True)
class StrengthPlotData:
    """w/c versus 28-day research mean MPa, suitable for any renderer."""
    aci_non_ae_points: tuple[tuple[float, float], ...]
    aci_ae_points: tuple[tuple[float, float], ...]
    model_curves: dict[str, tuple[tuple[float, float | None], ...]]
    mix_point_wc: float
    mix_point_strengths_mpa: dict[str, float | None]


@dataclass(frozen=True)
class StrengthReport:
    """Complete Mode B research report, masses normalised to kg/m3."""
    inputs: MixInputs
    per_m3_scale: float
    cement_kg_m3: float
    water_added_kg_m3: float
    coarse_entered_kg_m3: float
    fine_entered_kg_m3: float
    coarse: AggregateMoisture
    fine: AggregateMoisture
    water: WaterBreakdown
    wc: float
    wcm: float
    air_pct: float
    air_source: Literal['aci_table', 'user']
    volumes: VolumeCheck
    unit_weight: UnitWeightCheck
    indicators: PackingIndicators
    predictions: dict[str, StrengthPrediction]
    age_adjusted: dict[str, AgeAdjusted | None]
    characteristic: dict[str, CharacteristicEstimate | None]
    slump: SlumpEstimate
    air_entrainer_dosage_ml_m3: float | None
    cube_equivalent_mpa: dict[str, float | None]
    flags: tuple[Flag, ...]
    plot: StrengthPlotData
    disclaimer: str


def run_mode_b(inputs: MixInputs, constants: dict[str, ModelConstants] | None = None,
               policy: Policy = 'extrapolate', normalise_age_to_28d: bool = False,
               model_spread_threshold_mpa: float = 5.0) -> StrengthReport:
    """Normalise kg to per-m3; run physical and prediction steps without I/O."""
    flags = list(validate_mode_b(inputs))
    _number(model_spread_threshold_mpa, 'model_spread_threshold_mpa')
    if policy not in ('clamp', 'raise', 'extrapolate'):
        raise ValueError('Unknown policy')
    supplied = {} if constants is None else constants
    if set(supplied) - set(MODEL_REGISTRY):
        raise ValueError('Unknown model in constants')
    scale = 1 / inputs.batch_volume_m3 if inputs.batch_volume_m3 is not None else 1.0
    normalized_binders = tuple(replace(binder, weight_kg=binder.weight_kg*scale) for binder in binders(inputs))
    cement_kg_m3 = normalized_binders[0].weight_kg
    water_added_kg_m3 = inputs.water_kg*scale
    coarse_kg_m3, fine_kg_m3 = inputs.coarse_kg*scale, inputs.fine_kg*scale
    coarse = aggregate_moisture('CA', coarse_kg_m3, inputs.aggregate_weight_basis,
                              inputs.coarse.absorption_pct, inputs.coarse.mc_pct)
    fine = aggregate_moisture('FA', fine_kg_m3, inputs.aggregate_weight_basis,
                            inputs.fine.absorption_pct, inputs.fine.mc_pct)
    flags.extend(coarse.flags + fine.flags)
    water = effective_water(water_added_kg_m3, coarse, fine)
    _number(water.effective_water_kg, 'effective_water_kg_m3', strict=True)
    wc = water.effective_water_kg / cement_kg_m3
    binder_kg_m3 = sum(binder.weight_kg for binder in normalized_binders)
    wcm = water.effective_water_kg / binder_kg_m3
    air_pct = inputs.air_pct
    air_source: Literal['aci_table', 'user'] = 'user'
    if air_pct is None:
        lookup = air_content_pct(inputs.nmas_mm, inputs.exposure, inputs.air_entrained, policy)
        flags.extend(flags_from_lookup(lookup, 'AIR_TABLE'))
        if lookup.value is None:
            raise ValueError('Air table unavailable; provide air_pct')
        air_pct, air_source = lookup.value, 'aci_table'
    volumes = volume_check(normalized_binders, water.effective_water_kg,
        coarse.ssd_kg, inputs.coarse.sg_ssd, fine.ssd_kg, inputs.fine.sg_ssd, air_pct)
    density = unit_weight_check(normalized_binders, water.effective_water_kg,
        coarse.ssd_kg, fine.ssd_kg, inputs.nmas_mm, inputs.air_entrained, policy)
    indicators = packing_indicators(coarse.oven_dry_kg, coarse.ssd_kg, inputs.coarse,
        fine.ssd_kg, inputs.fine, inputs.nmas_mm, volumes, policy)
    flags.extend(volumes.flags + density.flags + indicators.flags)
    state = MixState(cement_kg_m3, binder_kg_m3, water.effective_water_kg, wc, wcm,
        air_pct, inputs.air_entrained, volumes.cement_m3, volumes.water_m3,
        volumes.air_m3, inputs.cement_type, inputs.curing, inputs.age_days)
    predictions: dict[str, StrengthPrediction] = {}
    ages: dict[str, AgeAdjusted | None] = {}
    characteristic: dict[str, CharacteristicEstimate | None] = {}
    cubes: dict[str, float | None] = {}
    curves: dict[str, tuple[tuple[float, float | None], ...]] = {}
    limits = input_validation_limits()
    low, high = limits['strength_model.wc_min'], limits['strength_model.wc_max']
    wc_values = tuple(low + (high-low)*i/60 for i in range(61))
    for name, model in MODEL_REGISTRY.items():
        parameters = supplied[name] if name in supplied else default_constants(name, inputs.air_entrained)
        result = predict_aci_table(state, parameters, policy) if name == 'aci_table' else model(state, parameters)
        predictions[name] = result
        flags.extend(result.flags)
        value = result.mean_28d_mpa
        ages[name] = None
        characteristic[name] = None
        cubes[name] = None
        if value is not None and value > 0:
            age = strength_at_age_mpa(value, inputs.age_days, inputs.cement_type, inputs.curing, normalise_age_to_28d)
            ages[name] = age
            flags.extend(age.flags)
            if inputs.sigma_mpa is not None or inputs.n_samples is not None:
                characteristic[name] = estimated_characteristic_strength_mpa(value, inputs.sigma_mpa, inputs.n_samples)
                flags.extend(characteristic[name].flags)
            if inputs.specimen == 'cube_150' and inputs.cube_to_cylinder_factor is not None:
                cubes[name] = value / inputs.cube_to_cylinder_factor
        curves[name] = tuple(zip(wc_values, strength_curve_mpa(name, wc_values, state, parameters)))
    if not limits['aci_table.basis_nmas_min_mm'] <= inputs.nmas_mm <= limits['aci_table.basis_nmas_max_mm']:
        flags.append(Flag('ACI_TABLE_NMAS_BASIS', 'info', 'Strength table basis is 19-25 mm NMAS; applied unchanged at entered size.'))
    available = [p.mean_28d_mpa for p in predictions.values() if p.mean_28d_mpa is not None]
    if available and max(available)-min(available) > model_spread_threshold_mpa:
        flags.append(Flag('MODEL_SPREAD', 'warning', 'Research models disagree beyond the selected MPa threshold.'))
    slump = estimate_slump_mm(water.effective_water_kg, inputs.nmas_mm,
        inputs.air_entrained, inputs.coarse.shape, inputs.element, policy)
    flags.extend(slump.flags)
    if inputs.admixtures.water_reducer_pct is not None or inputs.admixtures.superplasticizer_kg is not None:
        flags.append(Flag('SLUMP_IGNORES_ADMIXTURES', 'warning', 'Slump estimate ignores admixture effects.'))
    dosage = None
    if inputs.air_entrained:
        rate = inputs.admixtures.air_entrainer_ml_per_pct_per_100kg
        if rate is None:
            rate = limits['slide_rule.air_entrainer_ml_per_pct_per_100kg']
        dosage = rate*air_pct*cement_kg_m3/100
        flags.append(Flag('AIR_ENTRAINER_PRODUCT_SPECIFIC', 'warning', 'Air-entrainer dosage is product-specific; default rate is a slide value.'))
    plot = StrengthPlotData(strength_table_points(False), strength_table_points(True), curves, wc,
        {name: p.mean_28d_mpa for name,p in predictions.items()})
    return StrengthReport(inputs, scale, cement_kg_m3, water_added_kg_m3, coarse_kg_m3,
        fine_kg_m3, coarse, fine, water, wc, wcm, air_pct, air_source, volumes,
        density, indicators, predictions, ages, characteristic, slump, dosage,
        cubes, tuple(flags), plot, DISCLAIMER)


def report_to_dict(report: StrengthReport) -> dict:
    """Return a recursively copied, JSON-serialisable report with SI field names."""
    return asdict(report)
