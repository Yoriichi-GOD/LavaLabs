"""Target-wise conservative mixtures with selection confined to inner sites."""
import time
import numpy as np
from .core import TARGETS, metric, site_folds
from .baseline import fit_predict

AMPLITUDES = [0.,.25,.5,.75,1.]
IMAGE_WEIGHTS = [0.,.5,1.]


def mix_predictions(base, enhanced, mean, amplitude, image_weight):
    if not (0<=amplitude<=1 and 0<=image_weight<=1):
        raise ValueError('Only convex prediction mixtures are permitted')
    base,enhanced,mean = map(np.asarray,[base,enhanced,mean])
    return mean+amplitude*((1-image_weight)*(base-mean)+image_weight*(enhanced-mean))


def choose_mix(truth, base, enhanced, means, image_weights=None):
    y,b,e,m = map(lambda a:np.asarray(a,dtype=float),[truth,base,enhanced,means])
    if any(a.shape!=y.shape for a in [b,e,m]) or not all(np.isfinite(a).all() for a in [b,e,m]):
        raise ValueError('Mixture inputs must have matching shapes and finite predictions')
    keep = np.isfinite(y)
    if np.isinf(y).any() or keep.sum()<2:
        raise ValueError('Need at least two measured, finite tuning labels')
    best=None
    for w in (IMAGE_WEIGHTS if image_weights is None else image_weights):
        for a in AMPLITUDES:
            p=mix_predictions(b,e,m,a,w)
            error=float(np.sqrt(np.mean((y[keep]-p[keep])**2)))
            key=(error,w,a)
            if best is None or error<best[0][0]-1e-12 or (abs(error-best[0][0])<=1e-12 and (w,a)<best[0][1:]):
                best=(key,{'amplitude':a,'image_weight':w,'inner_rmse':error})
    return best[1]


def raw_oof(x,y,groups,n_splits=3,params=None,fitter=None):
    fitter=fit_predict if fitter is None else fitter
    y=np.asarray(y,dtype=float)
    predictions=np.full(y.shape,np.nan)
    means=np.full(y.shape,np.nan)
    for fit,check in site_folds(groups,n_splits):
        for j in range(5):
            keep=np.isfinite(y[fit,j])
            if len(set(np.asarray(groups)[fit][keep]))<2:
                raise ValueError('Need at least two label-bearing fitting sites per target')
            _,predictions[check,j]=fitter(x[fit],y[fit,j],x[check],params)
            means[check,j]=np.nanmean(y[fit,j])
    if not np.isfinite(predictions).all() or not np.isfinite(means).all():
        raise AssertionError('Incomplete inner cross-validation')
    return predictions,means


def nested_compare(features,truth,groups,folds=None,inner_splits=3,params=None,fitters=None):
    y=np.asarray(truth,dtype=float)
    groups=np.asarray(groups)
    features={key:np.asarray(value,dtype=float) for key,value in features.items()}
    if 'table' not in features or any(len(value)!=len(y) for value in features.values()):
        raise ValueError('Features require the shared table reference and matching rows')
    folds=site_folds(groups,3) if folds is None else folds
    predictions={key:np.full(y.shape,np.nan) for key in features}
    raw={key:np.full(y.shape,np.nan) for key in features}
    means=np.full(y.shape,np.nan)
    reports=[]
    fitters={} if fitters is None else fitters
    seen=np.zeros(len(y),dtype=int)
    for number,(fit,check) in enumerate(folds,1):
        tick=time.monotonic()
        if set(groups[fit])&set(groups[check]) or np.intersect1d(fit,check).size:
            raise ValueError('Outer facility leakage')
        seen[check]+=1
        inner={}
        for name,x in features.items():
            inner[name],inner_means=raw_oof(x[fit],y[fit],groups[fit],inner_splits,params,fitters.get(name))
        for name,x in features.items():
            for j in range(5):
                _,raw[name][check,j]=fitters.get(name,fit_predict)(x[fit],y[fit,j],x[check],params)
        means[check]=np.nanmean(y[fit],axis=0)
        choices={}
        for name in features:
            choices[name]=[]
            for j in range(5):
                choice=choose_mix(y[fit,j],inner['table'][:,j],inner[name][:,j],inner_means[:,j],
                                  image_weights=[0.] if name=='table' else None)
                choices[name].append(choice)
                predictions[name][check,j]=mix_predictions(raw['table'][check,j],raw[name][check,j],
                    means[check,j],choice['amplitude'],choice['image_weight'])
        reports.append({'fold':number,'fit_sites':len(set(groups[fit])),'check_sites':len(set(groups[check])),
                        'choices':choices,'scores':{name:metric(y[check],p[check]) for name,p in predictions.items()},
                        'seconds':round(time.monotonic()-tick,3)})
        print('Outer fold',number,'scores:',{name:round(value['mcrmse'],6) for name,value in reports[-1]['scores'].items()},flush=True)
    if not np.all(seen==1):
        raise ValueError('Outer folds must hold every row out exactly once')
    scores={name:metric(y,p) for name,p in predictions.items()}
    return {'scores':scores,'folds':reports,'predictions':predictions,'raw_predictions':raw,
            'mean_predictions':means,'fold_mean_score':metric(y,means),
            'raw_scores':{name:metric(y,p) for name,p in raw.items()}}


def final_predict(train_features,test_features,truth,groups,variant,n_splits=5,params=None,fitters=None):
    y=np.asarray(truth,dtype=float)
    names=['table'] if variant=='table' else ['table',variant]
    oof={}
    test_predictions={}
    fitters={} if fitters is None else fitters
    for name in names:
        oof[name],means=raw_oof(np.asarray(train_features[name]),y,groups,n_splits,params,fitters.get(name))
        test_predictions[name]=np.zeros((len(test_features[name]),5))
        for j in range(5):
            _,test_predictions[name][:,j]=fitters.get(name,fit_predict)(train_features[name],y[:,j],test_features[name],params)
    mu=np.nanmean(y,axis=0)
    result=np.zeros_like(test_predictions['table'])
    choices=[]
    for j in range(5):
        choice=choose_mix(y[:,j],oof['table'][:,j],oof[variant][:,j],means[:,j],
                          image_weights=[0.] if variant=='table' else None)
        result[:,j]=mix_predictions(test_predictions['table'][:,j],test_predictions[variant][:,j],
                                    mu[j],choice['amplitude'],choice['image_weight'])
        choices.append(choice)
    if not np.isfinite(result).all(): raise ValueError('Nonfinite final prediction')
    return result,choices
