import numpy as np
import pytest
from spectral_lab.hotspots import extract

def scene(position=None,kind='hot'):
    x=np.zeros((14,64,64),dtype=np.uint16);x[:12]=1000;x[8]=2000;x[10]=1500;x[11]=1000;x[12]=5
    if position:
        row,col=position;sl=(slice(row,row+7),slice(col,col+7))
        spectrum=(2100,4000,8000) if kind=='hot' else (6000,7000,8000)
        for band,v in zip([8,10,11],spectrum):x[band][sl]=v
    return x

def test_equal_b12_brightness_does_not_imply_equal_thermal_features():
    hot,reflect=scene((25,25)),scene((25,25),'reflective')
    assert np.array_equal(hot[11],reflect[11])
    h,_=extract(hot);r,_=extract(reflect)
    assert h['thermal'][3]==32 and r['thermal'][3]==0
    assert h['thermal'][9]==1 and h['thermal'][6]>0
    np.testing.assert_allclose(h['brightness'],r['brightness'],equal_nan=True)

def test_anomaly_features_translate_without_center_assumption_and_ignore_b8():
    values=[extract(scene(pos))[0]['thermal'] for pos in [(25,25),(10,39),(39,10)]]
    for v in values[1:]:np.testing.assert_allclose(v,values[0],atol=1e-10,equal_nan=True)
    x=scene((25,25));x[7]=65535
    np.testing.assert_allclose(extract(x)[0]['thermal'],values[0],equal_nan=True)

def test_missing_support_distinct_from_observed_no_candidate_and_no_uint_underflow():
    flat=scene();obs,_=extract(flat);empty,_=extract(np.zeros_like(flat))
    assert obs['thermal'][3]==0 and np.isnan(empty['thermal']).all()
    assert obs['quality'][0]==1 and empty['quality'][0]==0
    assert not any(np.isinf(v).any() for v in obs.values())
    assert np.isnan(obs['thermal'][0])  # B12<B11 cannot wrap into a huge positive anomaly.

def test_quality_flags_scramble_and_source_contract():
    x=scene((25,25));x[13,25:32,25:32]=100
    a,_=extract(x);b,_=extract(x)
    assert a['thermal'][10]==1
    for name in a:np.testing.assert_array_equal(a[name],b[name])
    assert not np.allclose(a['thermal'],a['scrambled'],equal_nan=True)
    for bad in [x[:13],x.astype(float)*np.nan]:
        with pytest.raises(ValueError):extract(bad)
    x[13,0,0]=101
    with pytest.raises(ValueError):extract(x)
