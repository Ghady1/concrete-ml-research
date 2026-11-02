"""ACI 211.1 course Mode A, ten explicit SI steps (task section 7).

The course and strict SSD field corrections are both reported. This workflow
preserves unresolved course assumptions; it does not certify a structural design.
"""
from dataclasses import dataclass
from typing import Literal
from concretecalc.schemas import (ModeAInputs, MixInputs, Binder, ElementType,
    Exposure, AggregateShape, DurabilityClass, MoistureConvention,
    CoarseAggregateProperties, FineAggregateProperties, DISCLAIMER)
from concretecalc.flags import Flag, flags_from_lookup
from concretecalc.validation import validate_mode_a, _number, _choice
from concretecalc.moisture import FieldWeights, field_weights_course, field_weights_strict
from concretecalc.required_strength import RequiredStrength, required_average_strength_mpa
from concretecalc.tables import lookups as t
from concretecalc.tables.interpolate import Policy
from concretecalc.tables.models import Lookup
from concretecalc.volumes import absolute_volume_m3


@dataclass(frozen=True)
class SlumpStep:
    min_mm: float
    max_mm: float
    target_mm: float
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class NmasStep:
    limits_mm: dict[str, float]
    governing_limit: str | None
    limit_mm: float | None
    max_size_mm: float
    nmas_mm: float
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class WaterAirStep:
    water_table_kg_m3: float
    water_reduction_kg_m3: float
    water_kg_m3: float
    air_pct: float
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class WcStep:
    fcr: RequiredStrength
    wc_strength: float
    wc_durability: float | None
    wc: float
    governing: Literal['strength', 'durability']
    wc_specified_table: float | None
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class CementStep:
    cement_from_wc_kg_m3: float
    minimum_kg_m3: float | None
    minimum_reason: str | None
    cement_kg_m3: float
    wc_final: float
    governing: Literal['strength', 'durability', 'min_cement']
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class CoarseStep:
    bb0_table: float
    bb0_used: float
    coarse_dry_kg_m3: float
    coarse_ssd_kg_m3: float
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class FineStep:
    volumes_m3: dict[str, float]
    fine_volume_m3: float
    fine_ssd_kg_m3: float
    unit_weight_kg_m3: float
    fine_weight_method_kg_m3: float
    method_difference_kg_m3: float
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class Proportions:
    cement: float
    fine: float
    coarse: float
    water: float


@dataclass(frozen=True)
class BatchWeights:
    batch_volume_m3: float
    cement_kg: float
    water_kg: float
    coarse_kg: float
    fine_kg: float
    trial_batch_guidance: tuple[str, ...]


@dataclass(frozen=True)
class MixDesignReport:
    inputs: ModeAInputs
    slump: SlumpStep
    nmas: NmasStep
    water_air: WaterAirStep
    wc: WcStep
    cement: CementStep
    coarse: CoarseStep
    fine: FineStep
    field: FieldWeights
    field_other_convention: FieldWeights
    proportions: Proportions
    batch: BatchWeights
    governing_constraint: str
    flags: tuple[Flag, ...]
    disclaimer: str


def _value(lookup: Lookup, name: str, flags: list[Flag]) -> float:
    flags.extend(flags_from_lookup(lookup, name.upper()))
    if lookup.value is None or lookup.value <= 0:
        raise ValueError(f'{name} unavailable or nonpositive; cannot continue design')
    return lookup.value


def step1_slump(element: ElementType, slump_target_mm: float | None, hand_consolidated: bool) -> SlumpStep:
    """Element min/max mm; optional hand-consolidated mass-concrete allowance."""
    low, high = t.slump_limits_mm(element)
    maximum_mm = high.value
    if element == 'mass_concrete' and hand_consolidated:
        maximum_mm += t.mode_a_rules()['hand_consolidation_extra_mm']
    target_mm = maximum_mm if slump_target_mm is None else slump_target_mm
    _number(target_mm, 'slump_target_mm')
    flags: tuple[Flag, ...] = ()
    if not low.value <= target_mm <= maximum_mm:
        flags = (Flag('SLUMP_TARGET_OUTSIDE_RANGE','warning','User slump target outside element reference range.'),)
    return SlumpStep(low.value, maximum_mm, target_mm, flags)


def step2_nmas(form_min_dimension_mm: float | None, rebar_clear_spacing_mm: float | None,
               cover_mm: float | None, slab_thickness_mm: float | None,
               nmas_override_mm: float | None) -> NmasStep:
    """Smallest geometric size limit -> largest permitted sieve -> one smaller."""
    limits: dict[str, float] = {}
    rules = t.mode_a_rules()
    dimensions = {'form':form_min_dimension_mm,'rebar_spacing':rebar_clear_spacing_mm,
                  'cover':cover_mm,'slab':slab_thickness_mm}
    for name, value_mm in dimensions.items():
        if value_mm is not None:
            _number(value_mm, name+'_mm', strict=True)
            limits[name] = value_mm*rules['geometry.'+name+'_factor']
    sieves = t.standard_sieves_mm()
    if nmas_override_mm is not None:
        _number(nmas_override_mm,'nmas_override_mm',strict=True)
        flags = () if t.is_standard_nmas(nmas_override_mm) else (Flag('NONSTANDARD_NMAS','warning','User-specified off-node NMAS.'),)
        return NmasStep(limits,None,None,nmas_override_mm,nmas_override_mm,flags)
    if not limits:
        raise ValueError('Geometry or nmas_override_mm required')
    governing = min(limits, key=limits.get)
    limit_mm = limits[governing]
    permitted = [size for size in sieves if size <= limit_mm]
    if not permitted:
        return NmasStep(limits,governing,limit_mm,sieves[0],sieves[0],
            (Flag('NMAS_BELOW_TABLE','error','Geometry limit below smallest supported sieve; fallback is not a valid design.'),))
    maximum_mm = permitted[-1]
    index = sieves.index(maximum_mm)
    flags = ()
    if index == 0:
        flags = (Flag('NMAS_SMALLEST_SIEVE','warning','No smaller supported sieve; NMAS equals smallest sieve.'),)
    return NmasStep(limits,governing,limit_mm,maximum_mm,sieves[max(0,index-1)],flags)


def _water_air(slump_mm: float, nmas_mm: float, air_entrained: bool, exposure: Exposure,
               shape: AggregateShape, water_reducer_pct: float | None, policy: Policy) -> WaterAirStep:
    flags: list[Flag] = []
    lookup = t.mixing_water_kg_m3(slump_mm,nmas_mm,air_entrained,shape,policy,slump_lookup='band')
    water_table = _value(lookup,'mixing_water',flags)
    air = t.air_content_pct(nmas_mm,exposure,air_entrained,policy)
    flags.extend(flags_from_lookup(air,'AIR_TABLE'))
    if air.value is None:
        raise ValueError('Air content unavailable')
    reduction = 0.0
    if water_reducer_pct is not None:
        _number(water_reducer_pct,'water_reducer_pct')
        if water_reducer_pct >= 100:
            raise ValueError('water_reducer_pct must be <100')
        reduction = water_table*water_reducer_pct/100
    return WaterAirStep(water_table,reduction,water_table-reduction,air.value,tuple(flags))


def step3_water_air(slump_mm: float, nmas_mm: float, air_entrained: bool, exposure: Exposure,
                     shape: AggregateShape, water_reducer_pct: float | None) -> WaterAirStep:
    """Band water kg/m3 minus optional reduction; lookup air percent (approved D-2)."""
    return _water_air(slump_mm,nmas_mm,air_entrained,exposure,shape,water_reducer_pct,'clamp')


def _wc(fc_mpa: float, sigma_mpa: float | None, n_samples: int | None,
         ae: bool, durability: DurabilityClass, policy: Policy) -> WcStep:
    required = required_average_strength_mpa(fc_mpa,sigma_mpa,n_samples)
    flags = list(required.flags)
    strength_wc = _value(t.wc_for_strength(required.fcr_mpa,ae,policy),'strength_wc',flags)
    durable = t.max_wc_durability(durability)
    specified = t.wc_for_specified_fc(fc_mpa,ae,policy)
    flags.extend(flags_from_lookup(specified,'SPECIFIED_FC_TABLE'))
    flags.append(Flag('WC_TABLE_BASIS_DIFFERENCE','info','Specified-strength table shown for comparison only; required-average table governs prediction.'))
    min_fc = t.min_fc_durability_mpa(durability)
    if min_fc.value is not None and min_fc.value > fc_mpa:
        flags.append(Flag('DURABILITY_MIN_FC','warning','Durability minimum strength exceeds specified fc; specified value not raised.'))
    governing = 'durability' if durable.value is not None and durable.value < strength_wc else 'strength'
    selected = durable.value if governing == 'durability' else strength_wc
    return WcStep(required,strength_wc,durable.value,selected,governing,specified.value,tuple(flags))


def step4_wc(specified_fc_mpa: float, sigma_mpa: float | None, n_samples: int | None,
             air_entrained: bool, durability_class: DurabilityClass) -> WcStep:
    """Lowest strength/durability w/c governs; report conflicting table basis."""
    return _wc(specified_fc_mpa,sigma_mpa,n_samples,air_entrained,durability_class,'extrapolate')


def step5_cement(water_kg_m3: float, wc: float, wc_governing: str, nmas_mm: float,
                 exposure: Exposure, underwater: bool, flatwork: bool) -> CementStep:
    """Cement kg/m3=max(water/wc, applicable minimums); recompute final w/c."""
    _number(water_kg_m3,'water_kg_m3',strict=True)
    _number(wc,'wc',strict=True)
    flags: list[Flag] = []
    minimums: dict[str,float] = {}
    if exposure == 'severe':
        minimums['severe_exposure'] = t.min_cement_misc_kg_m3('severe_exposure').value
    if underwater:
        minimums['underwater'] = t.min_cement_misc_kg_m3('underwater').value
    if flatwork:
        lookup = t.min_cement_flatwork_kg_m3(nmas_mm)
        flags.extend(flags_from_lookup(lookup,'FLATWORK_MINIMUM'))
        if lookup.value is not None:
            minimums['flatwork'] = lookup.value
    reason = max(minimums,key=minimums.get) if minimums else None
    minimum = minimums[reason] if reason is not None else None
    from_wc = water_kg_m3/wc
    cement = max(from_wc,minimum) if minimum is not None else from_wc
    governing = wc_governing
    if cement > from_wc:
        governing = 'min_cement'
        flags.append(Flag('MIN_CEMENT_GOVERNS','warning','Minimum cement governs; final w/c reduced.'))
    return CementStep(from_wc,minimum,reason,cement,water_kg_m3/cement,governing,tuple(flags))


def _coarse(nmas_mm: float, fm: float, drd_kg_m3: float, absorption_pct: float,
             adjustment_factor: float, policy: Policy) -> CoarseStep:
    _number(drd_kg_m3,'drd_kg_m3',strict=True)
    _number(adjustment_factor,'adjustment_factor',strict=True)
    _number(absorption_pct,'absorption_pct')
    flags: list[Flag] = []
    ratio = _value(t.bulk_volume_ratio(nmas_mm,fm,policy),'bulk_ratio',flags)
    used = ratio*adjustment_factor
    dry_kg_m3 = drd_kg_m3*used
    return CoarseStep(ratio,used,dry_kg_m3,dry_kg_m3*(1+absorption_pct/100),tuple(flags))


def step6_coarse(nmas_mm: float, fm: float, drd_kg_m3: float, absorption_pct: float,
                  adjustment_factor: float) -> CoarseStep:
    """OD coarse kg/m3=DRD*b/b0*adjustment; SSD=OD*(1+Abs/100)."""
    return _coarse(nmas_mm,fm,drd_kg_m3,absorption_pct,adjustment_factor,'extrapolate')


def _fine(cement_kg_m3: float, cement_sg: float, water_kg_m3: float, air_pct: float,
           coarse_ssd_kg_m3: float, coarse_sg_ssd: float, fine_sg_ssd: float,
           nmas_mm: float, air_entrained: bool, policy: Policy) -> FineStep:
    _number(air_pct,'air_pct')
    _number(fine_sg_ssd,'fine_sg_ssd',strict=True)
    volumes = {'cement':absolute_volume_m3(cement_kg_m3,cement_sg),
        'water':absolute_volume_m3(water_kg_m3,1), 'air':air_pct/100,
        'coarse':absolute_volume_m3(coarse_ssd_kg_m3,coarse_sg_ssd)}
    fine_m3 = 1-sum(volumes.values())
    if fine_m3 <= 0:
        raise ValueError('fine_volume_m3 is nonpositive; no physical mix at these inputs')
    fine_kg_m3 = fine_m3*fine_sg_ssd*1000
    flags: list[Flag] = []
    unit_weight = _value(t.fresh_unit_weight_kg_m3(nmas_mm,air_entrained,policy),'unit_weight',flags)
    weight_method = unit_weight-water_kg_m3-cement_kg_m3-coarse_ssd_kg_m3
    if weight_method <= 0:
        flags.append(Flag('FINE_WEIGHT_METHOD_NONPOSITIVE','error','Comparison weight method gives nonpositive fine mass.'))
    return FineStep(volumes,fine_m3,fine_kg_m3,unit_weight,weight_method,
        weight_method-fine_kg_m3,tuple(flags))


def step7_fine(cement_kg_m3: float, cement_sg: float, water_kg_m3: float, air_pct: float,
                coarse_ssd_kg_m3: float, coarse_sg_ssd: float, fine_sg_ssd: float,
                nmas_mm: float, air_entrained: bool) -> FineStep:
    """Fine SSD kg/m3 from remaining volume; report density-based alternative."""
    return _fine(cement_kg_m3,cement_sg,water_kg_m3,air_pct,coarse_ssd_kg_m3,
                  coarse_sg_ssd,fine_sg_ssd,nmas_mm,air_entrained,'clamp')


def step8_moisture(convention: MoistureConvention, water_kg_m3: float, coarse: CoarseStep,
                    fine: FineStep, coarse_props: CoarseAggregateProperties,
                    fine_props: FineAggregateProperties) -> FieldWeights:
    """Course uses CA_OD/FA_SSD design weights; strict uses CA_SSD/FA_SSD (A-20)."""
    _choice(convention,MoistureConvention,'convention')
    if convention == 'course':
        return field_weights_course(water_kg_m3,coarse.coarse_dry_kg_m3,fine.fine_ssd_kg_m3,
            coarse_props.mc_pct,coarse_props.absorption_pct,fine_props.mc_pct,fine_props.absorption_pct)
    return field_weights_strict(water_kg_m3,coarse.coarse_ssd_kg_m3,fine.fine_ssd_kg_m3,
        coarse_props.mc_pct,coarse_props.absorption_pct,fine_props.mc_pct,fine_props.absorption_pct)


def step9_proportions(cement_kg_m3: float, field: FieldWeights) -> Proportions:
    """Field C:FA:CA:W mass ratios with cement=1 (CIE308 step 9)."""
    _number(cement_kg_m3,'cement_kg_m3',strict=True)
    return Proportions(1,field.fine_wet_kg/cement_kg_m3,field.coarse_wet_kg/cement_kg_m3,
                        field.water_adjusted_kg/cement_kg_m3)


def step10_batch(cement_kg_m3: float, field: FieldWeights, batch_volume_m3: float) -> BatchWeights:
    """Scale per-m3 field weights by batch m3; include task trial guidance."""
    _number(cement_kg_m3,'cement_kg_m3',strict=True)
    _number(batch_volume_m3,'batch_volume_m3',strict=True)
    limits = t.input_validation_limits()
    guidance = (f"Check slump within +/-{limits['trial_batch.slump_tolerance_mm']} mm.",
        f"Check air within +/-{limits['trial_batch.air_tolerance_pct']} percent.",
        'Check fresh unit weight.',
        f"Make {int(limits['trial_batch.n_cylinders'])} cylinders for the 28-day test.")
    return BatchWeights(batch_volume_m3,cement_kg_m3*batch_volume_m3,
        field.water_adjusted_kg*batch_volume_m3,field.coarse_wet_kg*batch_volume_m3,
        field.fine_wet_kg*batch_volume_m3,guidance)


def design_mix(inputs: ModeAInputs, policy: Policy = 'extrapolate') -> MixDesignReport:
    """Run ten course design steps, preserving intermediate SI values and flags."""
    flags = list(validate_mode_a(inputs))
    if policy not in ('clamp','raise','extrapolate'):
        raise ValueError('Unknown policy')
    slump = step1_slump(inputs.element,inputs.slump_target_mm,inputs.hand_consolidated)
    nmas = step2_nmas(inputs.form_min_dimension_mm,inputs.rebar_clear_spacing_mm,
                      inputs.cover_mm,inputs.slab_thickness_mm,inputs.nmas_mm)
    water_air = _water_air(slump.target_mm,nmas.nmas_mm,inputs.air_entrained,inputs.exposure,
                           inputs.coarse.shape,inputs.water_reducer_pct,policy)
    wc = _wc(inputs.specified_fc_mpa,inputs.sigma_mpa,inputs.n_samples,
              inputs.air_entrained,inputs.durability_class,policy)
    cement = step5_cement(water_air.water_kg_m3,wc.wc,wc.governing,nmas.nmas_mm,
                          inputs.exposure,inputs.underwater,inputs.flatwork)
    coarse = _coarse(nmas.nmas_mm,inputs.fine.fm,inputs.coarse.drd_kg_m3,
                     inputs.coarse.absorption_pct,inputs.bb0_adjustment_factor,policy)
    fine = _fine(cement.cement_kg_m3,inputs.cement_sg,water_air.water_kg_m3,water_air.air_pct,
        coarse.coarse_ssd_kg_m3,inputs.coarse.sg_ssd,inputs.fine.sg_ssd,nmas.nmas_mm,inputs.air_entrained,policy)
    field = step8_moisture(inputs.moisture_convention,water_air.water_kg_m3,coarse,fine,inputs.coarse,inputs.fine)
    other = step8_moisture('strict' if inputs.moisture_convention=='course' else 'course',
                            water_air.water_kg_m3,coarse,fine,inputs.coarse,inputs.fine)
    proportions = step9_proportions(cement.cement_kg_m3,field)
    batch = step10_batch(cement.cement_kg_m3,field,inputs.batch_volume_m3)
    for step in (slump,nmas,water_air,wc,cement,coarse,fine):
        flags.extend(step.flags)
    if min(field.water_adjusted_kg,other.water_adjusted_kg) <= 0:
        flags.append(Flag('NONPOSITIVE_FIELD_WATER','error','Moisture correction gives nonpositive added water; do not batch this result.'))
    if inputs.moisture_convention=='course':
        flags.append(Flag('COURSE_MOISTURE_BASIS','warning','Course FA correction treats SSD design mass as dry (Q25); strict alternative shown.'))
    return MixDesignReport(inputs,slump,nmas,water_air,wc,cement,coarse,fine,field,other,
        proportions,batch,cement.governing,tuple(flags),DISCLAIMER)


def to_mode_b_inputs(design: MixDesignReport) -> MixInputs:
    """Convert selected field kg/m3 to explicit as-received Mode B inputs."""
    return MixInputs(Binder('cement',design.cement.cement_kg_m3,design.inputs.cement_sg,'cement'),
        design.field.water_adjusted_kg,design.field.coarse_wet_kg,design.inputs.coarse,
        design.field.fine_wet_kg,design.inputs.fine,design.nmas.nmas_mm,'as_received',
        design.inputs.air_entrained,design.inputs.exposure,cement_type=design.inputs.cement_type,
        air_pct=design.water_air.air_pct,curing=design.inputs.curing,
        sigma_mpa=design.inputs.sigma_mpa,n_samples=design.inputs.n_samples,element=design.inputs.element)
