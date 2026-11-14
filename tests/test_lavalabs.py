"""Controls for the new integration; source correctness is a separate question."""
import hashlib
import json
import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from lavalabs.server import create_app
from lavalabs.public_runs import DemoBridge, DEMO_RUNS
from jai_extension.flood_bridge import BridgeError
from scripts.bootstrap_demo import contained

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def client():
    with TestClient(create_app()) as value:yield value

@pytest.mark.parametrize('case', ['nepal','kedarnath','varanasi','sangam-vihar'])
def test_measured_case_contract(client,case):
    response=client.get(f'/api/lava/cases/{case}/view')
    assert response.status_code==200
    assert hashlib.sha256(response.content).hexdigest()==response.headers['x-artifact-sha256']
    data=response.json()
    assert set(data['fields'])=={'elevation','slope','hand','ndvi_before','ndvi_after','ndvi_change'}
    assert data['terrain_product']==('NASADEM_HGT_v001' if case=='kedarnath' else 'CopernicusGLO30')
    rows=len(data['elevation']);columns=len(data['elevation'][0])
    assert 1<rows<=150 and 1<columns<=150
    for layer in data['fields'].values():
        assert len(layer['values'])==rows
        for row in layer['values']:
            assert len(row)==columns
            assert all(value is None or math.isfinite(value) for value in row)
    before=data['fields']['ndvi_before']['values'];after=data['fields']['ndvi_after']['values'];delta=data['fields']['ndvi_change']['values']
    valid=0
    for r in range(rows):
        for c in range(columns):
            if before[r][c] is not None and after[r][c] is not None:
                assert abs(delta[r][c]-(after[r][c]-before[r][c]))<0.000003
                valid+=1
            else:assert delta[r][c] is None
    assert valid>0

def test_private_paths_and_unknown_cases(client):
    for path in ['/research/datasets/local/','/.env','/provenance/migration.json','/api/lava/cases/fake/view','/api/lava/reports/fake']:
        assert client.get(path).status_code==404
    assert client.get('/api/lava/research',headers={'Origin':'https://unrelated.example'}).status_code==403
    question={'question':'Summarize this area','run_id':'private-archive-run'}
    assert client.post('/api/investigations',json=question).status_code==404

def test_archive_boundary_is_explicit():
    bridge=DemoBridge('http://127.0.0.1:8781')
    for run in DEMO_RUNS:bridge.require(run)
    with pytest.raises(BridgeError) as error:bridge.require('private-archive-run')
    assert error.value.status==404

@pytest.mark.parametrize('name',['../escape','/tmp/escape','.runtime/jai/terrain/../../../../escape',r'.runtime\jai\terrain\escape','research/datasets/local/example'])
def test_bootstrap_rejects_outside_members(name,tmp_path):
    with pytest.raises(ValueError):contained(name,tmp_path)

def test_bundled_data_contains_only_declared_members():
    import zipfile
    manifest=json.loads((ROOT/'data/demo/manifest.json').read_text())
    archive=ROOT/'data/demo'/manifest['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with zipfile.ZipFile(archive) as source:
        assert set(source.namelist())==set(manifest['files'])
        assert all(contained(name).is_relative_to(ROOT) for name in source.namelist())

def test_named_reports_and_prior_work(client):
    data=client.get('/api/lava/research').json()
    assert data['prior_work'] is True and len(data['studies'])==6
    for row in data['studies']:
        assert client.get(row['report']).status_code==200

def test_trend_export_matches_frozen_comparison(client):
    route='/api/lava/trends/delhi/PRECTOTCORR/0/'
    receipt=client.get(route+'json')
    assert receipt.status_code==200 and 'attachment' in receipt.headers['content-disposition']
    data=receipt.json()
    frozen=json.loads((ROOT/'trend_lab/web/data/analysis.json').read_text())['windows'][0]
    assert data['period']==[1984,2025] and data['result'] in frozen['results']
    csv=client.get(route+'csv')
    assert csv.status_code==200 and len(csv.text.splitlines())==43
    assert client.get('/api/lava/trends/delhi/PRECTOTCORR/3/csv').status_code==404
