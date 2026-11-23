"""Separate disk-to-truth verification of saved private spectral outputs."""
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from .core import TARGETS,load_tables,write_json
from .independent_audit import independent_score,paired_site_summary

def audit(root,output):
    output=Path(output);receipt=json.loads((output/'spectral_receipt.json').read_text())
    train,_,_,names=load_tables(root);groups=train.site_key.to_numpy()
    dev,_=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(train[names],groups=groups))
    truth=train[TARGETS].to_numpy(dtype=float)[dev];groups=groups[dev].astype(str)
    result={'schema':1,'outputs':{},'rows_exported':False,'test_labels_accessed':False}
    for name,file,key in [('development','private_development_predictions.npz','development'),('environment','private_environment_predictions.npz','environment_stress')]:
        path=output/file
        with np.load(path,allow_pickle=False) as saved:
            if not np.array_equal(truth,saved['truth'],equal_nan=True) or not np.array_equal(groups,saved['groups']):raise ValueError('Saved truth/group mismatch')
            scores={variant:independent_score(truth,saved[variant]) for variant in ['C','Q','B','A','F','S']}
            for variant,score in scores.items():
                stated=receipt[key]['scores'][variant]
                if abs(score['mcrmse']-stated['mcrmse'])>1e-12 or score['observed']!=stated['observed']:raise ValueError('Saved metric mismatch')
                for t in TARGETS:
                    if abs(score['rmse'][t]-stated['rmse'][t])>1e-12:raise ValueError('Target RMSE mismatch')
                if not np.array_equal(saved['C'][:,:4],saved[variant][:,:4]):raise ValueError('Protected target mismatch')
            if name=='development':
                boot=paired_site_summary(truth,saved['C'],saved['F'],groups)
                if boot!=receipt['paired_sites']:raise ValueError('Bootstrap replay mismatch')
        result['outputs'][name]={'scores':scores,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'truth_and_sites_verified':True}
    result['passed']=True
    write_json(output/'independent_spectral_audit.json',result)
    print('SPECTRAL_AUDIT_BEGIN');print(json.dumps(result,sort_keys=True));print('SPECTRAL_AUDIT_END',flush=True)
    return result
