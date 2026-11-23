import numpy as np
import pandas as pd
import pytest
from spectral_lab import comparison as c
from spectral_lab.selection import choose_mix,mix_predictions

def test_zero_branch_matches_incumbent_selection():
    rng=np.random.default_rng(10);y=rng.normal(size=90);b=rng.normal(size=90);e=rng.normal(size=90);m=np.zeros(90)
    # A duplicate official branch cannot improve the incumbent's grid.
    choice=c.choose_branch(y,b,e,e,m);old=choose_mix(y,b,e,m)
    assert np.allclose(c.branch_predict(choice,b,e,e,m),mix_predictions(b,e,m,old['amplitude'],old['image_weight']))
    assert c.choose_branch(np.zeros(90),b,e,e,m)['branch_weight']==0

def fake_fit(x,y,z):
    return np.full(len(z),np.nanmean(y))+.01*np.nan_to_num(z[:,0])

def test_outer_labels_cannot_change_predictions_and_four_targets_protected():
    rng=np.random.default_rng(22);g=np.repeat(np.arange(12),4);y=rng.normal(size=(48,5));x=rng.normal(size=(48,3))
    f={name:x.copy() for name in ['table','official',*c.VARIANTS]};fit=np.arange(36);check=np.arange(36,48)
    pred,choices,_=c.outer(f,y,g,fit,check,fake_fit)
    other=y.copy();other[check]=1e6
    altered,changed,_=c.outer(f,other,g,fit,check,fake_fit)
    assert choices==changed
    for name in pred:
        assert np.array_equal(pred[name],altered[name])
        assert np.array_equal(pred[name][:,:4],pred['C'][:,:4])
    assert abs(c.metric(y[check],pred['C'])['mcrmse']-c.metric(y[check],pred['F'])['mcrmse']-(c.metric(y[check],pred['C'])['rmse']['t_firms']-c.metric(y[check],pred['F'])['rmse']['t_firms'])/5)<1e-12

def test_environment_partition_is_label_free_and_site_disjoint():
    rng=np.random.default_rng(17);groups=np.repeat(np.arange(16),3)
    columns=['temperature','humidity','wind_speed','precipitation','solar_rad','elevation','slope']
    x=rng.normal(size=(48,7));x[24:]+=10;table=pd.DataFrame(x,columns=columns)
    folds,receipt=c.environment_folds(table,groups)
    table['t_firms']=rng.normal(size=48);again,_=c.environment_folds(table,groups)
    assert not receipt['uses_targets']
    assert min(receipt['site_counts'])>=5
    for (a,b),(aa,bb) in zip(folds,again):
        assert np.array_equal(a,aa) and np.array_equal(b,bb)
        assert not set(groups[a])&set(groups[b])

def test_fit_only_missing_feature_guard():
    x=np.column_stack([np.arange(50),np.full(50,np.nan)]);y=np.sin(np.arange(50));z=np.array([[2.,1e5],[3.,-1e5]])
    first=c.safe_fit(x,y,z);z[:,1]*=1e4
    assert np.array_equal(first,c.safe_fit(x,y,z))
