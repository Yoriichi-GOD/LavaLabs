from pathlib import Path
import json,hashlib
here=Path(__file__).resolve().parent
sources={n:(here/n).read_text(encoding='utf-8') for n in ['spectral_lab/refit.py','test_refit.py']}
hashes={n:hashlib.sha256(c.encode()).hexdigest() for n,c in sources.items()}
parent=hashlib.sha256((here/'SOURCE_FREEZE.json').read_bytes()).hexdigest()
(here/'REFIT_SOURCE_FREEZE.json').write_text(json.dumps({'files':hashes,'development_freeze_sha256':parent},indent=2)+'\n')
code='''# Accepted full refit; model/feature comparison source remains unchanged.
import json,hashlib,subprocess,sys
sources=json.loads(SOURCES_LITERAL)
expected=json.loads(HASHES_LITERAL)
for name,code in sources.items():
    if hashlib.sha256(code.encode()).hexdigest()!=expected[name]:raise ValueError('Refit source identity mismatch')
    path=workspace/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(code)
(output/'refit_source_freeze.json').write_text(json.dumps(expected,sort_keys=True))
check=subprocess.run([sys.executable,'-m','pytest',str(workspace),'-q'],capture_output=True,text=True)
print(check.stdout[-2000:]);print(check.stderr[-1000:])
if check.returncode:raise RuntimeError('Accepted-refit regression check failed')
from spectral_lab.refit import run as accepted_refit
refit_receipt=accepted_refit(root,output)
'''.replace('SOURCES_LITERAL',repr(json.dumps(sources))).replace('HASHES_LITERAL',repr(json.dumps(hashes)))
(here/'run_refit_bootstrap.py').write_text(code,encoding='utf-8')
print('Packaged two refit additions; development source freeze preserved.')
