"""Holdout independence and archival behavior, without a new fitting equation."""
import csv
import io
import json
import pytest
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient
from concretecalc_web.api import create_app
from concretecalc_web.calibration_review import DiagnosticPoint,diagnostic_metrics


def upload(client, rows):
    text=io.StringIO(newline='')
    writer=csv.DictWriter(text,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    response=client.post('/api/v1/calibration/validate',files={'file':('lab.csv',text.getvalue().encode('utf-8'))})
    assert response.status_code==200,response.text
    return response.json()['dataset_id']


def test_group_holdout_prevents_mix_and_target_leakage(tmp_path):
    client=TestClient(create_app(calibrations_dir=tmp_path))
    rows=list(csv.DictReader(io.StringIO(client.get('/api/v1/demo/calibration.csv').text)))
    rows=rows+[dict(row) for row in rows]  # Repeated observations must stay with their mix.
    body={'dataset_id':upload(client,rows),'material_set_id':'SYNTHETIC-DEMO','models':['abrams'],'validation_mode':'group_holdout'}
    first=client.post('/api/v1/calibration/fit',json=body)
    assert first.status_code==200,first.text
    fit=first.json()
    train=set(fit['context']['train_mix_ids'])
    test=set(fit['context']['test_mix_ids'])
    assert len(train)==10 and len(test)==2 and not train & test
    assert fit['results']['abrams']['n_rows']==20
    assert fit['metrics']['abrams']['held_out']['n']==4
    for row in rows:
        if row['mix_id'] in test:
            row['measured_strength_mpa']=str(float(row['measured_strength_mpa'])*1.5)
    body['dataset_id']=upload(client,rows)
    second=client.post('/api/v1/calibration/fit',json=body).json()
    assert second['results']['abrams']['values']==pytest.approx(fit['results']['abrams']['values'],abs=1e-12)
    assert second['metrics']['abrams']['held_out']['rmse_mpa']>fit['metrics']['abrams']['held_out']['rmse_mpa']
    body['dataset_id']=upload(client,rows[:4])
    assert client.post('/api/v1/calibration/fit',json=body).status_code==422


def test_saved_revisions_retain_context_and_require_explicit_replacement(tmp_path):
    client=TestClient(create_app(calibrations_dir=tmp_path))
    demo=client.get('/api/v1/demo/calibration.csv')
    data=client.post('/api/v1/calibration/validate',files={'file':('demo.csv',demo.content)}).json()
    fit=client.post('/api/v1/calibration/fit',json={'dataset_id':data['dataset_id'],'material_set_id':'SYNTHETIC-DEMO'}).json()
    assert client.post('/api/v1/calibration/save',json={'fit_id':fit['fit_id']}).status_code==200
    original=(tmp_path/'SYNTHETIC-DEMO.json').read_bytes()
    assert client.post('/api/v1/calibration/save',json={'fit_id':fit['fit_id']}).status_code==409
    assert (tmp_path/'SYNTHETIC-DEMO.json').read_bytes()==original
    saved=client.post('/api/v1/calibration/save',json={'fit_id':fit['fit_id'],'replace_existing':True})
    assert saved.json()['revision']==2
    raw=json.loads((tmp_path/'SYNTHETIC-DEMO.json').read_text())
    assert len(raw['revision_history'])==1
    assert raw['models']['abrams']['fit_context']['age_policy']=='only_28d'
    inputs=client.get('/api/v1/metadata').json()['defaults_b']
    inputs['air_entrained']=True
    assert client.post('/api/v1/predict',json={'inputs':inputs,'options':{'calibration_id':'SYNTHETIC-DEMO'}}).status_code==422


def test_constant_target_r2_and_upload_rejections(tmp_path):
    points=[DiagnosticPoint(mix_id='A',measured_mpa=2,predicted_mpa=2,default_mpa=1,residual_mpa=0,split='calibration'),
            DiagnosticPoint(mix_id='B',measured_mpa=2,predicted_mpa=3,default_mpa=1,residual_mpa=-1,split='calibration')]
    result=diagnostic_metrics(points)
    assert result.r2_mpa is None
    assert result.mae_mpa==pytest.approx(.5,abs=1e-12)
    assert result.rmse_mpa==pytest.approx(2**-.5,abs=1e-12)
    client=TestClient(create_app(calibrations_dir=tmp_path))
    malformed=client.post('/api/v1/calibration/validate',files={'file':('broken.xlsx',b'not a zip')})
    assert malformed.status_code==422
    large=client.post('/api/v1/calibration/validate',files={'file':('too-many.csv',b'mix_id\n'+b'x\n'*5001)})
    assert large.status_code==422 and '5,000' in large.json()['error']['message']
