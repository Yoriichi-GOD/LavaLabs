import numpy as np
import pandas as pd
import pytest
from atmospheric_lab.core import TARGETS, metric, site_folds, validate_tables, export_submission


def tables():
    train = pd.DataFrame({'sample_id': ['train0','train1'], 'site_key':['a','b'], 'x':[1.,2.]})
    test = pd.DataFrame({'sample_id':['123e456','0001'], 'x':[3.,4.]})
    sample = test[['sample_id']].copy()
    for name in TARGETS:
        train[name] = [1.,np.nan]
        sample[name] = 0.
    return train, test, sample


def test_metric_uses_each_targets_observed_denominator():
    y = np.array([[1,2,3,4,5],[np.nan,4,5,6,7]], dtype=float)
    p = np.zeros_like(y)
    got = metric(y,p)
    expected = [1,np.sqrt(10),np.sqrt(17),np.sqrt(26),np.sqrt(37)]
    assert got['mcrmse'] == pytest.approx(np.mean(expected))
    assert list(got['observed'].values()) == [1,2,2,2,2]
    p[1,0] = np.nan
    with pytest.raises(ValueError): metric(y,p)
    with pytest.raises(ValueError): metric(np.full((2,5),np.nan),np.zeros((2,5)))


def test_site_split_never_sees_a_validation_facility():
    groups = np.repeat(['a','b','c','d','e','f'], [2,4,1,5,3,2])
    folds = site_folds(groups,3)
    for fit, check in folds: assert set(groups[fit]).isdisjoint(groups[check])
    assert sorted(np.concatenate([check for _,check in folds])) == list(range(len(groups)))
    with pytest.raises(ValueError): site_folds(['a','a'],2)


def test_csv_preserves_numeric_looking_string_identifiers(tmp_path):
    train,test,sample = tables()
    assert validate_tables(train,test,sample) == ['x']
    path = tmp_path/'submission.csv'
    export_submission(sample, np.arange(10).reshape(2,5)/7, path)
    got = pd.read_csv(path,dtype={'sample_id':str})
    assert list(got.sample_id) == ['123e456','0001']
    assert list(got.columns) == ['sample_id',*TARGETS]
    assert np.allclose(got[TARGETS],np.arange(10).reshape(2,5)/7)
    with pytest.raises(ValueError): export_submission(sample,np.full((2,5),np.inf),path)


@pytest.mark.parametrize('fault',['duplicate','order','overlap','feature','missingtarget','numericid'])
def test_contract_rejects_actual_export_and_leakage_failures(fault):
    train,test,sample = tables()
    if fault == 'duplicate': test.loc[1,'sample_id'] = test.loc[0,'sample_id']
    if fault == 'order': sample = sample.iloc[::-1]
    if fault == 'overlap': train.loc[0,'sample_id'] = test.loc[0,'sample_id']
    if fault == 'feature': test['site_key'] = ['a','b']
    if fault == 'missingtarget': train[TARGETS[0]] = np.nan
    if fault == 'numericid': test['sample_id'] = pd.Series([123,'0001'],dtype=object)
    with pytest.raises(ValueError): validate_tables(train,test,sample)
