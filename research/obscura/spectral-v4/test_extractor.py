import json
import numpy as np
import pytest
from spectral_lab import extractor as e

def test_cache_reuse_identity_and_corruption(tmp_path,monkeypatch):
    calls=[]
    def fake_read(root,sid):
        calls.append(sid)
        return {n:np.full(w,len(calls),float) for n,w in dict(official=54,thermal=12,quality=4,brightness=6,scrambled=12).items()},{'support':1.}
    monkeypatch.setattr(e,'read_one',fake_read)
    # Local function source is available, so source-aware cache can be tested.
    cache=tmp_path/'cache.npz';a,_=e.matrices(tmp_path,['a','b'],cache)
    again,_=e.matrices(tmp_path,['a','b'],cache)
    assert len(calls)==2 and np.array_equal(a['thermal'],again['thermal'])
    e.matrices(tmp_path,['b','a'],cache)
    assert len(calls)==4
    with np.load(cache,allow_pickle=False) as src:saved={n:src[n].copy() for n in src.files}
    saved['thermal'][0,0]=np.inf;np.savez_compressed(cache,**saved)
    with pytest.raises(ValueError,match='Invalid private feature cache'):e.matrices(tmp_path,['b','a'],cache)
