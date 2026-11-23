<!-- spectral-latest-20261123 -->
# Current result: sparse spectral FIRMS follow-up

Accepted public MCRMSE **1.13057**, versus 1.15808 for the previous HistGB finalist; both are selected. Private unknown. Development **0.91950** versus **0.93378**, with two environmental holdouts, saved-array audit and exact fresh-process replay. See [the current method, controls and evidence](spectral-v4/README.md). The updated three-page report uses the same serif two-column format; the [original report and source](frozen-report-before-spectral/) are preserved. Public source contains all three guarded recipes and no row outputs.

## Historical baseline and fixed-model notes

The material below records the earlier phase; statements that model search stopped or all custom features failed are historical snapshots superseded by the controlled spectral follow-up above.

# LavaLabs Atmospheric Lab

Five-target atmospheric regression for [OBSCURA](https://www.kaggle.com/competitions/obscura), developed by Saishreek Singh. The pipeline combines permitted weather, season, terrain and spectral inputs with optional Sentinel-2 chip summaries, masks missing labels per target, validates on unseen training sites, and exports the exact competition template.

**What the experiments say so far:** conservative mixtures with the official chip summaries outperform our custom cloud/spatial extensions in the fixed development comparison. The custom extensions are rejected. This is measured model selection, not a new gas-retrieval method or a claim of leaderboard superiority. See [experiment log](EXPERIMENT_LOG.md) and [first scored baseline](INITIAL_RESULTS.md).

| Evidence | Measured result | Interpretation |
|---|---:|---|
| Raw table baseline, 5-fold site CV | 0.966382 MCRMSE | Pooled target-wise held-out errors |
| Raw table baseline, public leaderboard | 1.32129 | Genuine accepted submission; private score unknown |
| Official-summary mixture, development | 0.933783 | Inner weight selection; 3 common outer site folds |
| Official-summary mixture, public leaderboard | 1.15808 | Best observed public score; accepted and selected |
| Official-summary mixture, confirmation | 0.862056 | Accept/reject partition, not untouched final test |
| Table mixture, same confirmation | 0.887252 | Matched control for the row above |
| Fixed Ordered CatBoost, later development | 0.931200 | Same 83 inputs; two of three paired fold wins |
| Fixed Ordered CatBoost, public leaderboard | 1.16407 | Accepted; slightly worse than HistGB public 1.15808 |

The corrected private saved replay (version **372947210**) completed successfully with identical scores and prediction SHA256. The image/blending candidate received **public MCRMSE 1.15808**, a 12.35% error reduction versus the first raw baseline on that public subset. This combines image inputs and conservative blending; the public gain does not isolate their individual effects. The development and confirmation results use a different partition from the raw baseline's all-training site CV.

One predeclared Ordered CatBoost follow-up completed in saved version **372977582**, using exactly 90 CatBoost fits in 758.705 seconds. It improved development to 0.931200, winning two folds, but public error rose to 1.16407. No parameter sweep or public-score mixture fitting followed. Both source/configs remain frozen, and private performance is unknown. See [fixed-model research](ONE_MODEL_FOLLOWUP.md) and the measured experiment log. Do not describe this as an independent confirmation or a public improvement.

## Reproduce in Kaggle

Open the [public source-only Kaggle notebook](https://www.kaggle.com/code/saishreeksingh/lavalabs-atmospheric-lab-source-and-evidence?scriptVersionId=372991446), released under Apache 2.0. It contains both exact frozen recipes, their aggregate findings and attribution, with zero output files. Create a private copy and enable only the relevant guarded run to reproduce with the official input. The private scored runs remain private.

1. Join the competition and review its rules using your own account.
2. Create a **private** Python notebook from the competition Code page; attach the official OBSCURA input.
3. Import `LavaLabs_Atmospheric_Experiments.ipynb`. It contains source, synthetic assertions and one run entry point; no competition observations are embedded.
4. Use Save Version / Save & Run All. CPU execution uses two numerical threads; GPU is unnecessary for this recipe. The first measured image run took about ten minutes, including 7.5 minutes of extraction; hardware/startup and future runs may differ.
5. Inspect the strict aggregate JSON receipt and the private CSV under `/kaggle/working/lavalabs_private_experiment/`. Submit `submission_selected.csv` through Kaggle, keeping row-level outputs private.

The raw baseline notebook is a separate frozen control. Its successful saved version is [372915885](https://www.kaggle.com/code/saishreeksingh/lavalabs-atmospheric-lab-baseline?scriptVersionId=372915885); access is currently private. Authorized judges/reproduction reviewers need an accessible source-only reference or approved sharing, not a promise that this private link is public.

## Research paper

The [research paper](../../UI/atmospheric/LavaLabs-Obscura-Research.pdf) reports the actual experiments, target denominators, retained controls, rejected additions, measured runtimes, hashes and limitations. Its three-page, two-column serif layout follows the user's formatting reference; no scientific content from that reference is reused. All 41 original paragraphs, five tables and eleven references were retained and all pages visually checked. See [format verification](FORMAT_VERIFICATION.json). Rebuild with `python build_report.py` (ReportLab and standard Windows Times fonts); content is stored in `paper_content.json`.

## Evaluation and acceptance

MCRMSE is the mean of five RMSEs, each using only that target's observed truth. Every prediction must be finite, including predictions at rows with missing training truth. `sample_id` is used only for joins/export; `site_key` is used only for partitioning. Neither enters predictors.

The fixed confirmation split holds out 20% of training sites with seed 2026. Three outer development site folds evaluate three-inner-fold selection of per-target convex mixtures. The amplitude grid is 0/.25/.5/.75/1 and image weight grid 0/.5/1. Fitted means use only the fitting partition. Feature families share identical splits and fixed estimator parameters. The v2 gate freezes one control and at most one custom challenger using development scores; a custom challenger must beat both controls on confirmation. Otherwise keep the development-chosen eligible control. No public-score weight fitting or confirmation search between custom families.

Final inference refits the retained recipe on all permitted training observations. The exporter preserves 1,221 string IDs and their template order, checks five finite target columns, reopens the CSV, and records its SHA256.

## Verify the software locally

Python 3.11 is sufficient for the synthetic suite; Kaggle used Python 3.13.18, NumPy 2.1.3, pandas 2.3.3 and scikit-learn 1.6.1. `requirements-local-lock.txt` records the separate local test environment, not the hosted runtime. GroupKFold's seeded shuffle requires scikit-learn >=1.6.

For exact scored-v2 reconstruction in this workspace, run `python frozen-v2/build_notebook.py --experiment`. It rebuilds the notebook inside `frozen-v2` using only its six preserved modules, source SHA256 `e878c89e8a00143e35c1f6819f7c926fdf9e7fd90c2cb081d053d5d3407b405c`. The published `research/obscura` package places the same frozen modules and builder at its root; there, `python build_notebook.py --experiment` is equivalent. Do not rebuild scored v2 from top-level development modules, which also contain the separate CatBoost follow-up.

Frozen scored-recipe suite: 26 passed, 17.61 seconds. The later development suite has 30 tests, including synthetic checks for the CatBoost follow-up; those do not establish CatBoost competition accuracy. Run `python -m pytest -q tests` in the relevant package. Checks cover masked denominators, invalid inputs, grouped coverage, CSV round-trips, unsigned-band arithmetic, cloudy/empty chips, synthetic TIFF extraction, cache invalidation/integrity, actual model inference and outer-label leakage. Synthetic fixtures establish engineering behavior, not atmospheric accuracy.

## Restricted data and prior work

Competition inputs, identifiers, feature matrices, fitted model internals and row predictions stay in private Kaggle storage. The public LavaLabs interface may show only permitted aggregate results and clearly synthetic examples. No competition chip is mapped to a real facility; no coordinates, dates or ground scale are recovered. No external satellite, fire, elevation, weather or air-quality observations are joined.

LavaLabs' Scientific Noir identity and earlier SATQuery flood/NDVI/terrain workflows predate this challenge. They are reusable infrastructure and research context, not validation of the five atmospheric targets. NDVI, elevation and slope already occur in the supplied features; their reuse alone is not claimed as novelty.

## Credits and limits

The official 54-feature recipe and fixed HistGradientBoosting settings are adapted from [Zelzy's Apache-2.0 starter](https://www.kaggle.com/code/zelza0/obscura-starter-baseline). NumPy, pandas, scikit-learn, SciPy, Rasterio/GDAL and threadpoolctl support the implementation. See [source/AI disclosure](NOTICE.md), [model research](MODEL_RESEARCH.md) and [code review](CODE_RESEARCH_REVIEW.md).

Targets are standardized indicators, not emission rates or concentrations in physical units. True dates, locations and scaler constants are withheld. Whole-site validation cannot establish future-period performance. Sparse CH4 labels reduce information; no irreducible-noise claim is made. Development family selection and the confirmation gate both create selection optimism. The earlier raw baseline included all training sites, including confirmation sites. The observed public-score degradation is a material generalization limitation. Private ranking, award eligibility and field utility remain unmeasured.
