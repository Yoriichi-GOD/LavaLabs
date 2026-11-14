"""Download the selected Nepal cell and its evidence without live data access."""
import csv
from functools import lru_cache
import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

CASE = Path(__file__).resolve().parents[1] / 'UI/nepal/data/case.json'
router = APIRouter(prefix='/api/lava/nepal')


@lru_cache(maxsize=1)
def load_case():
    return json.loads(CASE.read_bytes())


@router.get('/{cell_id}/{variable}/{kind}')
def download(cell_id: str, variable: str, kind: str):
    if variable not in {'T2M', 'PRECTOTCORR'} or kind not in {'csv', 'json'}:
        raise HTTPException(404, 'Unknown Nepal export')
    case = load_case()
    climate = case['climate']
    cell = next((row for row in climate['cells'] if row['id'] == cell_id), None)
    if cell is None:
        raise HTTPException(404, 'Unknown Nepal grid cell')
    result = cell['trends'][variable]
    unit = 'degC' if variable == 'T2M' else 'mm/year'
    filename = f'lavalabs-nepal-{cell_id}-{variable}.{kind}'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    if kind == 'json':
        selected = {key: climate[key] for key in ('method', 'period', 'site', 'grid_step', 'request_box')}
        selected.update(sources=[climate['sources'][variable], climate['sources']['point_check']],
                        cell={key: cell[key] for key in ('id', 'lon', 'lat')},
                        variable=variable, annual_unit=unit, result=result)
        return JSONResponse({'schema': 1, 'type': 'LavaLabs Nepal investigation', 'si_disclosure': case['si_disclosure'],
                             'climate': selected, 'event': case['event'],
                             'inference_boundary': 'The NASA model record ends in 2025. The saved 2026 satellite pair supports candidate observations at local scale. Event attribution requires separate evidence.'}, headers=headers)
    buffer = io.StringIO()
    output = csv.writer(buffer)
    output.writerow(['year', 'annual_value', 'fitted_value', 'unit'])
    fit = {point['year']: point['value'] for point in result.get('fit', [])}
    for point in result['annual']:
        year = point['year']
        output.writerow([year, point['value'], fit.get(year, ''), unit])
    return Response(buffer.getvalue(), media_type='text/csv', headers=headers)
