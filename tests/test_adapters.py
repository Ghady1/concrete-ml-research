"""Unit boundaries and Streamlit interaction smoke tests."""
from pathlib import Path
import csv
import io
import pytest
from app.adapters import (DEFAULT_VALUES, mode_b_inputs_from_widgets,
    mode_a_inputs_from_widgets, report_rows_for_display, report_to_csv_text, default_air_pct)
from concretecalc.mode_b import run_mode_b
from concretecalc import units as u


def test_si_defaults_and_csv():
    inputs=mode_b_inputs_from_widgets({},'SI')
    report=run_mode_b(inputs)
    assert inputs.aggregate_weight_basis=='as_received'
    assert inputs.cement.weight_kg==350
    assert report_rows_for_display(report,'SI')
    rows=list(csv.reader(io.StringIO(report_to_csv_text(report))))
    assert rows[0]==['section','quantity','value']
    assert any('DISCLAIMER' in row for row in rows)
    assert default_air_pct(19,'moderate',True)==5


def test_us_content_adapter():
    values=dict(DEFAULT_VALUES)
    for key in ('cement_kg','water_kg','coarse_kg','fine_kg'):
        values[key]=u.kg_m3_to_lb_yd3(values[key])
    values['coarse_drd_kg_m3']=u.kg_m3_to_pcf(values['coarse_drd_kg_m3'])
    values['nmas_mm']=u.mm_to_in(values['nmas_mm'])
    values['sigma_mpa']=u.mpa_to_psi(2.4)
    inputs=mode_b_inputs_from_widgets(values,'US')
    assert inputs.cement.weight_kg==pytest.approx(350,rel=1e-12)
    assert inputs.coarse.drd_kg_m3==pytest.approx(1600,rel=1e-12)
    assert inputs.nmas_mm==pytest.approx(19,rel=1e-12)
    assert inputs.sigma_mpa==pytest.approx(2.4,rel=1e-12)


def test_us_declared_batch_adapter():
    values=dict(DEFAULT_VALUES)
    for key in ('cement_kg','water_kg','coarse_kg','fine_kg'):
        values[key]=u.kg_to_lb(values[key]*.1)
    values.update(batch_volume_m3=u.m3_to_yd3(.1),nmas_mm=u.mm_to_in(19),
                  coarse_drd_kg_m3=u.kg_m3_to_pcf(1600))
    report=run_mode_b(mode_b_inputs_from_widgets(values,'US'))
    assert report.cement_kg_m3==pytest.approx(350,rel=1e-12)


def test_mode_a_units():
    values=dict(DEFAULT_VALUES)
    values.update(specified_fc_mpa=u.mpa_to_psi(25),nmas_mm=u.mm_to_in(19),
                  coarse_drd_kg_m3=u.kg_m3_to_pcf(1600),batch_volume_m3=u.m3_to_yd3(.1))
    inputs=mode_a_inputs_from_widgets(values,'US')
    assert inputs.specified_fc_mpa==pytest.approx(25,rel=1e-12)
    assert inputs.batch_volume_m3==pytest.approx(.1,rel=1e-12)


def test_streamlit_mode_b_defaults():
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app'/'streamlit_app.py'))
    app.run(timeout=45)
    assert not app.exception
    assert len(app.metric)>=3
    app.number_input(key='b_cement_kg').set_value(400).run(timeout=45)
    app.sidebar.selectbox(key='unit_system').select('US').run(timeout=45)
    assert not app.exception
    assert app.number_input(key='b_cement_kg').value==pytest.approx(u.kg_m3_to_lb_yd3(400),rel=1e-12)
    app.checkbox(key='b_ae').check().run(timeout=45)
    assert app.number_input(key='b_air_pct').value==5
    app.checkbox(key='b_override_air').check().run(timeout=45)
    app.number_input(key='b_air_pct').set_value(6).run(timeout=45)
    app.number_input(key='b_nmas_mm').set_value(u.mm_to_in(25)).run(timeout=45)
    assert not app.exception
    assert app.number_input(key='b_air_pct').value==6


def test_streamlit_mode_a_and_prediction():
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app'/'streamlit_app.py'))
    app.run(timeout=45)
    app.sidebar.selectbox(key='mode').select('Mode A').run(timeout=45)
    assert not app.exception
    assert any('10.' in expander.label for expander in app.expander)
    app.button(key='predict_design').click().run(timeout=45)
    assert not app.exception
    assert len(app.metric)>=6
    assert any(any('Difference from required mean' in str(column) for column in table.value.columns)
               for table in app.table)
    app.sidebar.selectbox(key='unit_system').select('US').run(timeout=45)
    assert not app.exception


def test_streamlit_calibration_page():
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app'/'streamlit_app.py'))
    app.run(timeout=45)
    app.sidebar.selectbox(key='mode').select('Calibration').run(timeout=45)
    assert not app.exception
    assert any('Calibration' in heading.value for heading in app.header)


def test_streamlit_upload_fit_and_save(tmp_path,monkeypatch):
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    from concretecalc.calibration import store
    real_save=store.save_calibration
    def save_in_test_directory(material,name,result,source,data_hash,directory):
        return real_save(material,name,result,source,data_hash,tmp_path)
    monkeypatch.setattr(store,'save_calibration',save_in_test_directory)
    root=Path(__file__).resolve().parents[1]
    with (root/'experiments'/'mix_log_template.csv').open() as source:
        rows=list(csv.DictReader(source))
    third=dict(rows[1])
    third.update(mix_id='synthetic-third',cement_kg_m3='450',measured_strength_mpa='42')
    rows.append(third)
    text=io.StringIO(newline='')
    writer=csv.DictWriter(text,fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    app=AppTest.from_file(str(root/'app'/'streamlit_app.py')).run(timeout=45)
    app.sidebar.selectbox(key='mode').select('Calibration').run(timeout=45)
    app.file_uploader(key='calibration_upload').set_value(('synthetic.csv',text.getvalue().encode(),'text/csv')).run(timeout=45)
    assert not app.exception
    assert not app.button(key='fit_models').disabled
    app.button(key='fit_models').click().run(timeout=45)
    assert not app.exception
    app.button(key='save_fits').click().run(timeout=45)
    assert not app.exception and len(app.success)==1
    loaded=store.load_calibration('EXAMPLE-SYNTHETIC-DELETE','abrams',tmp_path)
    assert loaded.calibrated


def test_streamlit_selects_stored_calibration():
    pytest.importorskip('streamlit')
    import uuid
    import numpy as np
    from streamlit.testing.v1 import AppTest
    from concretecalc.calibration.fit import fit_abrams
    from concretecalc.calibration.store import save_calibration
    root=Path(__file__).resolve().parents[1]
    material='pytest-'+uuid.uuid4().hex
    directory=root/'calibrations'
    path=directory/(material+'.json')
    assert not path.exists()
    try:
        wc=np.array([.3,.4,.5])
        fit=fit_abrams(wc,100/10**wc)
        save_calibration(material,'abrams',fit,'synthetic.csv','a'*64,directory)
        app=AppTest.from_file(str(root/'app'/'streamlit_app.py')).run(timeout=45)
        app.sidebar.selectbox(key='calibrated_set').select(material).run(timeout=45)
        assert not app.exception
        assert any(material in caption.value for caption in app.caption)
    finally:
        if path.exists():
            path.unlink()
