"""Streamlit boundary; all engineering calculations live in concretecalc."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.adapters import (DEFAULT_VALUES,mode_b_inputs_from_widgets,report_rows_for_display,
    report_to_csv_text,default_air_pct)
from concretecalc import schemas as s, units as u
from concretecalc.mode_b import run_mode_b,report_to_dict


def _convert(value: float,kind: str,to_us: bool) -> float:
    """Unit boundary only; kinds distinguish content from actual batch mass."""
    pairs={'content':(u.kg_m3_to_lb_yd3,u.lb_yd3_to_kg_m3),
        'mass':(u.kg_to_lb,u.lb_to_kg),'density':(u.kg_m3_to_pcf,u.pcf_to_kg_m3),
        'length':(u.mm_to_in,u.in_to_mm),'stress':(u.mpa_to_psi,u.psi_to_mpa),
        'volume':(u.m3_to_yd3,u.yd3_to_m3)}
    if kind not in pairs:
        return value
    return pairs[kind][0 if to_us else 1](value)


def _unit_change() -> None:
    """Preserve physical widget values when changing display units."""
    to_us=st.session_state.unit_system=='US'
    for prefix in ('b','a'):
        mapping={'nmas_mm':'length','coarse_drd_kg_m3':'density','sigma_mpa':'stress',
            'specified_fc_mpa':'stress','batch_volume_m3':'volume','slump_target_mm':'length',
            'form_min_dimension_mm':'length','rebar_clear_spacing_mm':'length',
            'cover_mm':'length','slab_thickness_mm':'length'}
        for field in ('cement_kg','water_kg','coarse_kg','fine_kg','superplasticizer_kg'):
            mapping[field]='mass' if st.session_state.get(prefix+'_use_batch',False) else 'content'
        for field,kind in mapping.items():
            key=prefix+'_'+field
            if key in st.session_state and st.session_state[key] is not None:
                st.session_state[key]=_convert(st.session_state[key],kind,to_us)


def _number(prefix: str,field: str,label: str,default: float,kind: str='',
             minimum: float=0.0,maximum: float | None=None) -> float:
    """Numeric widget whose default/bounds are authored in SI; returns display units."""
    us=st.session_state.unit_system=='US'
    value=_convert(float(default),kind,True) if us else float(default)
    low=_convert(float(minimum),kind,True) if us else float(minimum)
    high=None if maximum is None else (_convert(float(maximum),kind,True) if us else float(maximum))
    return st.number_input(label,min_value=low,max_value=high,value=value,
        key=prefix+'_'+field,format='%.4f')


def _select(prefix: str,field: str,label: str,options: tuple | list,default: str | None=None) -> str:
    """Plain labelled choice; underscore labels are made readable for display."""
    index=options.index(default) if default in options else 0
    return st.selectbox(label,options,index=index,key=prefix+'_'+field,
                        format_func=lambda value:value.replace('_',' ').title())


def material_widgets(prefix: str,design: bool=False) -> dict:
    """Collect material properties; all entered numeric values remain in display units."""
    us=st.session_state.unit_system=='US'
    length='in' if us else 'mm'
    density='pcf' if us else 'kg/m³'
    v={}
    batch=False
    if not design:
        with st.container(border=True):
            st.subheader('Aggregate weight basis')
            v['aggregate_weight_basis']=_select(prefix,'basis','Basis for both aggregates',
                ['as_received','ssd','oven_dry'],'as_received')
            st.caption('As received: stockpile mass includes total moisture. Oven dry: dry mass, moisture is added to it. SSD: saturated surface-dry mass; free water is zero and MC is treated as absorption.')
        batch=st.checkbox('Enter actual batch weights',key=prefix+'_use_batch',
            help='Leave off for contents per unit volume. When enabled, enter actual weights and the declared batch volume.')
        if batch:
            v['batch_volume_m3']=_number(prefix,'batch_volume_m3',f'Batch volume ({"yd³" if us else "m³"})',1,'volume',.000001)
    mass=('lb' if us else 'kg') if batch else ('lb/yd³' if us else 'kg/m³')
    kind='mass' if batch else 'content'
    left,right=st.columns(2)
    with left,st.container(border=True):
        st.subheader('Cement')
        if not design:
            v['cement_kg']=_number(prefix,'cement_kg',f'Cement ({mass})',350,kind,.000001)
        v['cement_sg']=_number(prefix,'cement_sg','Cement specific gravity',3.15,minimum=.000001)
        v['cement_type']=_select(prefix,'cement_type','Cement type',['I','II','III','IV','V'],'I')
        if not design:
            v['cement_strength_class']=st.text_input('Cement strength class (optional)',key=prefix+'_strength_class') or None
    with right,st.container(border=True):
        st.subheader('Coarse aggregate')
        if not design:
            v['coarse_kg']=_number(prefix,'coarse_kg',f'Coarse aggregate ({mass})',1000,kind,.000001)
        v['coarse_sg_ssd']=_number(prefix,'coarse_sg_ssd','Coarse SSD specific gravity',2.65,minimum=.000001)
        v['coarse_drd_kg_m3']=_number(prefix,'coarse_drd_kg_m3',f'Dry-rodded density ({density})',1600,'density',.000001)
        v['coarse_absorption_pct']=_number(prefix,'coarse_absorption_pct','Coarse absorption (%)',1,maximum=20)
        v['coarse_mc_pct']=_number(prefix,'coarse_mc_pct','Coarse total moisture (%)',1,maximum=30)
        v['coarse_shape']=_select(prefix,'coarse_shape','Coarse shape',list(s.AGGREGATE_SHAPES),'angular')
    with left,st.container(border=True):
        st.subheader('Fine aggregate')
        if not design:
            v['fine_kg']=_number(prefix,'fine_kg',f'Fine aggregate ({mass})',750,kind,.000001)
        v['fine_sg_ssd']=_number(prefix,'fine_sg_ssd','Fine SSD specific gravity',2.6,minimum=.000001)
        v['fine_absorption_pct']=_number(prefix,'fine_absorption_pct','Fine absorption (%)',1,maximum=20)
        v['fine_mc_pct']=_number(prefix,'fine_mc_pct','Fine total moisture (%)',1,maximum=30)
        v['fine_fm']=_number(prefix,'fine_fm','Fine fineness modulus',2.6,minimum=.000001)
    if not design:
        with right,st.container(border=True):
            st.subheader('Water')
            v['water_kg']=_number(prefix,'water_kg',f'Added water ({mass})',180,kind,.000001)
    with st.container(border=True):
        st.subheader('Mix, curing and test conditions')
        v['air_entrained']=st.checkbox('Air entrained',key=prefix+'_ae')
        v['exposure']=_select(prefix,'exposure','Exposure',list(s.EXPOSURES),'moderate')
        v['nmas_mm']=_number(prefix,'nmas_mm',f'Nominal maximum aggregate size ({length})',19,'length',.000001)
        v['curing']=_select(prefix,'curing','Curing',['moist','steam'],'moist')
        v['element']=_select(prefix,'element','Element',list(s.ELEMENT_TYPES),'building_columns')
        if not design:
            v['age_days']=_number(prefix,'age_days','Test age (days)',28,minimum=1)
            nmas_si=u.in_to_mm(v['nmas_mm']) if us else v['nmas_mm']
            default_air=default_air_pct(nmas_si,v['exposure'],v['air_entrained'])
            override=st.checkbox('Override table air content',key=prefix+'_override_air')
            if not override:
                st.session_state[prefix+'_air_pct']=default_air
            v['air_pct']=st.number_input('Air content (%)',min_value=0.0,max_value=99.0,
                key=prefix+'_air_pct',disabled=not override)
            v['specimen']=_select(prefix,'specimen','Specimen',['cylinder_150x300','cube_150'],'cylinder_150x300')
            if v['specimen']=='cube_150' and st.checkbox('Provide cube-to-cylinder factor',key=prefix+'_has_cube_factor'):
                v['cube_to_cylinder_factor']=st.number_input('User cube-to-cylinder factor',min_value=.000001,
                    value=None,key=prefix+'_cube_to_cylinder_factor',help='Enter the explicit factor accepted for your specimens; no default is assumed.')
        if st.checkbox('Known strength standard deviation',key=prefix+'_known_sigma'):
            v['sigma_mpa']=_number(prefix,'sigma_mpa',f'Standard deviation ({"psi" if us else "MPa"})',2.4,'stress')
            v['n_samples']=int(st.number_input('Number of strength results',min_value=1,value=30,key=prefix+'_n_samples'))
    with st.container(border=True):
        st.subheader('Admixtures (optional)')
        if st.checkbox('Water reducer specified',key=prefix+'_has_wr'):
            v['water_reducer_pct']=_number(prefix,'water_reducer_pct','Water reduction (%)',10,maximum=99)
        if not design:
            if st.checkbox('Air-entrainer product rate specified',key=prefix+'_has_dose'):
                v['air_entrainer_ml_per_pct_per_100kg']=_number(prefix,'dose','Product rate (ml per air % per 100 kg cement)',6.3)
            if st.checkbox('Superplasticizer specified',key=prefix+'_has_sp'):
                v['superplasticizer_kg']=_number(prefix,'superplasticizer_kg',f'Superplasticizer ({mass})',0,kind)
    return v


def render_flags(flags: tuple) -> None:
    """Group returned engine flags by severity; no calculation logic here."""
    with st.expander(f'Checks and notices ({len(flags)})',expanded=True):
        for severity,display in [('error',st.error),('warning',st.warning),('info',st.info)]:
            for flag in flags:
                if flag.severity==severity:
                    display(flag.message)


def render_report(report,unit_system: str) -> None:
    """Render report data and prepared plot coordinates in the selected units."""
    us=unit_system=='US'
    stress=u.mpa_to_psi if us else float
    length=u.mm_to_in if us else float
    stress_unit='psi' if us else 'MPa'
    st.header('Research prediction')
    st.metric('Effective water / cement',f'{report.wc:.4f}')
    columns=st.columns(len(report.predictions))
    for column,(name,prediction) in zip(columns,report.predictions.items()):
        value=prediction.mean_28d_mpa
        column.metric(f'{name} · 28-day mean ({stress_unit})','unavailable' if value is None else f'{stress(value):.2f}')
    if report.slump.slump_mm is not None:
        st.metric(f'Slump estimate ({"in" if us else "mm"})',f'{length(report.slump.slump_mm):.2f}',
            help='Placeholder uncertainty band, not a statistical confidence interval.')
        st.caption(f'Placeholder band ±{length(report.slump.band_mm):.2f}; trial-batch tolerance ±{length(report.slump.trial_tolerance_mm):.2f}.')
    for section,rows in report_rows_for_display(report,unit_system).items():
        if section!='Notice':
            with st.expander(section,expanded=section in ('Strength','Weights')):
                st.table([{'Quantity':label,'Value':value} for label,value in rows])
    with st.expander('Reference density, packing and dosage'):
        density=u.kg_m3_to_pcf if us else float
        density_unit='pcf' if us else 'kg/m³'
        comparison=report.unit_weight
        packing=report.indicators
        st.write(f'Computed density: {density(comparison.computed_kg_m3):.3f} {density_unit}')
        if comparison.aci_kg_m3 is not None:
            st.write(f'ACI density: {density(comparison.aci_kg_m3):.3f} {density_unit}; deviation {comparison.deviation_pct:.2f}%')
        st.write(f'Paste volume fraction: {packing.paste_volume_m3:.4f}')
        if packing.coarse_bulk_ratio_table is not None:
            st.write(f'Coarse bulk ratio reference: {packing.coarse_bulk_ratio_table:.4f}')
        if packing.coarse_bulk_ratio_deviation_pct is not None:
            st.write(f'Coarse bulk ratio deviation: {packing.coarse_bulk_ratio_deviation_pct:.2f}%')
        if report.air_entrainer_dosage_ml_m3 is not None:
            st.write(f'Product-specific air-entrainer estimate: {report.air_entrainer_dosage_ml_m3:.2f} ml/m³')
    with st.expander('Model constants and assumptions'):
        st.caption('Abrams assumes constant cement, aggregates, placement, curing and test conditions. SCM strength effects are not supported.')
        for name,prediction in report.predictions.items():
            st.write(name,'calibrated' if prediction.calibrated else 'uncalibrated',prediction.constants_used)
            st.caption(prediction.constants_source)
    fig,ax=plt.subplots()
    for label,points in [('ACI non-AE',report.plot.aci_non_ae_points),('ACI AE',report.plot.aci_ae_points)]:
        ax.scatter([p[0] for p in points],[stress(p[1]) for p in points],label=label)
    for name,points in report.plot.model_curves.items():
        ax.plot([p[0] for p in points],[stress(p[1]) if p[1] is not None else float('nan') for p in points],label=name)
        value=report.plot.mix_point_strengths_mpa[name]
        if value is not None:
            ax.scatter([report.wc],[stress(value)],marker='x',s=60)
    ax.set(xlabel='Effective w/c',ylabel=f'Estimated 28-day mean ({stress_unit})')
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)
    render_flags(report.flags)
    st.download_button('Download full report · JSON (SI)',json.dumps(report_to_dict(report),indent=2,allow_nan=False),'strength-report.json','application/json')
    st.download_button('Download report · CSV (SI)',report_to_csv_text(report),'strength-report.csv','text/csv')


st.set_page_config(page_title='Concrete research calculator',layout='wide')
st.title('Concrete research calculator')
st.info(s.DISCLAIMER)
unit_system=st.sidebar.selectbox('Unit system',['SI','US'],key='unit_system',on_change=_unit_change)
convention=st.sidebar.selectbox('Moisture convention',['course','strict'],key='moisture_convention')
policy=st.sidebar.selectbox('Out-of-range policy',['extrapolate','clamp','raise'],key='policy')
mode=st.sidebar.selectbox('Mode',['Mode B'],key='mode')
normalise=st.sidebar.checkbox('Normalize age equation to 28 days',key='normalise_age')
try:
    values=material_widgets('b')
    inputs=mode_b_inputs_from_widgets(values,unit_system)
    render_report(run_mode_b(inputs,policy=policy,normalise_age_to_28d=normalise),unit_system)
except (ValueError,KeyError,OverflowError) as error:
    st.error(str(error))
