import json
import numpy as np
import pandas as pd
import pytest
from spectral_lab import refit as r
from spectral_lab.core import TARGETS

def test_refit_refuses_failed_gate_before_reading_observations(tmp_path,monkeypatch):
    (tmp_path/'spectral_receipt.json').write_text(json.dumps({'gate':{'passed':False}}))
    (tmp_path/'independent_spectral_audit.json').write_text(json.dumps({'passed':True}))
    def forbidden(*args):raise AssertionError('Read observations despite failed gate')
    monkeypatch.setattr(r,'load_tables',forbidden)
    with pytest.raises(ValueError,match='Accepted audited'):r.run(tmp_path,tmp_path)

def test_refit_identity_mismatch_blocks_candidate_export(tmp_path,monkeypatch):
    (tmp_path/'spectral_receipt.json').write_text(json.dumps({'gate':{'passed':True}}))
    (tmp_path/'independent_spectral_audit.json').write_text(json.dumps({'passed':True}))
    rng=np.random.default_rng(10);n=60;names=[f'x{i}' for i in range(29)]
    train=pd.DataFrame(rng.normal(size=(n,29)),columns=names);test=pd.DataFrame(rng.normal(size=(4,29)),columns=names)
    train['sample_id']=[f'train{i}' for i in range(n)];train['site_key']=np.repeat(np.arange(10),6).astype(str)
    train[TARGETS]=rng.normal(size=(n,5));test['sample_id']=[f'test{i}' for i in range(4)]
    sample=test[['sample_id']].copy();sample[TARGETS]=0.
    monkeypatch.setattr(r,'load_tables',lambda root:(train,test,sample,names))
    values={name:rng.normal(size=(n+4,w)) for name,w in dict(official=54,quality=4,brightness=6,thermal=12,scrambled=12).items()}
    monkeypatch.setattr(r,'matrices',lambda *args:(values,{}))
    monkeypatch.setattr(r,'safe_fit',lambda x,y,z:np.full(len(z),np.nanmean(y)))
    calls=[]
    def export(sample,p,path):calls.append(str(path));return 'wrong-frozen-identity'
    monkeypatch.setattr(r,'export_submission',export)
    with pytest.raises(ValueError,match='Frozen final control CSV identity mismatch'):r.run(tmp_path,tmp_path)
    assert len(calls)==1 and calls[0].endswith('private_control_replay.csv')
    assert not (tmp_path/'refit_receipt.json').exists()
