"""Bounded content-feature experiments and site-held-out confirmation on Kaggle."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import importlib.metadata
import inspect
import json
import platform
import time
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from . import features as feature_module
from .features import chip_summary, BAND_ORDER, _spatial
from .baseline import PARAMS
from .core import TARGETS, load_tables, site_folds, metric, write_json, export_submission
from .selection import nested_compare, final_predict


def extract_one(path):
    import rasterio
    with rasterio.open(path) as source:
        chip=source.read()  # Intentionally do not inspect geospatial/file metadata.
    official=chip_summary(chip,'official')
    clear=(chip[3]>0)&~np.isin(chip[12],[3,8,9,10])
    sufficient=clear.sum()>=500
    if sufficient:
        revised=dict(official)
        revised.update(q_insufficient_clear=0.,q_clear_count=float(clear.sum()),q_cloud_high_fraction=float((chip[13]>=40).mean()))
    else:
        revised=chip_summary(chip,'no_fallback')
    bands={name:chip[index].astype(float)*1e-4 for index,name in enumerate(BAND_ORDER[:12])}
    spatial={**revised,**_spatial(bands,clear,bool(sufficient))}
    return official,revised,spatial


def feature_matrices(root,ids,cache_path,workers=2):
    root,cache_path=Path(root),Path(cache_path)
    # Both functions define extraction; changing either must invalidate the cache.
    source_hash=hashlib.sha256((inspect.getsource(feature_module)+'\n'+inspect.getsource(extract_one)).encode()).hexdigest()
    fingerprint=hashlib.sha256((source_hash+'\n'+str(root.resolve())+'\n'+'\n'.join(ids)).encode()).hexdigest()
    if cache_path.exists():
        with np.load(cache_path,allow_pickle=False) as saved:
            if saved['fingerprint'].item()==fingerprint:
                summary=json.loads(saved['summary'].item())
                expected={'official':54,'no_fallback':57,'spatial':73}
                for name,width in expected.items():
                    value=saved[name]
                    names=summary['column_names'][name]
                    if (value.shape!=(len(ids),width) or np.isinf(value).any()
                            or len(names)!=width or names!=sorted(set(names))
                            or summary['columns'][name]!=width or summary['chip_count']!=len(ids)
                            or summary['feature_source_sha256']!=source_hash):
                        raise ValueError('Private feature cache failed schema/integrity checks; rebuild it.')
                print('Verified private feature cache loaded.',flush=True)
                return {name:saved[name].copy() for name in expected},summary
    rows={name:[] for name in ['official','no_fallback','spatial']}
    names={}
    started=time.monotonic()
    def worker(sid):
        try: return extract_one(root/'images'/f'{sid}.tif')
        except Exception:
            # Keep row identifiers and original path errors out of notebook outputs.
            raise RuntimeError('A competition image failed extraction; no fabricated fallback is permitted.') from None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for number,triplet in enumerate(pool.map(worker,ids),1):
            for name,features in zip(rows,triplet):
                keys=sorted(features)
                if name not in names: names[name]=keys
                if keys!=names[name]: raise AssertionError('Feature schema changed across chips')
                rows[name].append([features[k] for k in keys])
            if number%250==0 or number==len(ids):
                elapsed=time.monotonic()-started
                print(f'Chips {number}/{len(ids)}; {elapsed:.1f}s; estimated {(len(ids)-number)*elapsed/max(number,1)/60:.1f} min remaining',flush=True)
    matrices={name:np.asarray(value,dtype=np.float64) for name,value in rows.items()}
    for value in matrices.values():
        if np.isinf(value).any(): raise ValueError('Infinite extracted predictor')
    revised=matrices['no_fallback']
    summary={'chip_count':len(ids),'columns':{name:len(keys) for name,keys in names.items()},
             'column_names':names,'insufficient_clear_fraction':float(revised[:,names['no_fallback'].index('q_insufficient_clear')].mean()),
             'seconds':round(time.monotonic()-started,3),'feature_source_sha256':source_hash,
             'boundary':'Relative pixels only; no geographic location, ground scale or outside observations.'}
    cache_path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(cache_path,**matrices,fingerprint=np.array(fingerprint),summary=np.array(json.dumps(summary)))
    return matrices,summary


def _public_summary(comparison):
    return {key:comparison[key] for key in ['scores','folds','fold_mean_score','raw_scores']}


GATE_TOLERANCE = 1e-10


def selection_plan(scores):
    """Freeze one comparator and at most one novel challenger on development only."""
    values={name:float(value['mcrmse']) for name,value in scores.items()}
    if set(values)!={'table','official','no_fallback','spatial'} or not all(np.isfinite(list(values.values()))):
        raise ValueError('Need four finite development scores')
    control='official' if values['official']<values['table']-GATE_TOLERANCE else 'table'
    novel='spatial' if values['spatial']<values['no_fallback']-GATE_TOLERANCE else 'no_fallback'
    eligible=values[novel]<values[control]-GATE_TOLERANCE
    return {'control':control,'novel':novel,'challenger_eligible':bool(eligible),
            'candidate':novel if eligible else control,'tolerance':GATE_TOLERANCE,
            'gate_protocol':'v2: development chooses control/challenger; confirmation only accepts or rejects; custom challenger must beat both controls'}


def confirm_selection(plan,scores):
    """No best-of-confirmation search and no switching between novel families."""
    values={name:float(value['mcrmse']) for name,value in scores.items()}
    required={'table','official',plan['candidate']}
    if not required.issubset(values) or not all(np.isfinite(list(values.values()))):
        raise ValueError('Missing or nonfinite confirmation score')
    control=plan['control']
    reasons=[]
    if control=='official' and not values['official']<values['table']-GATE_TOLERANCE:
        control='table'
        reasons.append('Development-selected official control failed confirmation against table; retain table.')
    retained=control
    candidate=plan['candidate']
    if plan['challenger_eligible']:
        beats_both=all(values[candidate]<values[name]-GATE_TOLERANCE for name in ['table','official'])
        if beats_both:
            retained=candidate
            reasons.append('Frozen novel challenger passed both confirmation controls.')
        else:
            reasons.append('Frozen novel challenger failed at least one control; reject it.')
    else:
        reasons.append('No novel challenger beat the development-selected control; no novel confirmation search.')
    return retained,{'fallback_control':control,'reasons':reasons}


def run(root,output,cache='/kaggle/temp/lavalabs_features_v1.npz'):
    started=time.monotonic()
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    train,test,sample,columns=load_tables(root)
    y=train[TARGETS].to_numpy(dtype=float)
    groups=train.site_key.to_numpy()
    ids=[*train.sample_id,*test.sample_id]
    print('Input contract passed:',{'train':len(train),'test':len(test),'sites':len(set(groups))},flush=True)
    matrices,feature_receipt=feature_matrices(root,ids,cache)
    tx=train[columns].to_numpy(dtype=float)
    zx=test[columns].to_numpy(dtype=float)
    train_features={'table':tx,**{name:np.column_stack([tx,array[:len(train)]]) for name,array in matrices.items()}}
    test_features={'table':zx,**{name:np.column_stack([zx,array[len(train):]]) for name,array in matrices.items()}}
    # The confirmation sites are excluded from candidate/weight selection below.
    dev,confirmation=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(tx,groups=groups))
    assert set(groups[dev]).isdisjoint(groups[confirmation])
    dev_features={name:x[dev] for name,x in train_features.items()}
    comparison=nested_compare(dev_features,y[dev],groups[dev],site_folds(groups[dev],3,seed=2026),inner_splits=3)
    scores=comparison['scores']
    plan=selection_plan(scores)
    candidate=plan['candidate']
    # Freeze the feature family before examining confirmation labels.
    selection={**plan,'basis':'development-only control and single challenger selection; simpler families win numerical ties',
               'development_sites':len(set(groups[dev])),'confirmation_sites':len(set(groups[confirmation])),
               'development_comparison':_public_summary(comparison)}
    write_json(output/'selection_before_confirmation.json',selection)
    print('Feature family frozen before confirmation:',candidate,flush=True)
    confirmation_scores={}
    for name in dict.fromkeys(['table','official',candidate]):
        pred,_=final_predict({k:v[dev] for k,v in train_features.items()},
                             {k:v[confirmation] for k,v in train_features.items()},y[dev],groups[dev],name,n_splits=3)
        confirmation_scores[name]=metric(y[confirmation],pred)
        print('Confirmation',name,confirmation_scores[name]['mcrmse'],flush=True)
    # Confirmation is an accept/reject gate, so its selected result is not an untouched test estimate.
    retained,gate=confirm_selection(plan,confirmation_scores)
    prediction,choices=final_predict(train_features,test_features,y,groups,retained,n_splits=5)
    export_hash=export_submission(sample,prediction,output/'submission_selected.csv')
    official_prediction,official_choices=final_predict(train_features,test_features,y,groups,'official',n_splits=5)
    official_hash=export_submission(sample,official_prediction,output/'submission_official_control.csv')
    receipt={'schema':2,'experiment':'cloud_spatial_nested_site_selection',
             'si_disclosure':'OpenAI Codex assisted code, tests, analysis implementation and documentation. Competition observations retain original provenance.',
             'counts':{'train':len(train),'test':len(test),'sites':len(set(groups))},
             'feature_extraction':feature_receipt,'selection':selection,'confirmation':confirmation_scores,
             'retained_variant':retained,'confirmation_gate':gate,'retained_choices':choices,'official_control_choices':official_choices,
             'parameters':PARAMS,'final_fit':'all permitted training rows with observed target masks; final weights from whole-site OOF',
             'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','rasterio','scipy']}},
             'submissions':{'selected':{'rows':len(test),'sha256':export_hash,'file':'submission_selected.csv'},
                            'official_control':{'rows':len(test),'sha256':official_hash,'file':'submission_official_control.csv'}},
             'seconds':round(time.monotonic()-started,3),
             'limitations':['Confirmation is used for an accept/reject gate; its selected result is not an untouched estimate.',
                            'Gate v2 was fixed during initial image extraction, before any image development/confirmation scores were observed; it also requires novel changes to beat the official control.',
                            'The earlier raw baseline aggregate evaluated all training sites before this refinement, including confirmation sites.',
                            'No true forward-time validation is possible with withheld dates. Private-test error remains unknown.',
                            'Feature-family selection uses development outer scores; those selected scores have model-selection optimism.']}
    write_json(output/'experiment_receipt.json',receipt)
    print('EXPERIMENT_COMPLETE',flush=True)
    print({'development':{name:value['mcrmse'] for name,value in scores.items()},'candidate':candidate,'retained':retained,
           'confirmation':{name:value['mcrmse'] for name,value in confirmation_scores.items()},'seconds':receipt['seconds']},flush=True)
    return receipt
