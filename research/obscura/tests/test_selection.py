import numpy as np
import pytest
from atmospheric_lab.selection import choose_mix, mix_predictions, nested_compare
from atmospheric_lab.baseline import PARAMS


def test_mix_can_reject_a_bad_predictor_and_ignores_missing_truth():
    y=np.array([1.,2.,np.nan,3.,4.])
    base=np.zeros(5)
    enhanced=np.array([1.,2.,999.,3.,4.])
    means=np.zeros(5)
    choice=choose_mix(y,base,enhanced,means)
    assert choice['amplitude']==1 and choice['image_weight']==1
    assert choice['inner_rmse']==0
    assert choose_mix(np.zeros(5),np.ones(5),np.ones(5),np.zeros(5))['amplitude']==0
    with pytest.raises(ValueError): choose_mix(y,base,np.full(5,np.nan),means)


def test_mix_is_convex_and_preserves_fitted_mean_as_zero_amplitude():
    assert np.allclose(mix_predictions(np.array([1,3]),np.array([5,7]),2.,.5,.5),[2.5,3.5])
    assert np.all(mix_predictions(np.ones(5),np.arange(5),4.,0,1)==4)


def test_outer_heldout_labels_cannot_affect_that_folds_fitted_prediction():
    rng=np.random.default_rng(31)
    x=rng.normal(size=(90,3))
    y=np.repeat(x[:,:1],5,axis=1)+rng.normal(scale=.2,size=(90,5))
    groups=np.repeat(np.arange(9),10)
    params={**PARAMS,'max_iter':4,'min_samples_leaf':3}
    from atmospheric_lab.core import site_folds
    folds=site_folds(groups,3)
    first=nested_compare({'table':x,'image':np.column_stack([x,x[:,0]**2])},y,groups,folds,inner_splits=2,params=params)
    changed=y.copy()
    changed[folds[0][1]]=changed[folds[0][1]]+100
    second=nested_compare({'table':x,'image':np.column_stack([x,x[:,0]**2])},changed,groups,folds,inner_splits=2,params=params)
    for variant in ['table','image']:
        assert np.array_equal(first['predictions'][variant][folds[0][1]],second['predictions'][variant][folds[0][1]])
        assert first['folds'][0]['choices'][variant]==second['folds'][0]['choices'][variant]
