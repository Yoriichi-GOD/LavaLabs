"""LavaLabs application: local owned services, fixed evidence stores and Scientific Noir.

SI-assisted implementation, OpenAI Codex. Original scientific outputs retain
their own provenance, dates, hashes and interpretation limits.
"""
from pathlib import Path
import hashlib
import json
import os
import re

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from jai_extension.server import attach
from jai_extension.terrain import TerrainStore
from jai_extension.terrain_exposure import TerrainExposureStore
from jai_extension.research_cases import CaseResearchStore, router as case_router, CASES
from .public_runs import DemoBridge
from .trend_exports import router as export_router
from .nepal_exports import router as nepal_export_router

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'UI'
FLOOD = ROOT / 'components/floodlab'
UPSTREAM = os.environ.get('LAVALABS_FLOOD_UPSTREAM', 'http://127.0.0.1:8781')


def read_json(path, limit=8*1024*1024):
    if not path.is_file():
        raise HTTPException(503, 'This evidence pack has not been prepared. Run scripts/prepare_case_views.py.')
    if path.stat().st_size > limit:
        raise HTTPException(413, 'Evidence file exceeds the inspection limit')
    return json.loads(path.read_text(encoding='utf-8'))


WORDMARK = 'LavaLabs Volcano Logo.png'


def logo_path():
    for name in ['logo.svg', 'logo.png', 'logo.webp', WORDMARK, 'volcano.svg', 'volcano.png', 'volcano.webp']:
        path = UI / 'assets' / name
        if path.is_file():
            return path
    return UI / 'assets' / 'volcano-placeholder.svg'


def with_brand(html):
    if logo_path().name != WORDMARK:
        return html
    html = html.replace('rel="icon" href="/logo"','rel="icon" href="/favicon.ico"')
    return html.replace('</head>', '<link rel="stylesheet" href="/ui/wordmark.css"></head>', 1)


REPORTS = {
    'spectral': ROOT/'research/results/exposure-verification-20261112/REPORT.md',
    'drainage': ROOT/'research/results/drainage-consistency-20261112/REPORT.md',
    'flow': ROOT/'research/results/drainage-validation-20261112/REPORT.md',
    'cases': ROOT/'research/results/case-campaign-20261107/REPORT.md',
    'validation': ROOT/'research/results/validation-closure-20261107/REPORT.md',
    'r3': ROOT/'research/researcher-3-final/integration/RESEARCHER_3_FINAL_FINDINGS.md',
}


def create_app():
    bridge = DemoBridge(UPSTREAM, include_archive=os.environ.get('LAVALABS_LOCAL_ARCHIVE') == '1')
    for receipt in (FLOOD/'data/jobs').glob('event-*.json'):
        if re.fullmatch(r'event-[a-f0-9]{12}', receipt.stem):
            bridge.allowed.add(receipt.stem)
    terrain = TerrainStore(ROOT/'.runtime/jai/terrain')
    exposure = TerrainExposureStore(ROOT/'.runtime/research-release/terrain-exposure')
    app = FastAPI(title='LavaLabs', version='0.1.0', docs_url='/api/docs', redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])

    @app.middleware('http')
    async def local_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        port = os.environ.get('LAVALABS_PORT', '8780')
        if origin and origin not in {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}:
            return JSONResponse({'detail': 'Use the LavaLabs local origin'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    attach(app, bridge, terrain, FLOOD, exposure, authorize_run=bridge.require)
    app.include_router(export_router)
    app.include_router(nepal_export_router)
    app.include_router(case_router(CaseResearchStore(ROOT/'research/results/case-campaign-20261107')))

    @app.get('/', response_class=HTMLResponse)
    def home():
        return HTMLResponse(with_brand((UI/'index.html').read_text(encoding='utf-8')), headers={'Cache-Control': 'no-store'})

    @app.get('/logo', include_in_schema=False)
    @app.get('/favicon.ico', include_in_schema=False)
    @app.get('/art/logo.png', include_in_schema=False)
    def logo(request: Request):
        path = logo_path()
        if path.name == WORDMARK and request.url.path == '/favicon.ico':
            path = UI / 'assets' / 'volcano-placeholder.svg'
        return FileResponse(path, headers={'Cache-Control': 'no-cache'})

    @app.get('/api/lava/status')
    def status():
        return {'project': 'LavaLabs', 'mode': 'local research workspace', 'cases': list(CASES),
                'terrain_scenes': terrain.status()['scenes'], 'flood': bridge.health(),
                'logo': logo_path().name, 'prior_work': True, 'science_accuracy': 'NOT_INDEPENDENTLY_VALIDATED'}

    @app.get('/api/status')
    def legacy_status():
        return {'state': 'saved evidence and local processing', 'lab_port': 8780}

    @app.get('/api/lava/cases/{case}/view')
    def case_view(case: str):
        if case not in CASES:
            raise HTTPException(404, 'Unknown case')
        path = ROOT/'data/views'/f'{case}.json'
        manifest = read_json(ROOT/'data/views/manifest.json')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest['files'].get(path.name):
            raise HTTPException(409, 'Case-view integrity mismatch; rebuild from the retained inputs')
        return FileResponse(path, headers={'Cache-Control': 'no-cache', 'X-Artifact-SHA256': manifest['files'][path.name]})

    @app.get('/api/lava/research')
    def research():
        return read_json(ROOT/'data/views/research.json')

    @app.get('/api/lava/reports/{name}')
    def report(name: str):
        path = REPORTS.get(name)
        if path is None or not path.is_file():
            raise HTTPException(404, 'Unknown report')
        return FileResponse(path, media_type='text/markdown', filename=f'lavalabs-{name}-source-report.md')

    @app.get('/trends', response_class=HTMLResponse)
    def trends():
        html = (UI/'trends/index.html').read_text(encoding='utf-8')
        html = html.replace('<span class="snapshot">Frozen real-data demonstration</span>',
                            '<a class="text-link" href="/nepal">Explore the Nepal investigation ↗</a>', 1)
        return HTMLResponse(with_brand(html), headers={'Cache-Control': 'no-store'})

    @app.get('/nepal', response_class=HTMLResponse)
    def nepal():
        return HTMLResponse(with_brand((UI/'nepal/index.html').read_text(encoding='utf-8')), headers={'Cache-Control': 'no-store'})

    @app.get('/processor', response_class=HTMLResponse)
    def processor():
        html = (FLOOD/'web/index.html').read_text(encoding='utf-8')
        html = html.replace('/assets/', '/processor-assets/').replace('/art/', '/processor-art/')
        html = html.replace('/processor-art/logo.png', '/logo').replace('SatQuery AI', 'LavaLabs').replace('SATquery', 'LavaLabs').replace('SatQuery', 'LavaLabs')
        html = html.replace('<option value="auto">AI selects topic</option>', '<option value="auto">Match a supported topic</option>')
        html = html.replace('</head>', '<link rel="stylesheet" href="/ui/processor.css"><script defer src="/ui/processor-lava.js"></script></head>')
        html = html.replace('</nav>', '<a class="lava-back" href="/#terrain">Terrain & cases</a><a class="lava-back" href="/trends">NASA trends</a></nav>', 1)
        return HTMLResponse(with_brand(html), headers={'Cache-Control': 'no-store'})

    # Preserve the complete Flood Lab service while keeping its port and data
    # separate from every original installation. Only named routes are proxied.
    async def proxy(request, path):
        if not (path in {'/api/runs','/api/experimental-evidence','/api/copilot','/api/event-jobs'} or
                re.fullmatch(r'/api/event-jobs/event-[a-f0-9]{12}', path) or
                re.fullmatch(r'/runs/[A-Za-z0-9_-]{1,100}/[A-Za-z0-9_.-]{1,80}', path)):
            raise HTTPException(404)
        body = await request.body()
        if len(body) > 64*1024:
            raise HTTPException(413, 'Request exceeds the bounded form size')
        if path == '/api/copilot' and body:
            try:
                data = json.loads(body)
            except (ValueError, UnicodeError):
                raise HTTPException(422, 'Provide a valid JSON question') from None
            if not isinstance(data, dict):
                raise HTTPException(422, 'Provide a question object')
            bridge.require(data.get('run_id'))
            if data.get('topic') == 'auto':
                question = str(data.get('question','')).lower()
                topic = 'summary'
                for pattern, candidate in [(r'limitation|safe|forecast|death|accur|damage|evacuat', 'limitations'),(r'road|bridge', 'roads'),(r'building', 'buildings'),(r'access|settlement|cut.off', 'connectivity'),(r'water|flood', 'water')]:
                    if re.search(pattern, question): topic = candidate; break
                data['topic'] = topic
                body = json.dumps(data).encode()
        run_match = re.match(r'/runs/([^/]+)/', path)
        if run_match:
            bridge.require(run_match[1])
        if path.startswith('/api/event-jobs/'):
            bridge.require(path.rsplit('/', 1)[1])
        try:
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=90) as client:
                result = await client.request(request.method, UPSTREAM+path, content=body, headers={'Content-Type': 'application/json'})
        except httpx.HTTPError:
            raise HTTPException(503, 'The LavaLabs flood service is unavailable. Start both services with start.py.') from None
        if result.status_code == 202 and path == '/api/event-jobs':
            job = result.json().get('job_id', '')
            if re.fullmatch(r'event-[a-f0-9]{12}', job):
                bridge.allowed.add(job)
        if result.status_code == 200 and path in {'/api/runs', '/api/experimental-evidence'}:
            data = result.json()
            if isinstance(data, list):
                data = [row for row in data if bridge.permits(row.get('run_id'))]
            elif isinstance(data, dict) and isinstance(data.get('runs'), list):
                data['runs'] = [row for row in data['runs'] if bridge.permits(row.get('run_id'))]
            return JSONResponse(data)
        headers = {key:value for key,value in result.headers.items() if key.lower() in {'content-type','content-disposition','x-artifact-sha256'}}
        return Response(result.content, status_code=result.status_code, headers=headers)

    @app.api_route('/api/runs', methods=['GET'])
    @app.api_route('/api/experimental-evidence', methods=['GET'])
    @app.api_route('/api/copilot', methods=['POST'])
    @app.api_route('/api/event-jobs', methods=['POST'])
    @app.api_route('/api/event-jobs/{job}', methods=['GET'])
    @app.api_route('/runs/{run_id}/{name}', methods=['GET'])
    async def flood_compatibility(request: Request):
        return await proxy(request, request.url.path)

    app.mount('/ui', StaticFiles(directory=UI), name='lava-ui')
    app.mount('/assets', StaticFiles(directory=UI/'satquery'), name='scientific-noir-assets')
    app.mount('/art', StaticFiles(directory=UI/'art'), name='scientific-noir-art')
    app.mount('/processor-assets', StaticFiles(directory=FLOOD/'web'), name='processor-assets')
    app.mount('/processor-art', StaticFiles(directory=FLOOD/'web/art'), name='processor-art')
    app.mount('/trends-data', StaticFiles(directory=ROOT/'trend_lab/web'), name='trends-data')
    return app
