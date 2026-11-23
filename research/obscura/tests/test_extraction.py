import numpy as np
import rasterio
import pytest
from atmospheric_lab.experiment import feature_matrices, extract_one
from atmospheric_lab.core import site_folds


def test_actual_geotiff_extractor_cache_and_feature_variants(tmp_path,monkeypatch):
    folder=tmp_path/'images'
    folder.mkdir()
    a=np.full((14,40,40),2000,dtype='uint16')
    a[3]=1000; a[7]=3000; a[12]=5; a[13]=0
    with rasterio.open(folder/'synthetic.tif','w',driver='GTiff',height=40,width=40,count=14,dtype='uint16') as dest:
        dest.write(a)
    official,revised,spatial=extract_one(folder/'synthetic.tif')
    assert len(official)==54 and len(revised)==57 and len(spatial)==73
    assert revised['q_clear_count']==1600
    matrices,summary=feature_matrices(tmp_path,['synthetic'],tmp_path/'cache.npz',workers=1)
    assert matrices['spatial'].shape==(1,73)
    assert summary['insufficient_clear_fraction']==0
    assert all('sample_id' not in v for v in summary['column_names'].values())
    monkeypatch.setattr(rasterio,'open',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Cache miss')))
    replay,replayed_summary=feature_matrices(tmp_path,['synthetic'],tmp_path/'cache.npz',workers=1)
    assert np.array_equal(replay['spatial'],matrices['spatial'],equal_nan=True)
    assert replayed_summary==summary
    with np.load(tmp_path/'cache.npz',allow_pickle=False) as saved:
        corrupt={name:saved[name].copy() for name in saved.files}
    corrupt['spatial']=np.zeros((1,72))
    np.savez_compressed(tmp_path/'cache.npz',**corrupt)
    with pytest.raises(ValueError,match='schema/integrity'):
        feature_matrices(tmp_path,['synthetic'],tmp_path/'cache.npz',workers=1)


def test_extractor_source_change_invalidates_cache(tmp_path,monkeypatch):
    import atmospheric_lab.experiment as module
    folder=tmp_path/'images'; folder.mkdir()
    a=np.full((14,40,40),2000,dtype='uint16')
    a[12]=5; a[13]=0
    with rasterio.open(folder/'synthetic.tif','w',driver='GTiff',height=40,width=40,count=14,dtype='uint16') as dest:
        dest.write(a)
    before,first=feature_matrices(tmp_path,['synthetic'],tmp_path/'cache.npz',workers=1)
    original=module.extract_one
    def changed(path):
        official,revised,spatial=original(path)
        revised['q_clear_count']=1234.
        spatial['q_clear_count']=1234.
        return official,revised,spatial
    monkeypatch.setattr(module,'extract_one',changed)
    after,second=feature_matrices(tmp_path,['synthetic'],tmp_path/'cache.npz',workers=1)
    assert first['feature_source_sha256']!=second['feature_source_sha256']
    index=second['column_names']['no_fallback'].index('q_clear_count')
    assert before['no_fallback'][0,index]==1600 and after['no_fallback'][0,index]==1234


def test_seeded_folds_are_reproducible_and_group_disjoint():
    groups=np.repeat(np.arange(18),5)
    first=site_folds(groups,3,seed=2026)
    second=site_folds(groups,3,seed=2026)
    for (fit,check),(again_fit,again_check) in zip(first,second):
        assert np.array_equal(fit,again_fit) and np.array_equal(check,again_check)
        assert set(groups[fit]).isdisjoint(groups[check])
