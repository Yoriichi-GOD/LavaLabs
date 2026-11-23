"""Contracts and numerical checks for masked, whole-site atmospheric regression."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

TARGETS = ['t_ch4', 't_no2', 't_co', 't_aai', 't_firms']
SOURCE = 'https://www.kaggle.com/code/zelza0/obscura-starter-baseline'


def metric(truth, prediction):
    """Official pooled, masked target RMSEs; never ignore a bad prediction."""
    y, p = np.asarray(truth, dtype=float), np.asarray(prediction, dtype=float)
    if y.ndim != 2 or y.shape != p.shape or y.shape[1] != 5:
        raise ValueError('Expected equally shaped n-by-five targets and predictions')
    if np.isinf(y).any() or not np.isfinite(p).all():
        raise ValueError('Targets cannot be infinite; every prediction must be finite')
    present = np.isfinite(y)
    counts = present.sum(axis=0)
    if (counts == 0).any():
        raise ValueError('All five targets need at least one observed value to report MCRMSE')
    errors = [float(np.sqrt(np.mean((y[present[:, j], j] - p[present[:, j], j]) ** 2)))
              for j in range(5)]
    return {'mcrmse': float(np.mean(errors)), 'rmse': dict(zip(TARGETS, errors)),
            'observed': dict(zip(TARGETS, map(int, counts)))}


def validate_tables(train, test, sample, expected_rows=None):
    for name, frame in [('train', train), ('test', test), ('sample', sample)]:
        if frame.columns.duplicated().any() or 'sample_id' not in frame:
            raise ValueError(f'{name}: duplicate columns or missing identifier')
        ids = frame['sample_id']
        if ids.isna().any() or not ids.is_unique or not ids.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
            raise ValueError(f'{name}: identifiers must be unique, nonempty strings')
    if set(train.sample_id) & set(test.sample_id):
        raise ValueError('Training and test sample IDs overlap')
    if list(sample.columns) != ['sample_id', *TARGETS]:
        raise ValueError('Submission template columns do not match the contract')
    if list(test.sample_id) != list(sample.sample_id):
        raise ValueError('Test and template identifier order differs')
    if expected_rows is not None and len(test) != expected_rows:
        raise ValueError('Unexpected test row count')
    if 'site_key' not in train or train.site_key.isna().any():
        raise ValueError('Training sites must be present')
    features = [c for c in test if c != 'sample_id']
    if any(c in features for c in ['site_key', *TARGETS]):
        raise ValueError('Label or site identifier found among predictors')
    if set(train.columns) != {'sample_id', 'site_key', *TARGETS, *features}:
        raise ValueError('Training and test feature schemas differ')
    for frame, names in [(train, [*features, *TARGETS]), (test, features)]:
        for name in names:
            if not pd.api.types.is_numeric_dtype(frame[name]) or np.isinf(frame[name].to_numpy(dtype=float)).any():
                raise ValueError('Predictors and targets must be numerical, missing or finite')
    if train[TARGETS].notna().sum().eq(0).any():
        raise ValueError('A training target has no observations')
    return features


def load_tables(root, expected_rows=1221):
    root = Path(root)
    train = pd.read_csv(root / 'train.csv', dtype={'sample_id': str, 'site_key': str})
    test = pd.read_csv(root / 'test.csv', dtype={'sample_id': str})
    sample = pd.read_csv(root / 'sample_submission.csv', dtype={'sample_id': str})
    features = validate_tables(train, test, sample, expected_rows)
    if len(features) != 29:
        raise ValueError('Expected the official 29 supplied numerical features')
    return train, test, sample, features


def site_folds(groups, n_splits=5, seed=None):
    groups = np.asarray(groups)
    if pd.isna(groups).any() or len(set(groups)) < n_splits:
        raise ValueError('Not enough valid sites for the requested folds')
    splitter = GroupKFold(n_splits=n_splits) if seed is None else GroupKFold(n_splits=n_splits,shuffle=True,random_state=seed)
    folds = list(splitter.split(np.zeros(len(groups)), groups=groups))
    seen = np.zeros(len(groups), dtype=int)
    for fit, check in folds:
        if set(groups[fit]) & set(groups[check]):
            raise AssertionError('Site leakage across a fold')
        seen[check] += 1
    if not np.all(seen == 1):
        raise AssertionError('Every row must be held out exactly once')
    return folds


def export_submission(sample, predictions, destination):
    p = np.asarray(predictions, dtype=float)
    if p.shape != (len(sample), 5) or not np.isfinite(p).all():
        raise ValueError('Test predictions must be finite and match all template rows')
    if not sample.sample_id.is_unique or not sample.sample_id.map(lambda x: isinstance(x, str)).all():
        raise ValueError('Invalid submission identifiers')
    result = sample[['sample_id']].copy()
    result[TARGETS] = p
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False, float_format='%.9g')
    replay = pd.read_csv(path, dtype={'sample_id': str})
    if list(replay.sample_id) != list(sample.sample_id) or not np.isfinite(replay[TARGETS]).all().all():
        raise AssertionError('Export round trip failed')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
