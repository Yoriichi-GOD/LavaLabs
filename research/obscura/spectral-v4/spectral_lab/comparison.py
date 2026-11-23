"""Frozen grouped evaluation. Only FIRMS may change; no outer-label selection."""
from pathlib import Path
import hashlib,json,time,platform,importlib.metadata
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupShuffleSplit
from .core import TARGETS,load_tables,metric,site_folds,write_json
from .baseline import fit_predict
from .selection import choose_mix,mix_predictions
from .independent_audit import independent_score,paired_site_summary
from .extractor import matrices

VARIANTS=('Q','B','A','F','S')
HISTORICAL_CONTROL=.9337828782984863

def branch_mix(b,e,f,m,a,w,v):
    return m+a*((1-v)*((1-w)*(b-m)+w*(e-m))+v*(f-m))

def choose_branch(y,b,e,f,m):
    arrays=[np.asarray(x,dtype=float) for x in [y,b,e,f,m]]
    y,b,e,f,m=arrays;keep=np.isfinite(y)
    if keep.sum()<2 or any(x.shape!=y.shape for x in arrays) or np.isinf(y).any() or not all(np.isfinite(x).all() for x in arrays[1:]):
        raise ValueError('Invalid branch selection inputs')
    best=None
    for v in [0.,.5,1.]:
        for w in [0.,.5,1.]:
            for a in [0.,.25,.5,.75,1.]:
                p=branch_mix(b,e,f,m,a,w,v)
                error=float(np.sqrt(np.mean((y[keep]-p[keep])**2)))
                key=(error,v,w,a)
                if best is None or error<best[0][0]-1e-12 or (abs(error-best[0][0])<=1e-12 and key[1:]<best[0][1:]):
                    best=(key,dict(amplitude=a,image_weight=w,branch_weight=v,inner_rmse=error))
    return best[1]

def branch_predict(choice,b,e,f,m):
    return branch_mix(b,e,f,m,choice['amplitude'],choice['image_weight'],choice['branch_weight'])

def safe_fit(x,y,z):
    # Fit-only all-missing columns cannot convey information and can trigger a
    # sklearn histogram bug. Never inspect validation rows to decide columns.
    measured=np.isfinite(y);columns=np.isfinite(x[measured]).any(axis=0)
    if not columns.any():raise ValueError('No observed fitting features')
    return fit_predict(x[:,columns],y,z[:,columns])[1]

def outer(features,y,groups,fit,check,fit_fn=safe_fit):
    groups=np.asarray(groups);y=np.asarray(y,dtype=float)
    if set(groups[fit])&set(groups[check]) or np.intersect1d(fit,check).size:raise ValueError('Outer site overlap')
    inner={k:np.full((len(fit),5),np.nan) for k in ['table','official','mean']}
    extra={k:np.full(len(fit),np.nan) for k in VARIANTS}
    for a,b in site_folds(groups[fit],3):
        a_global,b_global=fit[a],fit[b]
        for j in range(5):
            if len(set(groups[a_global][np.isfinite(y[a_global,j])]))<2:raise ValueError('Too few observed fitting sites')
            for name in ['table','official']:
                inner[name][b,j]=fit_fn(features[name][a_global],y[a_global,j],features[name][b_global])
        inner['mean'][b]=np.nanmean(y[a_global],axis=0)
        for name in VARIANTS:extra[name][b]=fit_fn(features[name][a_global],y[a_global,4],features[name][b_global])
    if not all(np.isfinite(a).all() for a in [*inner.values(),*extra.values()]):raise ValueError('Missing inner predictions')
    control_choices=[choose_mix(y[fit,j],inner['table'][:,j],inner['official'][:,j],inner['mean'][:,j]) for j in range(5)]
    choices={name:choose_branch(y[fit,4],inner['table'][:,4],inner['official'][:,4],extra[name],inner['mean'][:,4]) for name in VARIANTS}
    raw={k:np.column_stack([fit_fn(features[k][fit],y[fit,j],features[k][check]) for j in range(5)]) for k in ['table','official']}
    raw.update({name:fit_fn(features[name][fit],y[fit,4],features[name][check]) for name in VARIANTS})
    mu=np.nanmean(y[fit],axis=0)
    control=np.column_stack([mix_predictions(raw['table'][:,j],raw['official'][:,j],mu[j],c['amplitude'],c['image_weight']) for j,c in enumerate(control_choices)])
    prediction={'C':control}
    for name in VARIANTS:
        prediction[name]=control.copy()
        prediction[name][:,4]=branch_predict(choices[name],raw['table'][:,4],raw['official'][:,4],raw[name],mu[4])
        if not np.array_equal(prediction[name][:,:4],control[:,:4]):raise AssertionError('Protected targets changed')
    return prediction,{'C':control_choices,**choices},raw

def evaluate(features,y,groups,folds,label,started,fit_fn=safe_fit):
    oof={name:np.full(y.shape,np.nan) for name in ['C',*VARIANTS]};reports=[];seen=np.zeros(len(y),int)
    for number,(fit,check) in enumerate(folds,1):
        if time.monotonic()-started>7200:raise RuntimeError('Comparison exceeded fixed two-hour cap')
        tick=time.monotonic();prediction,choices,raw=outer(features,y,groups,fit,check,fit_fn)
        seen[check]+=1
        for name,p in prediction.items():oof[name][check]=p
        scores={name:metric(y[check],p) for name,p in prediction.items()}
        report=dict(fold=number,fit_sites=len(set(groups[fit])),check_sites=len(set(groups[check])),scores=scores,choices=choices,
                    raw_firms_rmse={name:float(np.sqrt(np.nanmean((y[check,4]-p)**2))) for name,p in raw.items() if name in VARIANTS},seconds=time.monotonic()-tick)
        reports.append(report)
        print('SPECTRAL_FOLD',label,number,json.dumps(report,allow_nan=False),flush=True)
    if not np.all(seen==1):raise ValueError('OOF coverage must be exactly once')
    scores={name:metric(y,p) for name,p in oof.items()}
    for name,p in oof.items():
        audited=independent_score(y,p)
        if abs(audited['mcrmse']-scores[name]['mcrmse'])>1e-12 or audited['observed']!=scores[name]['observed']:raise AssertionError('Independent metric mismatch')
    return dict(scores=scores,folds=reports,independently_recomputed=True),oof

def environment_folds(table,groups):
    columns=['temperature','humidity','wind_speed','precipitation','solar_rad','elevation','slope']
    if not set(columns)<=set(table.columns):raise ValueError('Environmental feature contract changed')
    data=table[columns].copy();data['group']=groups
    med=data.groupby('group',sort=True)[columns].median()
    a=med.to_numpy(dtype=float);fill=np.nanmedian(a,axis=0)
    if not np.isfinite(fill).all():raise ValueError('Unavailable environmental partition feature')
    a=np.where(np.isfinite(a),a,fill);scale=a.std(axis=0);scale[scale==0]=1
    clusters=KMeans(n_clusters=2,random_state=2026,n_init=10).fit_predict((a-a.mean(axis=0))/scale)
    if min(np.bincount(clusters))<5:raise ValueError('Environmental stress cluster too small')
    mapping=dict(zip(med.index,clusters));row_cluster=np.array([mapping[g] for g in groups])
    folds=[(np.flatnonzero(row_cluster!=i),np.flatnonzero(row_cluster==i)) for i in range(2)]
    return folds,dict(features=columns,site_counts=np.bincount(clusters).tolist(),row_counts=np.bincount(row_cluster).tolist(),uses_targets=False)

def make_features(x,values):
    official=np.column_stack([x,values['official']]);q=np.column_stack([official,values['quality']])
    return {'table':x,'official':official,'Q':q,'B':np.column_stack([q,values['brightness']]),
            'A':np.column_stack([q,values['thermal'][:,:6]]),'F':np.column_stack([q,values['thermal']]),
            'S':np.column_stack([q,values['scrambled']])}

def run(root,output):
    started=time.monotonic();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if not (output/'profile_receipt.json').exists() or not json.loads((output/'profile_receipt.json').read_text())['passed']:
        raise ValueError('Passed label-blind profile required')
    train,test,sample,names=load_tables(root);x=train[names].to_numpy(dtype=float);y=train[TARGETS].to_numpy(dtype=float);groups=train.site_key.to_numpy()
    values,extraction=matrices(root,[*train.sample_id,*test.sample_id],output/'private_features.npz')
    dev,_=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(x,groups=groups))
    dev_values={k:v[:len(x)][dev] for k,v in values.items()}
    f=make_features(x[dev],dev_values);dy=y[dev];dg=groups[dev]
    stress_splits,stress_partition=environment_folds(train.iloc[dev],dg)
    comparison_tick=time.monotonic()
    development,oof=evaluate(f,dy,dg,site_folds(dg,3,seed=2026),'development',comparison_tick)
    np.savez_compressed(output/'private_development_predictions.npz',truth=dy,groups=dg.astype(str),**oof)
    write_json(output/'development_receipt.json',development)
    stress,stress_oof=evaluate(f,dy,dg,stress_splits,'environment',comparison_tick)
    np.savez_compressed(output/'private_environment_predictions.npz',truth=dy,groups=dg.astype(str),**stress_oof)
    paired=paired_site_summary(dy,oof['C'],oof['F'],dg)
    scores=development['scores'];gain=scores['C']['mcrmse']-scores['F']['mcrmse']
    wins=sum(r['scores']['F']['mcrmse']<r['scores']['C']['mcrmse']-1e-10 for r in development['folds'])
    target_gain={t:scores['C']['rmse'][t]-scores['F']['rmse'][t] for t in TARGETS}
    checks={'pooled_gain_at_least_005':gain>=.005,'at_least_two_fold_wins':wins>=2,'no_target_regression_over_02':min(target_gain.values())>=-.02,
            'beats_quality_control':scores['F']['mcrmse']<scores['Q']['mcrmse']-1e-10,'beats_brightness_control':scores['F']['mcrmse']<scores['B']['mcrmse']-1e-10,
            'no_environment_stress_regression':stress['scores']['F']['mcrmse']<=stress['scores']['C']['mcrmse']+1e-10,
            'positive_conditional_bootstrap_lower_bound':paired['conditional_site_bootstrap_95_percentile'][0]>0,
            'historical_control_reconciled':abs(scores['C']['mcrmse']-HISTORICAL_CONTROL)<=1e-9,
            'protected_targets_byte_equal':all(np.array_equal(oof[n][:,:4],oof['C'][:,:4]) for n in VARIANTS)}
    receipt={'schema':1,'experiment':'sparse_local_spectral_firms_v4','development':development,'environment_stress':stress,
             'stress_partition':stress_partition,'paired_sites':paired,'extraction':extraction,
             'gate':dict(passed=all(checks.values()),checks=checks,pooled_gain=gain,fold_wins=wins,per_target_gain=target_gain),
             'counts':dict(development_rows=len(dev),development_sites=len(set(dg)),train_rows=len(x),test_rows=len(test)),
             'environment':dict(python=platform.python_version(),**{p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-learn','rasterio']}),
             'seconds':time.monotonic()-started,'submission_exported':False,
             'limits':['Reused development sites; no independent confirmation or time-forward guarantee.',
                       'Descriptors are L2A spectral shape, not calibrated fire, FRP, temperature or emissions.',
                       'Only FIRMS changes; first four targets exactly match control.','No scored export before separate fresh-session replay and audit.'],
             'si_disclosure':'OpenAI Codex assisted source and tests; source observations unchanged.'}
    write_json(output/'spectral_receipt.json',receipt)
    print('SPECTRAL_RECEIPT_BEGIN');print(json.dumps(receipt,sort_keys=True,allow_nan=False));print('SPECTRAL_RECEIPT_END',flush=True)
    return receipt
