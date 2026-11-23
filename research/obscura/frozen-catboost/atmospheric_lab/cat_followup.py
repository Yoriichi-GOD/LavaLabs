"""One predeclared Ordered CatBoost comparison. No leaderboard parameter search."""
from pathlib import Path
import importlib.metadata
import time
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from .core import TARGETS,load_tables,site_folds,write_json,export_submission
from .experiment import feature_matrices,_public_summary
from .selection import nested_compare,final_predict

CAT_PARAMS=dict(loss_function='RMSE',iterations=400,learning_rate=.03,depth=3,
    grow_policy='SymmetricTree',boosting_type='Ordered',l2_leaf_reg=10.,
    bootstrap_type='Bernoulli',subsample=.8,sampling_frequency='PerTree',rsm=.8,
    random_strength=1.,random_seed=2026,nan_mode='Min',boost_from_average=True,
    use_best_model=False,task_type='CPU',thread_count=2,verbose=False,allow_writing_files=False)


def fit_cat(x,y,z,params=None):
    from catboost import CatBoostRegressor
    x,y,z=map(np.asarray,[x,y,z])
    if x.ndim!=2 or z.ndim!=2 or y.ndim!=1 or len(x)!=len(y) or x.shape[1]!=z.shape[1]:
        raise ValueError('CatBoost inputs must be numeric matrices and one target vector')
    if any(a.dtype.kind not in 'fiu' for a in [x,y,z]) or any(np.isinf(a).any() for a in [x,y,z]):
        raise ValueError('CatBoost inputs must be numeric and cannot contain infinity')
    keep=np.isfinite(y)
    if keep.sum()<2:raise ValueError('Not enough observed CatBoost fitting labels')
    x,y,z=x.astype(float),y.astype(float),z.astype(float)
    if np.ptp(y[keep])==0:
        return None,np.full(len(z),float(y[keep][0]))
    model=CatBoostRegressor(**(CAT_PARAMS if params is None else params))
    model.fit(x[keep],y[keep])
    if model.tree_count_!=(CAT_PARAMS if params is None else params)['iterations']:
        raise AssertionError('Unexpected CatBoost iteration selection')
    prediction=model.predict(z)
    if not np.isfinite(prediction).all():raise ValueError('Nonfinite CatBoost prediction')
    return model,prediction


def run(root,output,cache='/kaggle/temp/lavalabs_features_v1.npz'):
    started=time.monotonic();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    train,test,sample,columns=load_tables(root)
    x=train[columns].to_numpy(dtype=float);z=test[columns].to_numpy(dtype=float)
    y=train[TARGETS].to_numpy(dtype=float);groups=train.site_key.to_numpy()
    matrices,features=feature_matrices(root,[*train.sample_id,*test.sample_id],cache)
    all_features={'table':x,'official':np.column_stack([x,matrices['official'][:len(x)]])}
    test_features={'table':z,'official':np.column_stack([z,matrices['official'][len(x):]])}
    all_features['cat']=all_features['official'];test_features['cat']=test_features['official']
    dev,_=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(x,groups=groups))
    counter={'fits':0,'seconds':[],'resolved':None}
    def bounded_fit(a,b,c,params=None):
        if counter['fits']>=90 or time.monotonic()-started>7200:
            raise RuntimeError('Fixed CatBoost experiment exceeded its 90-fit / two-hour cap; retain v2.')
        tick=time.monotonic();model,pred=fit_cat(a,b,c)
        counter['fits']+=1;counter['seconds'].append(time.monotonic()-tick)
        if model is not None and counter['resolved'] is None:counter['resolved']=model.get_all_params()
        if counter['fits'] in [1,2]:
            estimated=np.mean(counter['seconds'])*(90-counter['fits'])
            print('CatBoost timed fit',counter['fits'],round(counter['seconds'][-1],3),'seconds; remaining fit projection',round(estimated,1),flush=True)
            if estimated+time.monotonic()-started>7200:
                raise RuntimeError('Fixed CatBoost fit timing exceeds two-hour cap; retain v2 without retuning.')
        return model,pred
    comparison=nested_compare({k:v[dev] for k,v in all_features.items()},y[dev],groups[dev],
        site_folds(groups[dev],3,seed=2026),inner_splits=3,fitters={'cat':bounded_fit})
    control=comparison['scores']['official']['mcrmse'];candidate=comparison['scores']['cat']['mcrmse']
    fold_wins=sum(f['scores']['cat']['mcrmse']<f['scores']['official']['mcrmse']-1e-10 for f in comparison['folds'])
    retained='cat' if candidate<control-1e-10 and fold_wins>=2 else 'official'
    receipt={'schema':1,'experiment':'one_fixed_ordered_catboost','parameters':CAT_PARAMS,
      'catboost_version':importlib.metadata.version('catboost'),'comparison':_public_summary(comparison),
      'decision':{'retained':retained,'cat_fold_wins':fold_wins,'rule':'Cat must improve pooled development MCRMSE by >1e-10 and win at least two of three paired outer folds; otherwise retain v2 official.'},
      'counts':{'train':len(train),'test':len(test),'sites':len(set(groups)),'development_sites':len(set(groups[dev]))},
      'limitations':['This is iterative development on previously used sites, not new independent confirmation.','The previous confirmation sites are not scored again for this comparison.','Private/future-time transfer remains unknown. No public-score fitting.'],
      'feature_extraction':features,'si_disclosure':'OpenAI Codex assisted code, tests and analysis. Original competition observations unchanged.'}
    write_json(output/'selection_before_refit.json',receipt)
    if retained=='cat':
        pred,choices=final_predict(all_features,test_features,y,groups,'cat',n_splits=5,fitters={'cat':bounded_fit})
        digest=export_submission(sample,pred,output/'submission_cat.csv')
        receipt.update(final_choices=choices,submission={'rows':len(test),'sha256':digest,'file':'submission_cat.csv'})
    receipt.update(cat_fits=counter['fits'],cat_fit_seconds=counter['seconds'],resolved_catboost_parameters=counter['resolved'],seconds=time.monotonic()-started)
    write_json(output/'catboost_receipt.json',receipt)
    print('FIXED_CATBOOST_COMPLETE',{'retained':retained,'control':control,'candidate':candidate,'fold_wins':fold_wins,'seconds':round(receipt['seconds'],1)},flush=True)
    return receipt
