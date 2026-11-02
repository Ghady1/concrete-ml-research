"""Pure widget/unit boundary: no Streamlit imports and no engineering equations."""
import csv
import io
from typing import Literal
from concretecalc import schemas as s, units as u
from concretecalc.mode_b import StrengthReport
from concretecalc.mix_design import MixDesignReport
from concretecalc.tables.lookups import air_content_pct

UnitSystem=Literal['SI','US']
DEFAULT_VALUES={
    'cement_kg':350.0,'cement_sg':3.15,'cement_type':'I','water_kg':180.0,
    'coarse_kg':1000.0,'coarse_sg_ssd':2.65,'coarse_drd_kg_m3':1600.0,
    'coarse_absorption_pct':1.0,'coarse_mc_pct':1.0,'coarse_shape':'angular',
    'fine_kg':750.0,'fine_sg_ssd':2.6,'fine_absorption_pct':1.0,'fine_mc_pct':1.0,
    'fine_fm':2.6,'nmas_mm':19.0,'aggregate_weight_basis':'as_received',
    'air_entrained':False,'exposure':'moderate','curing':'moist','age_days':28.0,
    'air_pct':None,'batch_volume_m3':None,'sigma_mpa':None,'n_samples':None,
    'specimen':'cylinder_150x300','cube_to_cylinder_factor':None,
    'element':'building_columns','specified_fc_mpa':25.0,'moisture_convention':'course',
}


def _values(values: dict[str,object], unit_system: UnitSystem) -> dict:
    """Merge SI defaults; only explicitly supplied numeric values use display units."""
    if unit_system not in ('SI','US'):
        raise ValueError('Unknown unit_system')
    result=dict(DEFAULT_VALUES)
    result.update(values)
    if unit_system=='US':
        batch=result.get('batch_volume_m3') is not None
        for key in ('cement_kg','water_kg','coarse_kg','fine_kg','superplasticizer_kg'):
            if key in values and values[key] is not None:
                result[key]=u.lb_to_kg(values[key]) if batch else u.lb_yd3_to_kg_m3(values[key])
        conversions={'coarse_drd_kg_m3':u.pcf_to_kg_m3,'nmas_mm':u.in_to_mm,
            'specified_fc_mpa':u.psi_to_mpa,'sigma_mpa':u.psi_to_mpa,
            'batch_volume_m3':u.yd3_to_m3,'slump_target_mm':u.in_to_mm,
            'form_min_dimension_mm':u.in_to_mm,'rebar_clear_spacing_mm':u.in_to_mm,
            'cover_mm':u.in_to_mm,'slab_thickness_mm':u.in_to_mm}
        for key,conversion in conversions.items():
            if key in values and values[key] is not None:
                result[key]=conversion(values[key])
    return result


def _aggregates(v: dict) -> tuple[s.CoarseAggregateProperties,s.FineAggregateProperties]:
    """Pack material inputs after conversion, retaining explicit SSD SG."""
    return (s.CoarseAggregateProperties(v['coarse_sg_ssd'],v['coarse_drd_kg_m3'],
        v['coarse_absorption_pct'],v['coarse_mc_pct'],v['coarse_shape']),
        s.FineAggregateProperties(v['fine_sg_ssd'],v['fine_absorption_pct'],v['fine_mc_pct'],v['fine_fm']))


def mode_b_inputs_from_widgets(values: dict[str,object],unit_system: UnitSystem) -> s.MixInputs:
    """Displayed content or batch weights -> SI inputs; caller declares the basis."""
    v=_values(values,unit_system)
    coarse,fine=_aggregates(v)
    return s.MixInputs(s.Binder('cement',v['cement_kg'],v['cement_sg'],'cement'),
        v['water_kg'],v['coarse_kg'],coarse,v['fine_kg'],fine,v['nmas_mm'],
        v['aggregate_weight_basis'],v['air_entrained'],v['exposure'],cement_type=v['cement_type'],
        cement_strength_class=v.get('cement_strength_class'),air_pct=v['air_pct'],curing=v['curing'],
        age_days=v['age_days'],batch_volume_m3=v['batch_volume_m3'],specimen=v['specimen'],
        cube_to_cylinder_factor=v['cube_to_cylinder_factor'],sigma_mpa=v['sigma_mpa'],
        n_samples=v['n_samples'],element=v.get('element'),
        admixtures=s.Admixtures(v.get('air_entrainer_ml_per_pct_per_100kg'),
            v.get('water_reducer_pct'),v.get('superplasticizer_kg')))


def mode_a_inputs_from_widgets(values: dict[str,object],unit_system: UnitSystem) -> s.ModeAInputs:
    """Convert displayed targets/geometry/density to SI design inputs."""
    v=_values(values,unit_system)
    coarse,fine=_aggregates(v)
    return s.ModeAInputs(v['specified_fc_mpa'],v['element'],v['exposure'],v['air_entrained'],
        v['cement_sg'],coarse,fine,sigma_mpa=v['sigma_mpa'],n_samples=v['n_samples'],
        slump_target_mm=v.get('slump_target_mm'),hand_consolidated=v.get('hand_consolidated',False),
        nmas_mm=v['nmas_mm'],form_min_dimension_mm=v.get('form_min_dimension_mm'),
        rebar_clear_spacing_mm=v.get('rebar_clear_spacing_mm'),cover_mm=v.get('cover_mm'),
        slab_thickness_mm=v.get('slab_thickness_mm'),durability_class=v.get('durability_class','none'),
        underwater=v.get('underwater',False),flatwork=v.get('flatwork',False),cement_type=v['cement_type'],
        curing=v['curing'],water_reducer_pct=v.get('water_reducer_pct'),
        moisture_convention=v['moisture_convention'],bb0_adjustment_factor=v.get('bb0_adjustment_factor',1.0),
        batch_volume_m3=1.0 if v['batch_volume_m3'] is None else v['batch_volume_m3'])


def report_rows_for_display(report: StrengthReport,unit_system: UnitSystem) -> dict[str,list[tuple[str,str]]]:
    """Format SI report quantities for display; rounding happens only here."""
    if unit_system not in ('SI','US'):
        raise ValueError('Unknown unit_system')
    stress=u.mpa_to_psi if unit_system=='US' else float
    content=u.kg_m3_to_lb_yd3 if unit_system=='US' else float
    length=u.mm_to_in if unit_system=='US' else float
    density=u.kg_m3_to_pcf if unit_system=='US' else float
    stress_unit='psi' if unit_system=='US' else 'MPa'
    mass_unit='lb/yd3' if unit_system=='US' else 'kg/m3'
    length_unit='in' if unit_system=='US' else 'mm'
    output={'Summary':[('Effective w/c',f'{report.wc:.4f}'),('Effective w/cm',f'{report.wcm:.4f}'),('Air (%)',f'{report.air_pct:.3f}')],
        'Weights':[(f'Cement ({mass_unit})',f'{content(report.cement_kg_m3):.3f}'),
            (f'Added water ({mass_unit})',f'{content(report.water_added_kg_m3):.3f}'),
            (f'Effective water ({mass_unit})',f'{content(report.water.effective_water_kg):.3f}'),
            (f'Free water CA ({mass_unit})',f'{content(report.water.free_water_ca_kg):.3f}'),
            (f'Free water FA ({mass_unit})',f'{content(report.water.free_water_fa_kg):.3f}'),
            (f'Coarse SSD ({mass_unit})',f'{content(report.coarse.ssd_kg):.3f}'),
            (f'Fine SSD ({mass_unit})',f'{content(report.fine.ssd_kg):.3f}')],
        'Strength':[],
        'Volumes per unit concrete volume':[(name.removesuffix('_m3').replace('_',' '),f'{getattr(report.volumes,name):.6f}') for name in
            ('cement_m3','scm_m3','water_m3','coarse_m3','fine_m3','air_m3','total_m3','closure_error_m3')],
        'Indicators':[(f'Unit weight ({"pcf" if unit_system=="US" else "kg/m3"})',f'{density(report.unit_weight.computed_kg_m3):.3f}'),
            ('CA void fraction',f'{report.indicators.coarse_void_content:.4f}'),
            ('Actual CA bulk ratio',f'{report.indicators.coarse_bulk_ratio_actual:.4f}'),
            ('FA mass fraction',f'{report.indicators.fine_fraction_by_mass:.4f}'),
            ('FA volume fraction',f'{report.indicators.fine_fraction_by_volume:.4f}')],
        'Slump':[], 'Notice':[('DISCLAIMER',report.disclaimer)]}
    for name,prediction in report.predictions.items():
        for label,value in [('28-day mean',prediction.mean_28d_mpa),
            ('age-adjusted',report.age_adjusted[name].strength_mpa if report.age_adjusted[name] else None),
            ('characteristic estimate',report.characteristic[name].fc_est_mpa if report.characteristic[name] else None),
            ('cube equivalent',report.cube_equivalent_mpa[name])]:
            output['Strength'].append((f'{name} {label} ({stress_unit})','unavailable' if value is None else f'{stress(value):.3f}'))
    for label,value in [('Estimate',report.slump.slump_mm),('Lower placeholder band',report.slump.lower_mm),('Upper placeholder band',report.slump.upper_mm)]:
        output['Slump'].append((f'{label} ({length_unit})','unavailable' if value is None else f'{length(value):.3f}'))
    return output


def report_to_csv_text(report: StrengthReport) -> str:
    """Export labelled SI report rows, disclaimer, constants and flags to CSV."""
    target=io.StringIO(newline='')
    writer=csv.writer(target)
    writer.writerow(('section','quantity','value'))
    for section,rows in report_rows_for_display(report,'SI').items():
        for label,value in rows:
            writer.writerow((section,label,value))
    for name,prediction in report.predictions.items():
        writer.writerow(('Constants',name,str(prediction.constants_used)))
        writer.writerow(('Source',name,prediction.constants_source))
    for flag in report.flags:
        writer.writerow(('Flags',f'{flag.severity}: {flag.code}',flag.message))
    return target.getvalue()


def default_air_pct(nmas_mm: float,exposure: s.Exposure,air_entrained: bool) -> float:
    """SI default air percent; UI may override without changing the lookup."""
    lookup=air_content_pct(nmas_mm,exposure,air_entrained)
    if lookup.value is None:
        raise ValueError('Default air unavailable')
    return lookup.value


def design_comparison_rows(design: MixDesignReport,prediction: StrengthReport,
                            unit_system: UnitSystem) -> list[dict[str,str]]:
    """Display each 28-day model mean and signed difference from design fcr."""
    if unit_system not in ('SI','US'):
        raise ValueError('Unknown unit_system')
    convert=u.mpa_to_psi if unit_system=='US' else float
    unit='psi' if unit_system=='US' else 'MPa'
    required=design.wc.fcr.fcr_mpa
    rows=[]
    for name,result in prediction.predictions.items():
        mean=result.mean_28d_mpa
        rows.append({'Model':name,f'Required mean ({unit})':f'{convert(required):.3f}',
            f'Predicted 28-day mean ({unit})':'unavailable' if mean is None else f'{convert(mean):.3f}',
            f'Difference from required mean ({unit})':'unavailable' if mean is None else f'{convert(mean-required):+.3f}'})
    return rows
