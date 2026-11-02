"""The web transport must preserve engine numbers and provenance."""
import json
from pathlib import Path
import pytest
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient
from concretecalc_web.api import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(calibrations_dir=tmp_path))


def test_metadata_and_health(client):
    assert client.get('/api/v1/health').json()['status']=='ok'
    data=client.get('/api/v1/metadata').json()
    assert data['defaults_b']['aggregate_weight_basis']=='as_received'
    assert len(data['examples'])>=2
    assert data['disclaimer']


def test_api_matches_recorded_baseline(client):
    baseline=json.loads((Path(__file__).parent/'fixtures/web_baseline.json').read_text())
    for case in baseline['cases']:
        response=client.post('/api/v1/design',json={'inputs':case['inputs']})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['report']['cement']['cement_kg_m3']==pytest.approx(case['cement_kg_m3'],abs=1e-9)
        assert result['prediction']['wc']==pytest.approx(case['wc'],abs=1e-12)
        for name,value in case['strengths_mpa'].items():
            assert result['prediction']['predictions'][name]['mean_28d_mpa']==pytest.approx(value,abs=1e-9)
        report=result['prediction']
        assert result['visuals']['water'][-1]['value']==report['water']['effective_water_kg']
        predicted=client.post('/api/v1/predict',json={'inputs':report['inputs']})
        assert predicted.status_code==200
        assert predicted.json()['report']['wc']==pytest.approx(case['wc'],abs=1e-12)


def test_structured_errors(client):
    invalid=client.post('/api/v1/predict',json={'inputs':{}})
    assert invalid.status_code==422 and invalid.json()['error']['fields']
    inputs=client.get('/api/v1/metadata').json()['defaults_b']
    inputs['water_kg']=0
    invalid=client.post('/api/v1/predict',json={'inputs':inputs})
    assert invalid.status_code==422
    assert 'water' in invalid.json()['error']['message']


def test_synthetic_calibration_lifecycle(client):
    demo=client.get('/api/v1/demo/calibration.csv')
    upload=client.post('/api/v1/calibration/validate',files={'file':('demo.csv',demo.content,'text/csv')})
    assert upload.status_code==200,upload.text
    data=upload.json()
    assert data['valid_count']==12 and not data['errors']
    fit=client.post('/api/v1/calibration/fit',json={'dataset_id':data['dataset_id'],'material_set_id':'SYNTHETIC-DEMO','age_policy':'only_28d'})
    assert fit.status_code==200,fit.text
    result=fit.json()
    assert set(result['results'])=={'abrams','bolomey','feret'}
    assert len(result['diagnostics']['abrams'])==12
    save=client.post('/api/v1/calibration/save',json={'fit_id':result['fit_id']})
    assert save.status_code==200
    assert client.get('/api/v1/calibrations').json()['items']==['SYNTHETIC-DEMO']
    stale=client.post('/api/v1/calibration/save',json={'fit_id':'unknown'})
    assert stale.status_code==404


def test_upload_limits_and_unknown_format(client):
    assert client.post('/api/v1/calibration/validate',files={'file':('bad.txt',b'hello')}).status_code==422
    response=client.post('/api/v1/calibration/validate',files={'file':('large.csv',b'x'*(10*1024*1024+1))})
    assert response.status_code==413
