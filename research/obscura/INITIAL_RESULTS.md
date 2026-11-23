# First actual atmospheric baseline

Observed in the private Kaggle notebook on 23 November 2026. These are measured LavaLabs validation results, not copied organizer/example scores. The first genuine competition submission completed successfully with **public MCRMSE 1.32129**. Private-test accuracy remains unknown.

Notebook: `https://www.kaggle.com/code/saishreeksingh/lavalabs-atmospheric-lab-baseline?scriptVersionId=372915885`, displayed title **LavaLabs Atmospheric Lab - Baseline**. Share dialog confirmed **Private — Only collaborators can view this notebook**. Saved Version 1 displayed **Successful** after a fresh Save & Run All. The interactive baseline cell reported 9.361 seconds; the saved replay's viewer reported 31.3 seconds including setup.

Fixed recipe: 29 supplied numeric features, target-wise HistGradientBoostingRegressor, whole-site five-fold GroupKFold, parameters from the official starter with explicit `early_stopping=False`, two numerical threads, no post-hoc shrinkage or hyperparameter selection. Missing labels are masked per target. The Kaggle input was attached automatically from the competition; no restricted inputs or predictions were downloaded to this workspace.

| Target | Pooled held-out-site RMSE | Observed labels |
| --- | ---: | ---: |
| CH4 | 1.0412484901 | 1,113 |
| NO2 | 0.9612982864 | 3,130 |
| CO | 1.0222994788 | 3,188 |
| AAI | 0.6340371848 | 3,218 |
| FIRMS | 1.1730271517 | 3,218 |
| **Masked mean RMSE** | **0.9663821184** | Per-target masking above |

Fold MCRMSE: 0.961113, 0.982910, 1.077347, 0.787863, 0.965585. These fold scores must not be averaged as a substitute for pooled target-wise MCRMSE.

The pipeline completed its finite export and string-ID round-trip assertions and reported **Private CSV ready**. Its private `submission_table.csv` contains all 1,221 test rows, SHA256 `a3007dce4139cce512e5f448708fab6da4f822567c0e5bd98f99cab04f51d5a6`. The private `baseline_receipt.json` retains parameters, environment, comparison scores and prediction hash. The competition Submissions page visibly showed Success / Complete and public score 1.32129; no final selection checkbox was set.

Interpretation: AAI is the strongest target for this baseline. CH4, CO and FIRMS raw-model errors exceed the fixed-zero reference (approximately 1 on the organizer's standardized training record). This motivates conservative inner-site selection; it does not prove irreducible noise or that a new model cannot improve. No temporal-transfer or private-test accuracy claim is made.

Local verification so far: **21 tests passed in 16.63 seconds**, covering masked metric, IDs/export, site folds, cloud/spatial features, actual synthetic-raster extraction, model-to-CSV execution and an outer-label perturbation leakage regression. One initial fixture failed because pandas' string dtype rejected an intentionally inserted integer before the contract could run; the fixture now explicitly uses mixed object dtype and exercises the actual rejection path.

The public-versus-validation gap is evidence against treating local cross-validation as a reliable test-error estimate. It motivates conservative models and explicit distribution-shift limitations; one public result does not identify whether geographic, temporal or other shift caused the gap. Do not tune feature families or weights against repeated public submissions.

Research refinement predeclared before image results: official 54 summaries; no-cloudy-fallback variant with three coverage flags; then sixteen relative centre/outer/gradient/SWIR descriptors. These are content-only predictors with no geographic interpretation. The exact definition is frozen in `atmospheric_lab/features.py` and will be evaluated on common outer sites with inner-only mixture selection.
