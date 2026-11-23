"""Package reviewed source as a private Kaggle notebook without any source data."""
from pathlib import Path
import json
import hashlib
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--experiment',action='store_true')
args=parser.parse_args()
ROOT = Path(__file__).resolve().parent
files = sorted((ROOT/'atmospheric_lab').glob('*.py'))
sources = {path.name: path.read_text(encoding='utf-8') for path in files}
bootstrap = '''from pathlib import Path
import json, os, sys
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
package = Path('/kaggle/working/atmospheric_lab')
package.mkdir(exist_ok=True)
sources = json.loads(SOURCES_JSON)
for name, text in sources.items():
    (package/name).write_text(text, encoding='utf-8')
for name in list(sys.modules):
    if name == 'atmospheric_lab' or name.startswith('atmospheric_lab.'):
        del sys.modules[name]
print('LavaLabs source ready; aggregate reporting only.')
'''.replace('SOURCES_JSON',repr(json.dumps(sources)))
checks = '''import numpy as np
from atmospheric_lab.core import metric, site_folds
y = np.array([[1,2,3,4,5],[np.nan,4,5,6,7]], dtype=float)
assert abs(metric(y,np.zeros_like(y))['mcrmse'] - np.mean([1,np.sqrt(10),np.sqrt(17),np.sqrt(26),np.sqrt(37)])) < 1e-12
groups = np.repeat(np.arange(6),3)
assert all(set(groups[a]).isdisjoint(groups[b]) for a,b in site_folds(groups,3))
print('Masked metric and whole-site split assertions passed.')
'''
run = '''from pathlib import Path
from atmospheric_lab.baseline import run
roots = [Path('/kaggle/input/competitions/obscura'),Path('/kaggle/input/obscura')]
data = next((p for p in roots if (p/'train.csv').exists()),None)
if data is None:
    raise RuntimeError('Attach the official OBSCURA competition input before running.')
receipt = run(data, '/kaggle/working/lavalabs_private_baseline')
print('Private CSV ready. Do not publish row-level outputs.')
print('AGGREGATE_RECEIPT_BEGIN')
print(json.dumps(receipt, sort_keys=True))
print('AGGREGATE_RECEIPT_END')
'''
if args.experiment:
    run=run.replace('from atmospheric_lab.baseline import run','from atmospheric_lab.experiment import run').replace("'/kaggle/working/lavalabs_private_baseline'","'/kaggle/working/lavalabs_private_experiment'")
cells = [{'cell_type':'markdown','metadata':{},'source':[
    '# LavaLabs Atmospheric Lab — first measured baseline\n',
    'Private experiment using supplied OBSCURA inputs. Whole-site validation; missing-label masking.\n',
    'SI-assisted implementation. Credits: official starter (Apache-2.0), scikit-learn, NumPy, pandas.\n',
    'No external environmental data; no facility/date recovery. Keep prediction CSV private.\n']}]
for source in [bootstrap,checks,run]:
    cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[], 'source':source.splitlines(keepends=True)})
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
if args.experiment:
    cells[0]['source']=['# LavaLabs Atmospheric Lab — cloud and spatial experiments\n',
                        'Private supplied-data experiment. Candidate selection uses inner grouped predictions and separate confirmation sites.\n',
                        'All public-facing outputs are aggregate; prediction CSV and feature caches remain private.\n',
                        'SI-assisted implementation; official starter (Apache-2.0) credited in source. No outside environmental inputs.\n']
destination=ROOT/('LavaLabs_Atmospheric_Experiments.ipynb' if args.experiment else 'LavaLabs_Atmospheric_Baseline.ipynb')
destination.write_text(json.dumps(notebook,indent=1),encoding='utf-8')
print('Notebook written:',destination.name)
print('Source SHA256:',hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest())
