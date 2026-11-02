"""Synthetic fitting, row errors, age conversion and persisted provenance."""
from dataclasses import replace
from pathlib import Path
import csv
import numpy as np
import pytest
from concretecalc.calibration.fit import fit_abrams, fit_bolomey, fit_feret, fit_all, comparison_table
pytest.importorskip('pandas',reason='Calibration dataset tests require the calibration extra')
from concretecalc.calibration.dataset import load_rows, rows_to_fit_arrays
from concretecalc.calibration.store import save_calibration, load_calibration, file_sha256

TEMPLATE = Path(__file__).resolve().parents[1]/'experiments'/'mix_log_template.csv'


def test_noisy_synthetic_fit():
    rng = np.random.default_rng(15)
    wc = np.linspace(.3,.8,100)
    result = fit_abrams(wc,100/10**wc*np.exp(rng.normal(0,.03,len(wc))))
    assert result.values == pytest.approx({'A':100,'B':10},rel=.1)
    assert result.r2 > .95 and result.r2_space == 'log'
    assert fit_bolomey(1/wc,20*(1/wc-.5)).values['K'] == pytest.approx(20,rel=.05)
    assert fit_feret(wc,230*wc**2).values['K'] == pytest.approx(230,rel=.05)


def test_template_and_error_accumulation(tmp_path):
    rows, errors = load_rows(TEMPLATE)
    assert len(rows)==2 and not errors
    with TEMPLATE.open() as source:
        data=list(csv.DictReader(source))
    data[0].update(cement_kg_m3='-1',water_kg_m3='nan',weight_basis='unknown')
    bad=tmp_path/'bad.csv'
    with bad.open('w',newline='') as target:
        writer=csv.DictWriter(target,fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    valid, errors=load_rows(bad)
    assert len(valid)==1
    assert {e[1] for e in errors} >= {'cement_kg_m3','water_kg_m3','weight_basis'}
    assert all(e[0]==2 for e in errors)


def test_arrays_age_policy_and_cube():
    rows,_=load_rows(TEMPLATE)
    first=rows[0]
    data=(first,replace(first,age_days=7,measured_strength_mpa=first.measured_strength_mpa*7/(4+.85*7)),
          replace(first,cement_kg_m3=400,measured_strength_mpa=40))
    assert len(rows_to_fit_arrays(data).wc)==2
    arrays=rows_to_fit_arrays(data,'convert')
    assert arrays.strength_mpa[0] == pytest.approx(arrays.strength_mpa[1],abs=1e-12)
    assert set(fit_all(arrays))=={'abrams','bolomey','feret'}
    assert len(comparison_table(fit_all(arrays)))==3
    with pytest.raises(ValueError):
        fit_all(rows_to_fit_arrays(data))
    cube=replace(first,specimen='cube_150',cube_to_cylinder_factor=.8)
    assert rows_to_fit_arrays((cube,)).strength_mpa[0] == pytest.approx(first.measured_strength_mpa*.8,abs=1e-12)
    with pytest.raises(ValueError,match='material_set_id'):
        rows_to_fit_arrays((first,replace(first,material_set_id='other')))


def test_store_round_trip_and_model_merge(tmp_path):
    result=fit_abrams(np.array([.3,.4,.5]),100/10**np.array([.3,.4,.5]))
    path=save_calibration('materials-1','abrams',result,'source.csv','abc',tmp_path)
    loaded=load_calibration('materials-1','abrams',tmp_path)
    assert loaded.calibrated and loaded.material_set_id=='materials-1'
    assert loaded.values==result.values
    other=fit_bolomey(np.array([2,3,4]),np.array([30,50,70]))
    save_calibration('materials-1','bolomey',other,'source.csv','abc',tmp_path)
    assert load_calibration('materials-1','abrams',tmp_path).values==result.values
    assert len(file_sha256(path))==64
    with pytest.raises(ValueError,match='material_set_id'):
        save_calibration('../escape','abrams',result,'source.csv','abc',tmp_path)


def test_cube_factor_missing_columns_and_reserved_values(tmp_path):
    with TEMPLATE.open() as source:
        data=list(csv.DictReader(source))
    data[0].update(specimen='cube_150',scm_name='reserved',scm_pct='not modeled')
    path=tmp_path/'cubes.csv'
    def write():
        with path.open('w',newline='') as target:
            writer=csv.DictWriter(target,fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    write()
    rows,errors=load_rows(path)
    assert len(rows)==1 and errors[0][1]=='cube_to_cylinder_factor'
    for row in data:
        row['cube_to_cylinder_factor']='.8'
    write()
    rows,errors=load_rows(path)
    assert len(rows)==2 and not errors
    path.write_text('mix_id\nonly-id\n')
    rows,errors=load_rows(path)
    assert not rows and len(errors)>1 and all(e[0]==1 for e in errors)


def test_excel_round_trip(tmp_path):
    pytest.importorskip('openpyxl')
    import pandas as pd
    frame=pd.read_csv(TEMPLATE,keep_default_na=False)
    path=tmp_path/'records.xlsx'
    frame.to_excel(path,index=False)
    rows,errors=load_rows(path)
    assert len(rows)==2 and not errors
