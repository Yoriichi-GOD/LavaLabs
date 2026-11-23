"""First measured baseline. Official HistGB recipe, supplied features, no selection."""
from pathlib import Path
import importlib.metadata
import platform
import time
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
from .core import TARGETS, SOURCE, load_tables, site_folds, metric, export_submission, write_json

PARAMS = dict(max_iter=250, learning_rate=.04, max_depth=3,
              min_samples_leaf=40, l2_regularization=5., max_features=.6,
              random_state=0, early_stopping=False)


def fit_predict(x, y, z, params=None):
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(y)
    if keep.sum() < 2:
        raise ValueError('Not enough measured labels in the fitting partition')
    with threadpool_limits(limits=2):
        model = HistGradientBoostingRegressor(**(PARAMS if params is None else params))
        model.fit(np.asarray(x)[keep], y[keep])
        prediction = model.predict(z)
    if not np.isfinite(prediction).all():
        raise ValueError('Estimator produced a nonfinite prediction')
    return model, prediction


def run(root, output, n_splits=5, params=None, expected_rows=1221):
    started = time.monotonic()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    train, test, sample, names = load_tables(root, expected_rows)
    x = train[names].to_numpy(dtype=float)
    z = test[names].to_numpy(dtype=float)
    y = train[TARGETS].to_numpy(dtype=float)
    folds = site_folds(train.site_key.to_numpy(), n_splits)
    oof = np.full(y.shape, np.nan)
    mean_oof = np.full(y.shape, np.nan)
    fold_reports = []
    for fold_number, (fit, check) in enumerate(folds, 1):
        tick = time.monotonic()
        for j in range(5):
            _, oof[check, j] = fit_predict(x[fit], y[fit, j], x[check], params)
            mean_oof[check, j] = np.nanmean(y[fit, j])
        report = metric(y[check], oof[check])
        report.update(fold=fold_number, seconds=round(time.monotonic()-tick, 3),
                      heldout_sites=int(train.iloc[check].site_key.nunique()),
                      fit_sites=int(train.iloc[fit].site_key.nunique()))
        fold_reports.append(report)
        print(f'Fold {fold_number}/{n_splits}: MCRMSE {report["mcrmse"]:.6f}; {report["seconds"]:.1f}s', flush=True)
    predictions = np.zeros((len(test), 5))
    for j in range(5):
        _, predictions[:, j] = fit_predict(x, y[:, j], z, params)
    export_hash = export_submission(sample, predictions, output/'submission_table.csv')
    receipt = {'schema': 1, 'experiment': 'supplied_table_unselected_histgb',
               'si_disclosure': 'OpenAI Codex assisted code, tests and documentation; source observations retain competition provenance.',
               'baseline_reference': SOURCE, 'baseline_adaptation': '29 supplied features; explicit no early stopping; no OOF-tuned shrinkage.',
               'counts': {'train': len(train), 'test': len(test), 'sites': int(train.site_key.nunique()), 'features': len(names)},
               'validation': {'method': 'whole-site GroupKFold', 'folds': n_splits, 'site_overlap': False,
                              'selection': 'none; fixed baseline parameters', 'pooled_model': metric(y, oof),
                              'pooled_fold_mean': metric(y, mean_oof), 'pooled_zero': metric(y, np.zeros_like(y)),
                              'fold_reports': fold_reports},
               'parameters': PARAMS if params is None else params, 'seconds': round(time.monotonic()-started, 3),
               'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','scipy']}},
               'submission': {'rows': len(test), 'sha256': export_hash, 'finite': True, 'private_file': 'submission_table.csv'},
               'boundary': 'Unseen-site validation within training time; private/future-time performance is unknown. No leaderboard score yet.'}
    write_json(output/'baseline_receipt.json', receipt)
    print('BASELINE_COMPLETE', flush=True)
    print(receipt['validation']['pooled_model'], flush=True)
    return receipt
