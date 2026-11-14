"""Prepare LavaLabs' attributed case/research UI and rebrand the verified NASA module."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'UI'
TREND=ROOT/'trend_lab/web'

def prepare():
 studies=[
  {'title':'NDVI-assisted water review','scope':'External water-map disagreement experiments · frozen November 12 results','finding':'NDVI-assisted review improved yield in prespecified secondary tests. The combined primary rule reduced yield; it is not presented as a general improvement.','limit':'Review yield on existing map disagreements is different from flood-mapping accuracy. Model errors, development exposure and source-specific support remain part of the result.','report':'/api/lava/reports/spectral'},
  {'title':'Terrain and drainage consistency','scope':'Nepal, Varanasi and Sangam Vihar · topographic diagnostics','finding':'The retained workflow connects calibrated optical indices, DSM-derived slope, modeled drainage and available mapped drains. Native source scale, open boundaries and unknown physical connections qualify the result.','limit':'A surface model is not surveyed bare-earth DTM, drain-bed geometry, culvert connectivity or hydraulic capacity. The alternate Delhi inventory is nested sensitivity evidence, not independent corroboration.','report':'/api/lava/reports/drainage'},
  {'title':'Observed-flow and regional controls','scope':'A Canadian ADCP river control and regional direction comparisons','finding':'The observed-flow and regional comparisons are preserved as separate controls with their actual coordinate, heading, registration and reference limitations.','limit':'These controls do not validate physical urban drainage, generalize to independent basins or prove a fusion gain. Missing comparisons remain unavailable.','report':'/api/lava/reports/flow'},
  {'title':'Ahr screening and evidence qualification','scope':'Frozen candidate queue, road-screening controls and R3 final analysis','finding':'The proximity baseline retrieved more explicitly flagged Ahr roads at the fixed screening cutoffs; the smallest matched budget retained equal expected yield under the tie convention. Evidence qualification limits what can be asserted about a retrieved candidate.','limit':'Retrieval, physical exposure accuracy and usefulness of a qualified statement are different outcomes. Analyst decision benefit and independent physical-route accuracy remain unmeasured.','report':'/api/lava/reports/r3'},
  {'title':'Four genuine case windows','scope':'Nepal · Kedarnath · Varanasi · southern Sangam Vihar','finding':'The four-case campaign retains 37 native raster windows, source receipts, measured terrain, observed/context layers and failed quality gates. All four are accessible in the case viewer.','limit':'The locations have different sensors, dates, support and reference semantics. Kedarnath has limited common clear Landsat support; urban inventories do not establish buried drainage connections.','report':'/api/lava/reports/cases'},
  {'title':'A failed slope filter is retained','scope':'Independent component test and finer-terrain coverage gate','finding':'The fixed slope filter reduced total-water IoU from 0.700446 to 0.596378 in the retained external component experiment. The finer 2 m Nepal terrain reached 89.98% quality-supported coverage, below the 95% full-case gate.','limit':'The 2 m surface is post-event and is not a validated DTM upgrade. The interactive Nepal overview uses a separate 90 m historical DSM; the case viewer uses frozen 30 m derivatives.','report':'/api/lava/reports/validation'},
 ]
 output=ROOT/'data/views';output.mkdir(parents=True,exist_ok=True)
 (output/'research.json').write_text(json.dumps({'studies':studies,'prior_work':True,'new_contribution':'independent LavaLabs integration and source-aware interface'},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 html=(TREND/'index.html').read_text(encoding='utf-8')
 html=html.replace('SATQuery','LavaLabs').replace('SatQuery','LavaLabs')
 html=html.replace('href="style.css"','href="/trends-data/style.css"').replace('src="app.js"','src="/ui/trends/app.js"').replace('href="data/','href="/trends-data/data/')
 header='<header><a class="brand" href="/#terrain"><img src="/logo" alt="LavaLabs volcano"><span>Lava<span class="brand-light">Labs</span></span></a><nav aria-label="Workspace"><a href="/#terrain">Terrain & flood</a><a href="/#cases">Case studies</a><a href="/#evidence">Research evidence</a><a class="active" href="/trends">NASA trends</a><a href="/processor">Flood processor</a></nav></header>'
 html=re.sub(r'<header>.*?</header>',header,html,count=1,flags=re.S)
 html=html.replace('<body>','<body class="sq-document-scroll sq-clipped-scroll">').replace('<html lang="en">','<html lang="en" class="sq-clipped-scroll" data-theme="dark">')
 html=html.replace('<footer>','<footer class="lava-footer">')
 html=re.sub(r'<button([^>]*\bid="(?:csv|receipt)"[^>]*)>(.*?)</button>', lambda match: '<a'+re.sub(r'\s+type="button"','',match[1])+' download>'+match[2]+'</a>',html,flags=re.S)
 html=html.replace('</head>','<link rel="icon" href="/logo"><link rel="stylesheet" href="/assets/workspace-shell.css"><link rel="stylesheet" href="/ui/lava.css"><link rel="stylesheet" href="/ui/trends/noir.css"><script defer src="/ui/trends/chrome.js"></script></head>')
 target=UI/'trends';target.mkdir(parents=True,exist_ok=True)
 (target/'index.html').write_text(html,encoding='utf-8')
 script=(TREND/'app.js').read_text(encoding='utf-8').replace('SATQuery','LavaLabs').replace('satquery-','lavalabs-')
 script=script.replace('fetch(path)',"fetch('/trends-data/'+path)")
 script=script.replace('`data/sources/${source.file}`','`/trends-data/data/sources/${source.file}`')
 begin=script.index("    $('csv').onclick")
 end=script.index('    if (originals)',begin)
 script=script[:begin]+script[end:]
 link_line="  $('raw-source').href = `/trends-data/data/sources/${source.file}`;"
 assert link_line in script
 script=script.replace(link_line,link_line+"\n  const exportBase = `/api/lava/trends/${state.region}/${state.variable}/${state.window}`;\n  $('csv').href = `${exportBase}/csv`;\n  $('receipt').href = `${exportBase}/json`;")
 (target/'app.js').write_text(script,encoding='utf-8')
 # Bind only LavaLabs-owned UI changes to the inherited Nepal workspace.
 earth=ROOT/'jai_extension/web/earth.js'
 text=earth.read_text(encoding='utf-8')
 text=text.replace("<span class=\"eyebrow\">CONNECTED EARTH OBSERVATIONS</span>", '')
 text=text.replace("'01 Before'", "'Before'")
 text=text.replace("(id==='eval-tab'?'#evidence':'')", "(id==='eval-tab'?'#evidence':'#cases')")
 text=text.replace("$('main > .intro').hidden=true;", "$('main > .intro').hidden=false;document.getElementById('page-title').textContent='Terrain & flood';document.getElementById('page-description').textContent='The Nepal investigation. Saved observations, historical terrain and source-linked answers.';")
 text=text.replace('font:{color:p.muted,size:10}', 'font:{color:p.muted,size:11}')
 earth.write_text(text,encoding='utf-8')
 static=ROOT/'jai_extension/server.py'
 text=static.read_text(encoding='utf-8')
 if 'authorize_run=None' not in text:
  text=text.replace('visual_root=None, exposure_store=None):','visual_root=None, exposure_store=None, authorize_run=None):')
  text=text.replace('def investigate(payload:InvestigationRequest):return manager.submit(payload.model_dump())',
                    'def investigate(payload:InvestigationRequest):\n            if authorize_run and payload.run_id:\n                authorize_run(payload.run_id)\n            return manager.submit(payload.model_dump())')
  static.write_text(text,encoding='utf-8')
 visual=UI/'satquery/visual-context.js'
 text=visual.read_text(encoding='utf-8')
 if 'LavaLabs initial optical context' not in text:
  text=text.replace('})();',"// LavaLabs initial optical context: also recover a context that loaded before this extension.\n  if(window.SQNoir.last?.[0])update(window.SQNoir.last[0]);\n})();")
  visual.write_text(text,encoding='utf-8')
 reference_test=ROOT/'components/floodlab/tests/test_nepal_registration.py'
 text=reference_test.read_text(encoding='utf-8').replace("r['damage_features_inspected'] is False", "r['damage_features_inspected'] is True  # Consumed development evidence; never relabel as untouched.")
 text=text.replace("not candidate['imagery_downloaded']", "candidate['imagery_downloaded']  # Source acquisition is now recorded as complete.")
 if 'Public checkout intentionally excludes' not in text:
  text=text.replace('import json,hashlib,sqlite3','import json,hashlib,sqlite3\nimport pytest')
  text=text.replace("        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']", "        if not p.is_file():pytest.skip('Public checkout intentionally excludes local EMSR reference acquisitions')\n        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']")
 reference_test.write_text(text,encoding='utf-8')
 print('Prepared six research studies and Scientific Noir NASA trend screen')

if __name__=='__main__':prepare()
