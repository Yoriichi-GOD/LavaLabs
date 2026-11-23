"""Package only own source; all competition data and outputs stay private."""
from pathlib import Path
import json,hashlib

HERE=Path(__file__).resolve().parent
sources={str(p.relative_to(HERE)).replace('\\','/'):p.read_text(encoding='utf-8') for p in [*sorted((HERE/'spectral_lab').glob('*.py')),*sorted(HERE.glob('test_*.py'))] if p.name not in {'refit.py','test_refit.py'}}
hashes={name:hashlib.sha256(code.encode()).hexdigest() for name,code in sources.items()}
freeze=HERE/'SOURCE_FREEZE.json'
if freeze.exists():
    if json.loads(freeze.read_text())['files']!=hashes:raise RuntimeError('Frozen development source changed; use a new experiment directory.')
else:freeze.write_text(json.dumps({'files':hashes,'intent':'Frozen before new real-data accuracy; source only.'},indent=2)+'\n')
bootstrap='''# Private scientific experiment. No downloads or external observations.
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='2'
from pathlib import Path
import json,hashlib,sys,subprocess
import pandas as pd
sources=json.loads(SOURCES_LITERAL)
hashes=json.loads(HASHES_LITERAL)
workspace=Path('/kaggle/working/lavalabs_spectral_source');workspace.mkdir(exist_ok=True)
for name,code in sources.items():
    if hashlib.sha256(code.encode()).hexdigest()!=hashes[name]:raise ValueError('Source freeze mismatch')
    path=workspace/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(code)
sys.path.insert(0,str(workspace))
check=subprocess.run([sys.executable,'-m','pytest',str(workspace),'-q'],capture_output=True,text=True)
print(check.stdout[-5000:]);print(check.stderr[-1000:])
if check.returncode:raise RuntimeError('Spectral regression checks failed')
paths=[p.parent for p in Path('/kaggle/input').rglob('train.csv') if (p.parent/'images').is_dir() and (p.parent/'test.csv').exists()]
if len(paths)!=1:raise RuntimeError('Expected exactly one official dataset directory')
root=paths[0]
output=Path('/kaggle/working/lavalabs_private_spectral');output.mkdir(exist_ok=True)
(output/'source_freeze.json').write_text(json.dumps(hashes,sort_keys=True,indent=2))
from spectral_lab.extractor import profile
# Only identifiers are read for the label-blind feasibility pass. No labels.
ids=pd.read_csv(root/'train.csv',usecols=['sample_id'],dtype={'sample_id':str}).sample_id.tolist()
profile_receipt=profile(root,ids,output)
print('PROFILE_READY_FOR_PRIVATE_LABEL_BLIND_INSPECTION',flush=True)
'''.replace('SOURCES_LITERAL',repr(json.dumps(sources))).replace('HASHES_LITERAL',repr(json.dumps(hashes)))
compare="""# Execute after the fixed label-blind profile and overlays are reviewed.
from spectral_lab.comparison import run
spectral_receipt=run(root,output)
from spectral_lab.audit_saved import audit
spectral_audit=audit(root,output)
"""
(HERE/'bootstrap_profile.py').write_text(bootstrap,encoding='utf-8')
(HERE/'run_comparison.py').write_text(compare,encoding='utf-8')
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'cells':[
 {'cell_type':'markdown','metadata':{},'source':['# LavaLabs: private sparse spectral experiment\n','Source-only bootstrap. All observations, chips and predictions stay private. SI-assisted source. Fixed protocol and historical model are protected. CPU two threads, no internet or pretrained models.\n','First run: software checks and label-blind 32-chip feasibility profile only. Spectral candidates are not validated fire detections.']},
 {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':bootstrap.splitlines(True)}]}
(HERE/'LavaLabs-Spectral-Private.ipynb').write_text(json.dumps(nb,indent=1),encoding='utf-8')
print('Packaged',len(sources),'source/test files; no observations included.')
