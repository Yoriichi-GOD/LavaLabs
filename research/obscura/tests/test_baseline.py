import json
import numpy as np
import pandas as pd
from atmospheric_lab.baseline import run, PARAMS
from atmospheric_lab.core import TARGETS


def test_actual_estimator_pipeline_runs_masked_and_exports_finite_rows(tmp_path):
    rng = np.random.default_rng(17)
    rows = 120
    names = [f'x{i}' for i in range(29)]
    train = pd.DataFrame(rng.normal(size=(rows,29)),columns=names)
    train.insert(0,'site_key',np.repeat([f'g{i}' for i in range(12)],10))
    train.insert(0,'sample_id',[f'train{i}' for i in range(rows)])
    for j,name in enumerate(TARGETS):
        train[name]=train[f'x{j}']*.7+rng.normal(0,.1,rows)
        train.loc[np.arange(rows)%5==j,name]=np.nan
    train.loc[0,'x0']=np.nan
    test = pd.DataFrame(rng.normal(size=(5,29)),columns=names)
    test.insert(0,'sample_id',['0001','123e456','abc','def','ghi'])
    sample = test[['sample_id']].copy()
    sample[TARGETS]=0.
    for name,frame in [('train',train),('test',test),('sample_submission',sample)]:
        frame.to_csv(tmp_path/f'{name}.csv',index=False)
    receipt = run(tmp_path,tmp_path/'private',3,{**PARAMS,'max_iter':8,'min_samples_leaf':5},expected_rows=5)
    assert receipt['validation']['site_overlap'] is False
    assert receipt['validation']['pooled_model']['observed'][TARGETS[0]] == 96
    assert receipt['submission']['finite'] and len(receipt['submission']['sha256'])==64
    assert json.loads((tmp_path/'private/baseline_receipt.json').read_text())['counts']['test']==5
