"""Streamlit boundary; all engineering calculations live in concretecalc."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import matplotlib
# Streamlit renders images in worker threads; never start a native Tk window.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.adapters import (DEFAULT_VALUES,mode_b_inputs_from_widgets,report_rows_for_display,
    report_to_csv_text,default_air_pct,mode_a_inputs_from_widgets)
from concretecalc import schemas as s, units as u
from concretecalc.mode_b import run_mode_b,report_to_dict
from concretecalc.mix_design import design_mix,to_mode_b_inputs
from concretecalc.calibration.dataset import load_rows,rows_to_fit_arrays
from concretecalc.calibration.fit import fit_all
from concretecalc.calibration.store import save_calibration,load_calibration

ROOT=Path(__file__).resolve().parents[1]
CALIBRATIONS_DIR=ROOT/'calibrations'


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


def _flatten(value: dict,prefix: str='') -> list[tuple[str,object]]:
    """Flatten step data for display; flags are presented separately."""
    rows=[]
    for key,item in value.items():
        if key=='flags':
            continue
        label=prefix+key
        if isinstance(item,dict):
            rows.extend(_flatten(item,label+'.'))
        elif isinstance(item,(tuple,list)):
            rows.append((label,'; '.join(str(part) for part in item)))
        else:
            rows.append((label,item))
    return rows


def _design_rows(step,number: int,unit_system: str) -> list[dict]:
    """Format step quantities, distinguishing per-m3 field weights from batch kg."""
    us=unit_system=='US'
    result=[]
    for key,value in _flatten(asdict(step)):
        label=key.replace('_',' ').replace('.',' · ').title()
        if key.startswith('volumes_m3.'):
            label='Volume fraction · '+key.split('.')[-1].title()
        elif key=='fine_volume_m3':
            label='Fine volume fraction'
        elif key.startswith('limits_mm.'):
            label='Size limit · '+key.split('.')[-1].replace('_',' ').title()
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            kind=''
            if key.endswith('_kg_m3') or (key.endswith('_kg') and number!=10):
                kind='content'
            elif key.endswith('_kg'):
                kind='mass'
            elif key.endswith('_mpa'):
                kind='stress'
            elif key.endswith('_mm') or key.startswith('limits_mm.'):
                kind='length'
            elif key=='batch_volume_m3':
                kind='volume'
            units={'content':'lb/yd³' if us else 'kg/m³','mass':'lb' if us else 'kg',
                'stress':'psi' if us else 'MPa','length':'in' if us else 'mm','volume':'yd³' if us else 'm³'}
            if kind:
                value=_convert(value,kind,True) if us else value
                for suffix in (' Kg M3',' Kg',' Mpa',' Mm',' M3'):
                    if label.endswith(suffix):
                        label=label[:-len(suffix)]
                        break
                label+=f' ({units[kind]})'
            value=f'{value:.6f}'
        result.append({'Quantity':label,'Value':'not applicable' if value is None else str(value)})
    return result


def mode_a_page(unit_system: str,convention: str,policy: str,normalise: bool,constants: dict) -> None:
    """Collect design inputs and render all ten returned steps, without equations."""
    values=material_widgets('a',design=True)
    us=unit_system=='US'
    with st.container(border=True):
        st.subheader('Design targets and geometry')
        values['specified_fc_mpa']=_number('a','specified_fc_mpa',f'Specified strength ({"psi" if us else "MPa"})',25,'stress',.000001)
        values['durability_class']=_select('a','durability_class','Durability class',list(s.DURABILITY_CLASSES),'none')
        values['underwater']=st.checkbox('Underwater placement',key='a_underwater')
        values['flatwork']=st.checkbox('Flatwork minimum cement',key='a_flatwork')
        values['hand_consolidated']=st.checkbox('Hand-consolidated mass concrete',key='a_hand_consolidated')
        if st.checkbox('Override element default slump',key='a_override_slump'):
            values['slump_target_mm']=_number('a','slump_target_mm',f'Target slump ({"in" if us else "mm"})',75,'length')
        if not st.checkbox('Use entered NMAS instead of geometry',value=True,key='a_override_nmas'):
            values['nmas_mm']=None
            for field,label,default in [('form_min_dimension_mm','Smallest form dimension',200),
                ('rebar_clear_spacing_mm','Clear rebar spacing',40),('cover_mm','Clear cover',40),
                ('slab_thickness_mm','Slab thickness',0)]:
                value=_number('a',field,f'{label} ({"in" if us else "mm"}; 0 = not supplied)',default,'length')
                values[field]=None if value==0 else value
        values['bb0_adjustment_factor']=_number('a','bb0_adjustment_factor','Coarse bulk-ratio adjustment',1,minimum=.000001)
        values['batch_volume_m3']=_number('a','batch_volume_m3',f'Trial batch volume ({"yd³" if us else "m³"})',1,'volume',.000001)
    values['moisture_convention']=convention
    design=design_mix(mode_a_inputs_from_widgets(values,unit_system),policy)
    st.header('Ten-step design walkthrough')
    st.metric('Governing constraint',design.governing_constraint.replace('_',' ').title())
    st.metric('Final water / cement',f'{design.cement.wc_final:.4f}')
    steps=[('Slump',design.slump),('Aggregate size',design.nmas),('Water and air',design.water_air),
        ('Strength and durability',design.wc),('Cement',design.cement),('Coarse aggregate',design.coarse),
        ('Fine aggregate',design.fine),('Field moisture corrections',design.field),
        ('Field proportions · C:FA:CA:W',design.proportions),('Batch weights and trial guidance',design.batch)]
    for number,(label,step) in enumerate(steps,start=1):
        with st.expander(f'{number}. {label}',expanded=number in (8,10)):
            st.table(_design_rows(step,number,unit_system))
            if number==8:
                st.caption(f'Alternative moisture convention: {design.field_other_convention.convention}')
                st.table(_design_rows(design.field_other_convention,8,unit_system))
                st.caption('Course applies the slide correction directly to design masses; strict uses SSD-consistent correction. See the professor question on this basis difference.')
    render_flags(design.flags)
    st.download_button('Download design · JSON (SI)',json.dumps(asdict(design),indent=2),
                       'mix-design.json','application/json')
    if st.button('Predict this design back in Mode B',key='predict_design'):
        prediction=run_mode_b(to_mode_b_inputs(design),constants=constants,policy=policy,normalise_age_to_28d=normalise)
        st.caption('Comparison uses the selected field moisture convention. Research models may differ from the required mean; durability and cement minimums can raise predicted strength.')
        render_report(prediction,unit_system)


def selected_constants() -> dict:
    """Load user-selected stored parameters at the application boundary."""
    names=sorted(path.stem for path in CALIBRATIONS_DIR.glob('*.json'))
    selected=st.sidebar.selectbox('Prediction constants',['Uncalibrated defaults',*names],key='calibrated_set')
    constants={}
    if selected!='Uncalibrated defaults':
        for name in ('abrams','bolomey','feret'):
            try:
                constants[name]=load_calibration(selected,name,CALIBRATIONS_DIR)
            except KeyError:
                st.sidebar.warning(f'No stored {name} fit; using its uncalibrated default.')
        st.sidebar.caption('Use only with the materials and test conditions represented by this calibration.')
    return constants


def calibration_page() -> None:
    """Upload, review errors, choose one material set, fit and save explicit results."""
    st.header('Calibration')
    st.caption('CSV and Excel records always use SI units, regardless of display units. Fit statistics describe the supplied rows, not independent validation.')
    st.download_button('Download SI lab template',(ROOT/'experiments'/'mix_log_template.csv').read_bytes(),
        'mix_log_template.csv','text/csv')
    uploaded=st.file_uploader('Lab mix log (CSV or .xlsx)',type=['csv','xlsx'],key='calibration_upload')
    if uploaded is None:
        st.info('Upload your lab records to validate and fit. Delete the template’s synthetic rows first; at least three eligible rows are required.')
        return
    payload=uploaded.getvalue()
    data_hash=hashlib.sha256(payload).hexdigest()
    # The dataset API accepts a path. Keep upload bytes in a temporary boundary
    # file; only the original name and exact hash enter stored provenance.
    with TemporaryDirectory(prefix='concretecalc-upload-') as temporary:
        path=Path(temporary)/('records'+Path(uploaded.name).suffix.lower())
        path.write_bytes(payload)
        rows,errors=load_rows(path)
    st.write(f'{len(rows)} valid rows; {len(errors)} validation errors.')
    if errors:
        st.table([{'Row':row,'Column':column,'Message':message} for row,column,message in errors])
    if not rows:
        return
    st.dataframe([asdict(row) for row in rows],hide_index=True)
    material=st.selectbox('Material set to fit',sorted({row.material_set_id for row in rows}),key='fit_material')
    age_policy=st.selectbox('Age policy',['only_28d','convert'],key='fit_age_policy',
        format_func=lambda value:'28-day measurements only' if value=='only_28d' else 'Convert other ages using the literal age equation')
    selected=tuple(row for row in rows if row.material_set_id==material)
    eligible=sum(row.age_days==28 or age_policy=='convert' for row in selected)
    st.caption(f'{len(selected)} rows in this material set; {eligible} eligible for this age policy. Other-age rows are excluded by default.')
    if age_policy=='convert':
        st.warning('Age conversion is model-based. Confirm cement type, curing and age-equation validity; actual 28-day measurements remain unchanged.')
    permission=not errors
    if errors:
        permission=st.checkbox('Fit valid rows while excluding the invalid rows shown above',key='fit_valid_subset')
    context=(data_hash,material,age_policy)
    if st.button('Fit three strength models',key='fit_models',disabled=eligible<3 or not permission):
        results=fit_all(rows_to_fit_arrays(selected,age_policy))
        st.session_state['calibration_fit']=(context,results)
    saved=st.session_state.get('calibration_fit')
    if saved is None or saved[0]!=context:
        return
    results=saved[1]
    st.table([{'Model':name,'Rows':result.n_rows,'R²':result.r2,'R² space':result.r2_space,
        'R² (MPa)':result.r2_mpa,'RMSE (MPa)':result.rmse_mpa,'Constants':str(result.values)}
        for name,result in results.items()])
    st.caption('These coefficients are fitted in memory. Predictions acquire calibrated status only when loaded from a saved material-set file.')
    if st.button('Save fits for this material set',key='save_fits',disabled=not permission):
        for name,result in results.items():
            path=save_calibration(material,name,result,uploaded.name,data_hash,CALIBRATIONS_DIR)
        st.success(f'Saved three models for {material}. Select this set under Prediction constants after refreshing the page.')


st.set_page_config(page_title='Concrete research calculator',layout='wide')
st.title('Concrete research calculator')
st.info(s.DISCLAIMER)
unit_system=st.sidebar.selectbox('Unit system',['SI','US'],key='unit_system',on_change=_unit_change)
convention=st.sidebar.selectbox('Moisture convention',['course','strict'],key='moisture_convention')
policy=st.sidebar.selectbox('Out-of-range policy',['extrapolate','clamp','raise'],key='policy')
mode=st.sidebar.selectbox('Mode',['Mode B','Mode A','Calibration'],key='mode')
normalise=st.sidebar.checkbox('Normalize age equation to 28 days',key='normalise_age')
try:
    constants=selected_constants()
    if mode=='Mode B':
        values=material_widgets('b')
        inputs=mode_b_inputs_from_widgets(values,unit_system)
        render_report(run_mode_b(inputs,constants=constants,policy=policy,normalise_age_to_28d=normalise),unit_system)
    elif mode=='Mode A':
        mode_a_page(unit_system,convention,policy,normalise,constants)
    else:
        calibration_page()
except (ValueError,KeyError,OverflowError,OSError) as error:
    st.error(str(error))
