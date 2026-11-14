"""Export the same frozen comparison shown in the NASA trends workspace."""
from functools import lru_cache
from pathlib import Path
import csv
import io
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

DATA = Path(__file__).resolve().parents[1] / 'trend_lab/web/data'
router = APIRouter(prefix='/api/lava/trends')


@lru_cache(maxsize=2)
def read(file):
    return json.loads((DATA / file).read_text(encoding='utf-8'))


@router.get('/{region}/{variable}/{window}/{format}')
def download(region: str, variable: str, window: int, format: str):
    windows = read('analysis.json')['windows']
    if not 0 <= window < len(windows) or format not in {'csv', 'json'}:
        raise HTTPException(404, 'Unknown trend export')
    comparison = windows[window]
    row = next((item for item in comparison['results']
                if item['region']['id'] == region and item['variable'] == variable), None)
    if row is None:
        raise HTTPException(404, 'Unknown trend comparison')
    start, end = comparison['start'], comparison['end']
    filename = f'lavalabs-{region}-{variable}-{start}-{end}.{format}'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    if format == 'json':
        entry = next(item for item in read('manifest.json')['entries'] if item['region']['id'] == region)
        return JSONResponse({'source': comparison['source'], 'method': comparison['method'],
                             'period': [start, end], 'variable': comparison['variables'][variable],
                             'result': row, 'manifest': entry}, headers=headers)
    text = io.StringIO()
    output = csv.writer(text)
    unit = 'C' if variable == 'T2M' else 'mm'
    output.writerow(['year', f'{variable}_{unit}', 'fitted_value'])
    for annual, fitted in zip(row['annual'], row['fit'], strict=True):
        output.writerow([annual['year'], annual['value'], fitted['value']])
    return Response(text.getvalue(), media_type='text/csv', headers=headers)
