"""Build the frozen Nepal case from retained source bytes. SI-assisted code."""
import hashlib
import json
from pathlib import Path
import sys

import rasterio
import numpy as np
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'trend_lab'))
from analysis import annual_values, fit_series

PACK = ROOT / 'UI/nepal/data'
RUN = 'event-fe47db331390'
VARIABLES = ('T2M', 'PRECTOTCORR')
START, END = 1984, 2025
SITE = (85.335, 28.17)
REGIONAL = 'https://power.larc.nasa.gov/api/temporal/monthly/regional?latitude-min=27&latitude-max=29&longitude-min=84&longitude-max=86&community=AG&start=1984&end=2025&format=JSON&parameters='
POINT = 'https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=85.335&latitude=28.17&start=1984&end=2025&format=JSON'
SOURCES = {
    't2m.json': ('fc61a6ff13ddfb970077a9326f1d00601a60dd5301f387031844420b6f264c38', REGIONAL + 'T2M'),
    'rainfall.json': ('8d65b18a901ba3291449ebda71001ab09ce1f1aec6090c6c77e01d59cb3bdd68', REGIONAL + 'PRECTOTCORR'),
    'syapru-point.json': ('aff7ce7af840014b3af2ebc1d674f56b8357b4cf8e55e77409709e376408f185', POINT),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_source(name):
    raw = (PACK / name).read_bytes()
    expected, url = SOURCES[name]
    checksum = digest(raw)
    if expected and checksum != expected:
        raise ValueError(f'NASA source checksum mismatch: {name}')
    data = json.loads(raw)
    header = data['header']
    if header['sources'] != ['MERRA2'] or (header['start'], header['end']) != ('19840101', '20251231'):
        raise ValueError(f'Unexpected NASA product or period: {name}')
    return data, {'file': name, 'url': url, 'sha256': checksum, 'bytes': len(raw),
                  'api_version': header['api']['version'], 'source': header['sources'][0]}


def month_keys():
    return [f'{year}{month:02}' for year in range(START, END + 1) for month in range(1, 13)]


def match_regional_point(point, payload, variable):
    selected = point['properties']['parameter'][variable]
    months = month_keys()
    matching = [feature['geometry']['coordinates'][:2] for feature in payload['features']
                if all(selected[key] == feature['properties']['parameter'][variable][key] for key in months)]
    if len(matching) != 1:
        raise ValueError(f'Syapru must match exactly one {variable} series')
    return tuple(matching[0])


def fit_cell(payload, feature, variable):
    annual, missing = annual_values({**payload, 'properties': feature['properties']}, variable, START, END)
    result = fit_series(annual)
    subperiods = []
    for start, end in ((1984, 2004), (2005, 2025)):
        section = [point for point in annual if start <= point['year'] <= end]
        slope = None
        if len(section) == end - start + 1:
            x = np.array([point['year'] for point in section], dtype=float)
            y = np.array([point['value'] for point in section], dtype=float)
            slope = float(np.polyfit(x - x.mean(), y, 1)[0] * 10)
        subperiods.append({'period': [start, end], 'slope_per_decade': slope})
    return {'annual': annual, 'missing_years': missing, 'descriptive_subperiods': subperiods, **result}


def add_adjusted_results(cells):
    rows = [row for cell in cells for row in cell['trends'].values()]
    for lag in ('1', '3', '5'):
        raw = [row['hac_sensitivity'][lag]['p'] if row['status'] == 'ok' else 1.0 for row in rows]
        corrected = multipletests(raw, method='holm')[1]
        for row, p_adjusted in zip(rows, corrected, strict=True):
            if row['status'] == 'ok':
                row['hac_sensitivity'][lag]['p_adjusted'] = float(p_adjusted)
                if lag == '3':
                    row['p_adjusted'] = float(p_adjusted)
                    row['significant'] = bool(p_adjusted < 0.05)


def build_trends():
    point, point_source = read_source('syapru-point.json')
    if tuple(point['geometry']['coordinates'][:2]) != SITE:
        raise ValueError('Unexpected Syapru point request coordinates')
    cells = {}
    matches = []
    sources = {'point_check': point_source}
    for variable, name in zip(VARIABLES, ('t2m.json', 'rainfall.json'), strict=True):
        payload, sources[variable] = read_source(name)
        grid = set()
        matches.append(match_regional_point(point, payload, variable))
        for feature in payload['features']:
            lng, lat = feature['geometry']['coordinates'][:2]
            if (lng, lat) in grid:
                raise ValueError('Duplicate NASA grid centre')
            grid.add((lng, lat))
            cells.setdefault((lng, lat), {'lon': lng, 'lat': lat, 'trends': {}})
            cells[lng, lat]['trends'][variable] = fit_cell(payload, feature, variable)
        expected_grid = {(lng, lat) for lng in (84.375, 85.0, 85.625) for lat in (27, 27.5, 28, 28.5, 29)}
        if grid != expected_grid:
            raise ValueError('NASA grid differs from the fixed analysis population')
    if matches[0] != matches[1]:
        raise ValueError('The two variables disagree on the matched Syapru grid centre')
    ordered = []
    for index, coordinate in enumerate(sorted(cells, key=lambda pair: (-pair[1], pair[0])), start=1):
        cell = cells[coordinate]
        cell['id'] = f'c{index:02d}'
        ordered.append(cell)
    add_adjusted_results(ordered)
    return {'period': [START, END], 'request_box': [84, 27, 86, 29], 'grid_step': [0.625, 0.5],
            'site': {'name': 'Syapru Besi', 'requested_lon_lat': list(SITE),
                     'matching_cell': cells[matches[0]]['id'], 'matched_months_per_variable': len(month_keys())},
            'sources': sources, 'cells': ordered,
            'method': {'alpha': 0.05, 'tests_per_family': 30, 'primary_lag': 3, 'diagnostic_lags': [1, 5],
                       'fit': 'OLS on calendar-weighted annual data. Bartlett HAC with finite-sample correction and Student t reference.',
                       'multiple_testing': 'Holm across 15 cells × 2 variables at lag 3. Lags 1 and 5 each use their own 30-test diagnostic correction.',
                       'coverage': 'A year requires 12 usable months. The inherited fit requires at least 20 consecutive annual values. Failed fits enter Holm as p=1 and receive no verdict.',
                       'scope': 'Exploratory results for one product and fixed window. Slope intervals are marginal. Separate cell tests do not test a difference between cells.'}}


def build_event():
    folder = ROOT / 'components/floodlab/artifacts/runs' / RUN
    freeze = json.loads((folder / 'freeze.json').read_bytes())
    names = ('pre.png', 'post.png', 'manifest.json', 'result.json', 'sensitivity.json', 'prediction.tif', 'exposure.csv')
    for name in names:
        if digest((folder / name).read_bytes()) != freeze['files'][name]:
            raise ValueError(f'Saved event checksum mismatch: {name}')
    run = json.loads((folder / 'result.json').read_bytes())
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    summary = run['summary']
    with rasterio.open(folder / 'prediction.tif') as dataset:
        mask = dataset.read(1)
        if dataset.crs.to_epsg() != 32645 or dataset.res != (10, 10) or dataset.nodata is None:
            raise ValueError('Unexpected event raster support')
        values = set(np.unique(mask).tolist())
        if not values <= {0, 1, 2, 3, dataset.nodata}:
            raise ValueError('Unexpected event raster codes')
        recounted = {'valid_pixels': int(np.count_nonzero(mask != dataset.nodata)), 'total_pixels': int(mask.size),
                     'new_water_pixels': int(np.count_nonzero(mask == 2))}
    if any(summary[key] != value for key, value in recounted.items()) or summary['new_water_m2'] != recounted['new_water_pixels'] * 100:
        raise ValueError('Event raster recount disagrees with the frozen summary')
    case = json.loads((ROOT / 'data/views/nepal.json').read_bytes())
    sar = []
    for role, name in [('pre', 'before.png'), ('post', 'after.png')]:
        (PACK / name).write_bytes((folder / (role + '.png')).read_bytes())
        sar.append({'date': manifest[role]['datetime'][:10], 'source': manifest[role]['scene_id'],
                    'file': name, 'sha256': freeze['files'][role + '.png']})
    return {'run_id': RUN, 'date': '2026-08-26', 'sar': sar, 'raster_resolution_m': 10,
            'metrics': {key: summary[key] for key in (*recounted, 'new_water_m2', 'exposed_buildings', 'exposed_road_m')},
            'optical_coverage': [{'date': row['date'], 'clear_pixels': row['clear_pixels'],
                                  'total_grid_pixels': row['total_grid_pixels']} for row in case['observations']],
            'mask_sensitivity': json.loads((folder / 'sensitivity.json').read_bytes()),
            'verified_artifacts': {name: freeze['files'][name] for name in names},
            'connectivity_status': 'Not assessed in this run',
            'interpretation': 'Fixed threshold, one radar pair. The recount verifies run arithmetic. Candidate overlap with mapped assets does not establish damage or closure. Independent event accuracy remains unestablished.'}


def main():
    data = {'schema': 1, 'si_disclosure': 'OpenAI Codex assisted implementation and documentation. Original NASA source values and carried-forward satellite evidence retain their provenance.',
            'climate': build_trends(), 'event': build_event()}
    (PACK / 'case.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    print(f"Nepal bundle: {len(data['climate']['cells'])} matched centres, 30 tests, {data['event']['metrics']['new_water_pixels']} recounted water candidates")


if __name__ == '__main__':
    main()
