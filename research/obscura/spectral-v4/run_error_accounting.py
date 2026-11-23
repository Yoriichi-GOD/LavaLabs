"""Post-evaluation aggregate diagnostics only; never changes fitting/selection."""
from pathlib import Path
import json,hashlib
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from spectral_lab.core import TARGETS,load_tables,write_json

output=Path('/kaggle/working/lavalabs_private_spectral')
train,_,_,names=load_tables(root);groups=train.site_key.to_numpy()
dev,_=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(train[names],groups=groups))
with np.load(output/'private_development_predictions.npz',allow_pickle=False) as saved:
    y=saved['truth'].copy();control=saved['C'].copy();candidate=saved['F'].copy();site=saved['groups'].copy()
with np.load(output/'private_features.npz',allow_pickle=False) as saved:
    quality=saved['quality'][:len(train)][dev].copy()
if not np.array_equal(y,train[TARGETS].to_numpy(dtype=float)[dev],equal_nan=True):raise ValueError('Diagnostic row identity mismatch')

def segment(mask):
    answer={'rows':int(mask.sum()),'targets':{}}
    for j,t in enumerate(TARGETS):
        keep=mask&np.isfinite(y[:,j]);n=int(keep.sum())
        answer['targets'][t]={'observed':n}
        if n:
            answer['targets'][t].update({name:float(np.sqrt(np.mean((p[keep,j]-y[keep,j])**2))) for name,p in [('C',control),('F',candidate)]})
    return answer

firm=y[:,4];threshold=float(np.nanquantile(firm,.9));valid=np.isfinite(firm)
floor=float(np.nanmin(firm));site_errors=[]
for s in np.unique(site):
    keep=(site==s)&valid;site_errors.append(float(np.sum((firm[keep]-control[keep,4])**2)))
total=sum(site_errors)
report={'schema':1,'purpose':'Error accounting only; no model or threshold selection.',
        'fixed_clear_fraction_strata':{'below_10_percent':segment(quality[:,1]<.1),
             '10_to_50_percent':segment((quality[:,1]>=.1)&(quality[:,1]<.5)),'at_least_50_percent':segment(quality[:,1]>=.5)},
        'firms_label_diagnostics':{'development_floor':floor,'floor_rows':int(np.sum(valid&np.isclose(firm,floor,rtol=0,atol=1e-10))),
             'development_90_percentile':threshold,'strictly_above_90_percentile':segment(valid&(firm>threshold)),
             'at_or_below_90_percentile':segment(valid&(firm<=threshold)),
             'top_five_sites_share_of_control_firms_squared_error':sum(sorted(site_errors,reverse=True)[:5])/total if total else 0},
        'no_site_identifiers_or_rows_exported':True,
        'limits':['Strata have different denominators and cannot be ranked as comparable global scores.',
                  'Tail boundary uses development labels for descriptive accounting only.',
                  'Error concentration cannot establish the leader method or future-time accuracy.']}
write_json(output/'error_accounting.json',report)
print('SPECTRAL_ERROR_ACCOUNTING_BEGIN');print(json.dumps(report,sort_keys=True,allow_nan=False));print('SPECTRAL_ERROR_ACCOUNTING_END',flush=True)
