"""Verify the Nepal bundle and its independent trend calculation."""
import hashlib
import csv
import io
import json
from pathlib import Path

import numpy as np
from scipy.stats import t
from fastapi.testclient import TestClient

from lavalabs.server import create_app
from scripts import build_nepal_case as builder

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'UI/nepal/data'
CASE = json.loads((PACK / 'case.json').read_bytes())


def independent_hac(annual):
    values = np.array([point['value'] for point in annual])
    years = np.array([point['year'] for point in annual])
    design = np.column_stack((np.ones(years.size), years - years.mean()))
    beta = np.linalg.lstsq(design, values, rcond=None)[0]
    residuals = values - design @ beta
    scores = design * residuals[:, None]
    meat = scores.T @ scores
    for lag in range(1, 4):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / 4) * (cross + cross.T)
    inverse = np.linalg.inv(design.T @ design)
    variance = (inverse @ meat @ inverse)[1, 1] * years.size / (years.size - 2)
    error = variance ** .5
    p = 2 * t.sf(abs(beta[1] / error), df=years.size - 2)
    return beta[1] * 10, p


def test_every_frozen_result_matches_independent_hac_and_holm():
    rows = [row for cell in CASE['climate']['cells'] for row in cell['trends'].values()]
    checked = [independent_hac(row['annual']) for row in rows]
    assert len(rows) == 30
    order = sorted(range(len(rows)), key=lambda index: checked[index][1])
    running = 0.0
    for rank, index in enumerate(order):
        row = rows[index]
        slope, p = checked[index]
        running = max(running, min(1, (len(rows) - rank) * p))
        assert np.isclose(row['slope_per_decade'], slope, atol=1e-9)
        assert np.isclose(row['p_adjusted'], running, atol=1e-11)
        assert row['significant'] == (running < 0.05)


def test_source_and_syapru_identity_and_incomplete_series():
    c = CASE['climate']
    for source in c['sources'].values():
        assert hashlib.sha256((PACK / source['file']).read_bytes()).hexdigest() == source['sha256']
    point, _ = builder.read_source('syapru-point.json')
    sites = []
    for variable, name in [('T2M', 't2m.json'), ('PRECTOTCORR', 'rainfall.json')]:
        raw, _ = builder.read_source(name)
        sites.append(builder.match_regional_point(point, raw, variable))
        feature = raw['features'][0]
        feature['properties']['parameter'][variable]['200105'] = raw['header']['fill_value']
        incomplete = builder.fit_cell(raw, feature, variable)
        assert incomplete['status'] == 'incomplete' and incomplete['missing_years'] == [2001]
        assert 'p' not in incomplete
    site = next(cell for cell in c['cells'] if cell['id'] == c['site']['matching_cell'])
    assert sites == [(85.625, 28.0)] * 2
    assert (site['lon'], site['lat']) == sites[0]
    assert site['trends']['PRECTOTCORR']['significant'] and not site['trends']['T2M']['significant']
    halves = site['trends']['PRECTOTCORR']['descriptive_subperiods']
    assert [round(item['slope_per_decade'], 1) for item in halves] == [-28.4, 128.7]


def test_public_page_and_published_evidence():
    event = CASE['event']
    assert event['metrics']['new_water_pixels'] == 956 and event['metrics']['new_water_m2'] == 95600
    assert event['connectivity_status'] == 'Not assessed in this run'
    with TestClient(create_app()) as client:
        assert 'Nepal investigation' in client.get('/nepal').text
        assert '/nepal' in client.get('/trends').text
        assert '/nepal' in client.get('/').text
        assert client.get('/ui/nepal/data/case.json').content == (PACK / 'case.json').read_bytes()
        for image in event['sar']:
            response = client.get(f"/ui/nepal/data/{image['file']}")
            assert response.status_code == 200 and hashlib.sha256(response.content).hexdigest() == image['sha256']
        source = CASE['climate']['site']['matching_cell']
        row = next(cell['trends']['PRECTOTCORR'] for cell in CASE['climate']['cells'] if cell['id'] == source)
        path = f'/api/lava/nepal/{source}/PRECTOTCORR'
        receipt = client.get(path + '/json')
        assert receipt.headers['content-disposition'].startswith('attachment')
        assert receipt.json()['climate']['result'] == row
        exported = list(csv.DictReader(io.StringIO(client.get(path + '/csv').text)))
        assert [{ 'year': int(item['year']), 'value': float(item['annual_value']) } for item in exported] == row['annual']
        assert client.get('/api/lava/nepal/c16/FAKE/csv').status_code == 404
