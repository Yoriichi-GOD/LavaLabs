"""Accepted FIRMS-only refit. Export remains private until fresh replay passes."""
from pathlib import Path
import time,json,hashlib
import numpy as np
from .core import TARGETS,load_tables,site_folds,export_submission,write_json
from .selection import choose_mix,mix_predictions
from .comparison import make_features,safe_fit,choose_branch,branch_predict
from .extractor import matrices

EXPECTED_CONTROL='007abb84e2f53b01d7ca71929647d83ea6803e2cb186871fd61f3cda38892c20'

def run(root,output):
    tick=time.monotonic();output=Path(output)
    decision=json.loads((output/'spectral_receipt.json').read_text())
    audit=json.loads((output/'independent_spectral_audit.json').read_text())
    if not decision['gate']['passed'] or not audit['passed']:raise ValueError('Accepted audited comparison required')
    train,test,sample,names=load_tables(root);y=train[TARGETS].to_numpy(dtype=float);groups=train.site_key.to_numpy()
    values,_=matrices(root,[*train.sample_id,*test.sample_id],output/'private_features.npz')
    x=np.vstack([train[names].to_numpy(dtype=float),test[names].to_numpy(dtype=float)])
    all_features=make_features(x,values);n=len(train);oof={k:np.full(y.shape,np.nan) for k in ['table','official','mean']};branch=np.full(n,np.nan)
    for number,(a,b) in enumerate(site_folds(groups,5),1):
        if time.monotonic()-tick>2700:raise RuntimeError('Accepted refit exceeded45minutes')
        for name in ['table','official']:
            for j in range(5):oof[name][b,j]=safe_fit(all_features[name][a],y[a,j],all_features[name][b])
        oof['mean'][b]=np.nanmean(y[a],axis=0)
        branch[b]=safe_fit(all_features['F'][a],y[a,4],all_features['F'][b])
        print('SPECTRAL_REFIT_FOLD',number,round(time.monotonic()-tick,2),flush=True)
    if not all(np.isfinite(a).all() for a in [*oof.values(),branch]):raise ValueError('Incomplete refit OOF')
    choices=[choose_mix(y[:,j],oof['table'][:,j],oof['official'][:,j],oof['mean'][:,j]) for j in range(5)]
    new_choice=choose_branch(y[:,4],oof['table'][:,4],oof['official'][:,4],branch,oof['mean'][:,4])
    raw={name:np.column_stack([safe_fit(all_features[name][:n],y[:,j],all_features[name][n:]) for j in range(5)]) for name in ['table','official']}
    new=safe_fit(all_features['F'][:n],y[:,4],all_features['F'][n:]);mu=np.nanmean(y,axis=0)
    control=np.column_stack([mix_predictions(raw['table'][:,j],raw['official'][:,j],mu[j],c['amplitude'],c['image_weight']) for j,c in enumerate(choices)])
    control_hash=export_submission(sample,control,output/'private_control_replay.csv')
    # The previous CSV is compared as a complete independent frozen identity.
    if control_hash!=EXPECTED_CONTROL:raise ValueError('Frozen final control CSV identity mismatch; do not submit')
    candidate=control.copy();candidate[:,4]=branch_predict(new_choice,raw['table'][:,4],raw['official'][:,4],new,mu[4])
    if not np.array_equal(candidate[:,:4],control[:,:4]):raise AssertionError('Protected test targets changed')
    candidate_hash=export_submission(sample,candidate,output/'submission_spectral.csv')
    np.savez_compressed(output/'private_refit_predictions.npz',truth=y,table=oof['table'],official=oof['official'],mean=oof['mean'],branch=branch,control=control,candidate=candidate)
    result={'schema':1,'experiment':'accepted_firms_only_full_refit','rows':len(test),'train_rows':n,'sites':len(set(groups)),
            'control_sha256':control_hash,'candidate_sha256':candidate_hash,'protected_targets_byte_equal':True,
            'control_choices':choices,'firms_choice':new_choice,'seconds':time.monotonic()-tick,
            'scored_submission_made':False,'fresh_session_replay_verified':False,
            'limits':['Full-training OOF selects final weights; it is not an untouched accuracy estimate.',
                      'Private final CSV; no scored export before fresh-session reproduction.',
                      'No physical fire, emission or spatial-mechanism claim follows from this score.']}
    write_json(output/'refit_receipt.json',result)
    print('SPECTRAL_REFIT_BEGIN');print(json.dumps(result,sort_keys=True));print('SPECTRAL_REFIT_END',flush=True)
    return result
