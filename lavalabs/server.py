"""LavaLabs application: one local workspace with fixed evidence stores.

SI-assisted implementation, OpenAI Codex. Original scientific outputs retain
their own provenance, dates, hashes and interpretation limits.
"""
from pathlib import Path
import hashlib
import json
import os
import re
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from jai_extension.server import attach
from jai_extension.terrain import TerrainStore
from jai_extension.terrain_exposure import TerrainExposureStore
from jai_extension.research_cases import CaseResearchStore, router as case_router, CASES
from components.floodlab.floodlab import server as flood
from components.floodlab.floodlab import jobs as event_jobs
from .public_runs import DemoBridge
from .trend_exports import router as export_router
from .nepal_exports import router as nepal_export_router
from .response import build as build_response

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'UI'
FLOOD = ROOT / 'components/floodlab'

WORKSPACES = (
    ('/#terrain', 'Terrain &amp; flood'), ('/#cases', 'Case studies'), ('/#evidence', 'Research evidence'),
    ('/nepal', 'Nepal investigation'), ('/trends', 'NASA trends'),
)


def workspace_nav(active):
    links = []
    for path, label in WORKSPACES:
        current = ' class="active" aria-current="page"' if path == active else ''
        links.append(f'<a{current} href="{path}">{label}</a>')
    return '<nav aria-label="Workspace">' + ''.join(links) + '</nav>'


def update_workspace_nav(html, active):
    return re.sub(r'<nav aria-label="Workspace">.*?</nav>', lambda match: workspace_nav(active), html, count=1, flags=re.S)


def match_copilot_topic(question):
    for pattern, topic in (
        (r'limitation|safe|forecast|death|casualt|confiden|accur|certain|validat|invent|ignore|damage|evacuat|मृत्यु|निश्चित|शुद्धता', 'limitations'),
        (r'road|bridge', 'roads'), (r'building', 'buildings'),
        (r'access|settlement|cut.off', 'connectivity'), (r'water|flood', 'water'),
    ):
        if re.search(pattern, question, re.I):
            return topic
    return 'summary'


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


def flood_views():
    source = (FLOOD/'web/index.html').read_text(encoding='utf-8')
    processor = '<section id="lab">' + source.split('<section id="lab">', 1)[1].split('</main>', 1)[0]
    dialog = '<dialog id="image-viewer"' + source.split('<dialog id="image-viewer"', 1)[1].split('</body>', 1)[0]
    processor = processor.replace('/assets/', '/processor-assets/').replace('/art/', '/processor-art/')
    processor = processor.replace('AI selects topic', 'Match a supported topic')
    settings = re.search(r'<section class="analysis-settings">.*?</section></section>', processor, re.S)[0]
    processor = processor.replace(settings, '', 1).replace('<section class="question-panel">',
        '<section class="processor-response" id="processor-response" hidden>'
        '<h2>Response for this observation</h2><p id="processor-response-status" role="status"></p>'
        '<a id="processor-response-link" hidden>Analyze saved observation →</a></section>' +
        settings + '<section class="question-panel">', 1)
    processor = re.sub(r'(id="event-(?:bbox|date)"[^>]*?) value="[^"]*"', r'\1', processor)
    processor = processor.replace('<button type="submit">Run analysis</button>',
        '<div class="area-actions"><button id="event-pick" type="button">Pick area on map</button>'
        '<button type="submit">Run analysis</button></div><p id="event-pick-status" role="status"></p>')
    response = (UI/'response/index.html').read_text(encoding='utf-8').split('<main ', 1)[1].split('</main>', 1)[0]
    return ('<section id="flood-processor" data-lavalabs-processor hidden><template shadowrootmode="open">'
            '<link rel="stylesheet" href="/processor-assets/style.css">'
            '<link rel="stylesheet" href="/processor-assets/flood-workspace.css">'
            '<link rel="stylesheet" href="/ui/processor.css">'
            f'{processor}{dialog}</template></section>'
            '<section id="flood-response" hidden><template shadowrootmode="open">'
            '<link rel="stylesheet" href="/ui/response/style.css">'
            f'<div {response}</div></template></section>')


REPORTS = {
    'spectral': ROOT/'research/results/exposure-verification-20261112/REPORT.md',
    'drainage': ROOT/'research/results/drainage-consistency-20261112/REPORT.md',
    'flow': ROOT/'research/results/drainage-validation-20261112/REPORT.md',
    'cases': ROOT/'research/results/case-campaign-20261107/REPORT.md',
    'validation': ROOT/'research/results/validation-closure-20261107/REPORT.md',
    'r3': ROOT/'research/researcher-3-final/integration/RESEARCHER_3_FINAL_FINDINGS.md',
}


def create_app():
    bridge = DemoBridge(include_archive=os.environ.get('LAVALABS_LOCAL_ARCHIVE') == '1')
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

    attach(app, bridge, terrain, FLOOD, exposure, authorize_run=bridge.require, job_bridge=bridge.for_job)
    app.include_router(export_router)
    app.include_router(nepal_export_router)
    app.include_router(case_router(CaseResearchStore(ROOT/'research/results/case-campaign-20261107')))

    @app.get('/', response_class=HTMLResponse)
    def home():
        html = (UI/'index.html').read_text(encoding='utf-8').replace('<!-- flood views -->', flood_views(), 1)
        return HTMLResponse(with_brand(html), headers={'Cache-Control': 'no-store'})

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
        return {'state': 'saved evidence and local processing', 'lab_port': int(os.environ.get('LAVALABS_PORT', '8780'))}

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
        return HTMLResponse(with_brand(update_workspace_nav(html, '/trends')), headers={'Cache-Control': 'no-store'})

    @app.get('/nepal', response_class=HTMLResponse)
    def nepal():
        html = (UI/'nepal/index.html').read_text(encoding='utf-8')
        return HTMLResponse(with_brand(update_workspace_nav(html, '/nepal')), headers={'Cache-Control': 'no-store'})

    @app.get('/processor')
    @app.get('/processor/response')
    def processor_alias(request: Request, run: str | None = None):
        view = 'response' if request.url.path.endswith('/response') else 'analysis'
        query = {'view': view}
        if run:
            query['run'] = run
        return RedirectResponse('/?' + urlencode(query) + '#terrain')

    @app.get('/api/flood/runs/{run_id}/response')
    def response_evidence(run_id: str, brief: bool = False):
        packet = build_response(bridge, run_id, include_map=not brief)
        headers = {'Cache-Control': 'no-store'}
        if brief:
            headers['Content-Disposition'] = f'attachment; filename="lavalabs-response-{run_id}.json"'
        return JSONResponse(packet, headers=headers)

    @app.get('/flood', include_in_schema=False)
    def flood_alias():
        return RedirectResponse('/?view=analysis#terrain')

    @app.get('/api/runs')
    def flood_runs():
        return bridge.listing()

    @app.get('/api/experimental-evidence')
    def flood_evidence():
        return flood.evidence_for(bridge.listing())

    @app.post('/api/copilot')
    def flood_copilot(question: flood.CopilotQuery):
        bridge.require(question.run_id)
        if question.topic == 'auto':
            question = question.model_copy(update={'topic': match_copilot_topic(question.question)})
        return flood.copilot(question)

    @app.post('/api/event-jobs', status_code=202)
    def flood_submit(job: event_jobs.EventRequest):
        return event_jobs.submit(job)

    @app.get('/api/event-jobs/{job}')
    def flood_job(job: str):
        bridge.require(job)
        return event_jobs.status(job)

    @app.get('/runs/{run_id}/{name}')
    def flood_artifact(run_id: str, name: str):
        path = bridge.artifact_path(run_id, name)
        return FileResponse(path, filename=name if name.endswith(('.tif', '.csv', '.geojson')) else None)

    app.mount('/ui', StaticFiles(directory=UI), name='lava-ui')
    app.mount('/assets', StaticFiles(directory=UI/'satquery'), name='scientific-noir-assets')
    app.mount('/art', StaticFiles(directory=UI/'art'), name='scientific-noir-art')
    app.mount('/processor-assets', StaticFiles(directory=FLOOD/'web'), name='processor-assets')
    app.mount('/processor-art', StaticFiles(directory=FLOOD/'web/art'), name='processor-art')
    app.mount('/trends-data', StaticFiles(directory=ROOT/'trend_lab/web'), name='trends-data')
    return app
