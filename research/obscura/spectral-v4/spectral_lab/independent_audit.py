"""Recompute private OOF evidence; output aggregates only, never rows or site keys."""
from pathlib import Path
import hashlib
import json
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from .core import TARGETS,load_tables,site_folds

def independent_score(y,p,weights=None):
    y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float)
    if y.shape!=p.shape or y.ndim!=2 or y.shape[1]!=5 or not np.isfinite(p).all() or np.isinf(y).any():
        raise ValueError('Invalid audit prediction/label contract')
    weights=np.ones(len(y)) if weights is None else np.asarray(weights,dtype=float)
    if weights.shape!=(len(y),) or not np.isfinite(weights).all() or (weights<0).any():raise ValueError('Invalid audit weights')
    errors={};counts={}
    for j,name in enumerate(TARGETS):
        keep=np.isfinite(y[:,j]);den=float(weights[keep].sum())
        if den<=0:raise ValueError('Missing observed labels in audit target')
        errors[name]=float(np.sqrt(np.sum(weights[keep]*(y[keep,j]-p[keep,j])**2)/den));counts[name]=den
    return {'mcrmse':float(np.mean(list(errors.values()))),'rmse':errors,'observed':counts}

def paired_site_summary(y,control,candidate,groups,draws=1000):
    groups=np.asarray(groups);sites,inverse=np.unique(groups,return_inverse=True)
    if len(groups)!=len(y):raise ValueError('Mismatched audit groups')
    point=independent_score(y,control)['mcrmse']-independent_score(y,candidate)['mcrmse']
    rng=np.random.default_rng(2026);deltas=[]
    for _ in range(draws):
        weights=np.bincount(rng.integers(0,len(sites),len(sites)),minlength=len(sites))[inverse]
        try:deltas.append(independent_score(y,control,weights)['mcrmse']-independent_score(y,candidate,weights)['mcrmse'])
        except ValueError:continue
    if len(deltas)<.99*draws:raise ValueError('Insufficient valid site bootstrap draws')
    macro={};support={}
    for j,t in enumerate(TARGETS):
        scores={name:[] for name in ['control','candidate']}
        for site in sites:
            keep=(groups==site)&np.isfinite(y[:,j])
            if keep.any():
                for name,p in [('control',control),('candidate',candidate)]:scores[name].append(float(np.sqrt(np.mean((y[keep,j]-p[keep,j])**2))))
        macro[t]={name:float(np.mean(v)) for name,v in scores.items()};support[t]=len(scores['control'])
    return {'sites':len(sites),'point_gain':point,'conditional_site_bootstrap_95_percentile':np.quantile(deltas,[.025,.975]).tolist(),
        'valid_draws':len(deltas),'site_macro_rmse':macro,'label_bearing_sites':support,
        'limitation':'Fixed OOF predictions only; no retraining/selection uncertainty, independent confirmation or temporal claim.'}

def audit(root,output):
    output=Path(output);receipt=json.loads((output/'foundation_receipt.json').read_text())
    train,test,sample,names=load_tables(root);groups=train.site_key.to_numpy();y=train[TARGETS].to_numpy(dtype=float)
    dev,_=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(train[names],groups=groups))
    saved=np.load(output/'private_development_predictions.npz',allow_pickle=False)
    if not np.array_equal(saved['truth'],y[dev],equal_nan=True):raise ValueError('Saved OOF truth does not match exact development rows')
    scores={name:independent_score(y[dev],saved[name]) for name in ['control','candidate','raw_foundation']}
    for name,value in scores.items():
        stated=receipt['comparison']['scores'][name]
        if not np.isclose(value['mcrmse'],stated['mcrmse'],atol=1e-12,rtol=0):raise ValueError('Receipt MCRMSE disagrees with independent calculation')
        for t in TARGETS:
            if not np.isclose(value['rmse'][t],stated['rmse'][t],atol=1e-12,rtol=0) or value['observed'][t]!=stated['observed'][t]:
                raise ValueError('Receipt target score/denominator disagrees with independent calculation')
    mean=np.zeros_like(y[dev])
    for a,b in site_folds(groups[dev],3,seed=2026):mean[b]=np.nanmean(y[dev][a],axis=0)
    result={'schema':1,'experiment':receipt['experiment'],'independent_scores':scores,
        'zero':independent_score(y[dev],np.zeros_like(mean)),'outer_fold_mean':independent_score(y[dev],mean),
        'paired_sites':paired_site_summary(y[dev],saved['control'],saved['candidate'],groups[dev]),
        'exact_development_truth_match':True,'no_test_label_access':True,'rows_exported_in_audit':False}
    submission=receipt.get('submission')
    if submission:
        import pandas as pd
        path=output/submission['file'];table=pd.read_csv(path,dtype={'sample_id':str})
        if list(table.columns)!=['sample_id',*TARGETS] or not table.sample_id.equals(sample.sample_id):raise ValueError('CSV schema/order mismatch')
        if len(table)!=len(test) or table.sample_id.duplicated().any() or not np.isfinite(table[TARGETS].to_numpy()).all():raise ValueError('CSV coverage/finiteness mismatch')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=submission['sha256']:raise ValueError('CSV hash mismatch')
        result['verified_submission']={'sha256':digest,'rows':len(table),'columns':list(table.columns)}
    (output/'independent_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print('INDEPENDENT_AUDIT_BEGIN');print(json.dumps(result,sort_keys=True));print('INDEPENDENT_AUDIT_END')
    return result

