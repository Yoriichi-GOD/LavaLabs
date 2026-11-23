# LavaLabs OBSCURA: bounded CPU experiment research

Research date: 23 November 2026. No training, restricted-row inspection, app modification, account mutation or environmental-data acquisition was performed for this note. Dataset/baseline facts below inherit the completed [Kaggle audit](KAGGLE_AUDIT.md); proposed gains remain **hypotheses**, with no accuracy or runtime promise.

## Decision

Run three controlled changes: **cloud handling without a cloudy fallback; a small spatial SWIR feature block; conservative per-target blending/shrinkage selected inside grouped validation**. Keep the official regularized HistGradientBoosting model family. Do not spend today's budget adding a CNN, several libraries, a physical methane retrieval or an unjustified FIRMS hurdle.

The existing baseline already has 29 table inputs and 54 chip summaries, including SWIR tails/thresholds, NDVI spread, SCL fractions and cloud coverage. Repeating those is not a contribution. The relevant research question is whether the three changes add unseen-site predictive value **beyond that baseline**. [Official starter](https://www.kaggle.com/code/zelza0/obscura-starter-baseline?scriptVersionId=359068856)

## What is established, and what is not

- Prior audit: 3,218 rows from 81 train sites, five standardized targets, missing CH4 labels, no test `site_key`, withheld true dates/locations/scales. Approximate observed counts are CH4 1,113, NO2 3,130, CO 3,188, AAI/FIRMS 3,218. These are organizer-reported counts, not a recount by this subtask. [Data](https://www.kaggle.com/competitions/obscura/data), [starter](https://www.kaggle.com/code/zelza0/obscura-starter-baseline)
- GroupKFold separates groups; parameter tuning on the same CV results used for reporting creates optimistic selection. This affects shrinkage weights as well as architectures. The 81 sites, rather than 3,218 rows, are the main independent units for assessing transfer. [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html), [Cawley and Talbot, 2010](https://www.jmlr.org/papers/v11/cawley10a.html)
- Lower predictability of CH4/CO is **not established here**. Fewer CH4 labels imply less fitting/evaluation information, not a measured irreducible-noise estimate; CO has many labels. Test both targets against a fold-fitted mean, examine site variability and shrink if measured evidence favors it.
- No method below can establish future-period transfer: dates are withheld. No feature should use IDs, ordering, file sizes, coordinates, acquisition recovery or outside observations. [Competition Rules](https://www.kaggle.com/competitions/obscura/rules)

## Improvement 1: distinguish missing clear imagery from cloudy observations

**Established:** SCL has separate no-data/defective/shadow/cloud/cirrus/snow classes; class 7 is unclassified/low cloud probability, not guaranteed clear ground. CLD is a percentage. Sentinel-2 reflectance can exceed one. The competition's band map and 10,000 scale remain authoritative for its chips. [Copernicus band and mask documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html)

**Hypothesis:** The baseline's replacement of a clear mask with nonzero pixels when fewer than 500 clear pixels remain can turn cloud contamination into apparently valid reflectance statistics. Preserving missingness may generalize better; discarding useful industrial pixels could also make it worse.

Test this before changing the threshold:

1. **M0:** reproduce the exact official mask and fallback.
2. **M1:** identical mask/500-pixel requirement, but return NaN for clear-dependent summaries when coverage is insufficient. Retain valid count/fraction, `insufficient_clear` and mask-class/cloud summaries. Keep quality statistics available even when reflectance summaries are absent.
3. Only if M1 is viable, one predeclared strict sensitivity: SCL in `{4,5,6}` and cloud probability `<20`, otherwise identical missing handling. This threshold is an engineering hypothesis, not an organizer or ESA recommendation. Do not sweep ten thresholds.

Use native missing handling in HistGradientBoosting; no global target-aware imputation. Ensure numerical division/subtraction first casts unsigned bands to float. Test all-cloud, all-zero, insufficient-clear, saturated-bright and ordinary synthetic chips. For real Kaggle data, record aggregate fractions affected and held-out errors by coverage; keep chips/rows private. Compare M0/M1 on identical sites. If M1 loses, preserve M0 and report the negative result. [Native NaN handling](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)

## Improvement 2: spatial contrast, not more global averages

**Established:** Sentinel-2 B12 overlaps a stronger methane absorption region than B11. Published retrievals exploit band contrast and/or non-plume reference scenes; heterogeneous surfaces and clouds create artifacts. Those studies concern favorable large point sources and do not validate direct methane retrieval from these anonymous chips. [Varon et al., 2021](https://amt.copernicus.org/articles/14/2771/2021/)

**Hypothesis:** A compact relative spatial block captures local industrial/surface structure lost by global chip averages. It may help FIRMS/NO2 or CH4, or simply encode nuisance surface differences. Treat all features as predictors, never measured gas/fire quantities.

Predeclare at most **16 added values**, only from the existing intended pixels and selected clear mask:

- A fixed central half-width/half-height rectangle versus its surrounding ring: median B11, B12 and NDVI centre-minus-ring differences (3). Add centre/ring valid fractions (2). This is relative image position; facility centering is an unverified assumption, and no distance/area in metres is inferred.
- Per clear pixel, normalized SWIR contrast `D=(B12-B11)/(B12+B11+eps)`: 1st/10th/90th/99th percentiles (4). Cast to float, use reflectance-scale `eps=1e-4`, and reject pixels whose denominator is effectively zero. Deduplicate against the official feature list before adding.
- Local continuum residual: `c=median(B12/(B11+eps))` over the same valid pixels; `R=(B12-c*B11)/(abs(c*B11)+eps)`. Summarize R's lower/upper percentiles and centre-minus-ring median (3). This per-chip normalization uses no labels or archive reference and is **not** the published MBMP retrieval.
- Split into a fixed 2x2 grid, compute median D per sufficiently clear cell, then cell-median range and standard deviation (2); add count of valid cells and a missing-block indicator (2).

Use NaN for a region with fewer than a fixed 100 valid pixels; do not relax the mask automatically. The 100/500 thresholds and 16-feature cap are predeclared engineering choices. Cache one content extraction privately in Kaggle, with deterministic feature names/version. No orientation/wind-plume alignment, inferred resolution or geographic reconstruction. If feature computation dominates runtime, abandon the residual block first and keep centre/ring + D. No improvement is proved until grouped validation beats the official summaries.

## Improvement 3: target-wise convex prediction mixtures with honest selection

The baseline already shrinks predictions; the useful change is **where the weights are selected and how conservatively they are constrained**, not renaming shrinkage. Use base table-only prediction B, selected image-enhanced prediction E, and an observed-label mean mu fitted on the current training partition:

`prediction_j = mu_j + a_j * ((1-w_j)*(B_j-mu_j) + w_j*(E_j-mu_j))`

Predeclare `a in {0,.25,.5,.75,1}` and `w in {0,.5,1}`. All weights come solely from inner grouped out-of-fold predictions on observed labels. Ties or changes below the numerical tolerance choose smaller image weight, then smaller amplitude. No target-wise extrapolation above one, fitted intercept, high-order stacker or per-test-row weight fitting. A target may legitimately select a=0. Compare all weights against the unshrunk baseline and fold mean, including CH4/CO. **Do not assume zero is best** merely because the released labels are z-scores; a fold mean is leakage-safe, while zero is a separately reported fixed prior.

Tuning a,w on OOF labels and reporting that same tuned OOF error is selection-biased. Evaluate the entire inner selection procedure on outer unseen sites. The nested-CV principle applies to this small weight grid. [scikit-learn nested-CV example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)

This is a plausible variance-control strategy, not a guaranteed improvement. Under distribution shift, even well-selected local weights may fail; retain table-only and official-baseline exports as fallbacks.

## RMSE, transformations and the FIRMS hurdle trap

The competition averages five target-specific RMSEs on each target's observed rows. Pool squared errors/counts across OOF rows before taking each square root; do not average fold RMSEs or take a square root after pooling different targets. Target-wise blending is separable for this metric when each target is fit independently. Negative standardized values are legitimate. [Official evaluation](https://www.kaggle.com/competitions/obscura/overview#evaluation)

For squared loss, `E[(Y-p)^2|X] = Var(Y|X)+(E[Y|X]-p)^2`, so the conditional mean minimizes it. RMSE gives the same minimizer for a target. Training on `log1p(Y)` or `asinh(Y)` then applying the inverse generally produces `g^-1(E[g(Y)|X])`, which differs from `E[Y|X]`; log back-transformation tends below the mean under skew. A prettified tail can therefore worsen the scored metric. `log1p` also fails for valid standardized Y<=-1; Poisson/Gamma require nonnegative/positive targets. Stay with raw standardized squared-error loss today. A transformed model is only an optional candidate if inverse predictions are evaluated on original-scale nested held-outs; do not copy a generic log-normal variance correction without its assumptions. [Transformation bias and mean versus median](https://otexts.com/fpp3/toolbox.html#bias-adjustments), [HistGB loss constraints](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)

**FIRMS hurdle: defer unless a real no-event atom is demonstrated inside the permitted training environment.** NASA FIRMS detects active fires/thermal anomalies; this does not imply the released standardized aggregate is a zero-inflated count. In particular `t_firms>0` means above the standardization centre, **not** presence of fire. With withheld scaler constants, raw zero may be a negative z-score. A minimum/mode could be rounding or censoring rather than known no-event state. [NASA FIRMS](https://firms2.modaps.eosdis.nasa.gov/), [competition target description](https://www.kaggle.com/competitions/obscura/data)

If the provided specification plus training distribution establishes a common no-event floor c, use `p*c+(1-p)*m_active` where p is no-event probability and m_active is an original-standardized-scale conditional **mean** among active rows. This follows total expectation. Use soft probabilities, not a hard classifier switch; fit both stages only inside grouped training folds and score the resulting continuous prediction with RMSE. No SMOTE, class reweighting or probability calibration without validation: changing event priors changes the mixture mean. Require multiple active sites in every inner fold; otherwise revert to direct regression. This doubles failure modes and is outside the first three experiments.

## Executable experiment protocol and stopping rules

**First prove the baseline.** In the authorized Kaggle environment, check actual package versions, input schema, labels/sites per target, exact mask/band semantics and measured wall time. Rerun constant/fold-mean, table-only, and official combined baseline. Verify masked metric with a synthetic fixture; fold site sets must be disjoint, every row gets finite OOF predictions, and target masks must match the scored denominators. Do not infer full runtime from the official notebook's nine-second log.

**Freeze the search before looking at new outer scores.** Use 3 outer GroupKFold partitions and 3 inner GroupKFold partitions within each outer training set, identical across all feature variants. Record fold configuration privately. Confirm labels and multiple label-bearing sites in every target/fold before fitting. Reduce fold count if infeasible; do not reroll partitions after seeing scores. GroupKFold's shuffle/random_state options require scikit-learn >=1.6; pin the installed behavior. GroupShuffleSplit is a viable fixed whole-site holdout if nested compute is too slow, but its test_size counts groups, not rows. [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html), [GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html)

| Stage | Bounded work | Decision evidence |
| --- | --- | --- |
| 0: first 30–60 min | Schema/synthetic checks, exact baseline reproduction, one feature batch and one target/fold timed | Correct metric/export, measured runtime; revise remaining schedule using these timings |
| 1: ~next 1–2h budget | Cache M0/M1 and at most 16 spatial values in one image pass | Aggregate clear-coverage/missingness checks; no overflow or false finite summaries |
| 2: ~next 2–4h budget | Nested table-only, official combined, M1 combined and one M1+spatial variant; weights selected inner-only | Outer pooled masked MCRMSE, per-target errors/counts, raw versus adjusted scores, foldwise direction |
| 3: final ~1h budget | Freeze selected recipe; grouped OOF on all train for final weights, full refit, inference/export and receipts | Exact test IDs/column order, finite outputs, hashes, accessible reproduction links and measured-result report |

The budgets are planning limits, not benchmarked runtimes. Four variants with 3 outer x 3 inner x 5 targets require 180 inner model fits, plus outer refits. Cache common predictions; prevent thread oversubscription. If projected work exceeds budget, drop the strict-mask sensitivity and spatial residual block, then use a single frozen ~20%-of-sites holdout with 3-fold development tuning. Never quietly relabel reused development scores as untouched validation. Once the holdout has influenced a revision, its new role is development.

Keep model hyperparameters equal to the official regularized recipe for feature ablations; disable random-row early stopping or use a separately grouped inner validation. The installed HistGB API may differ from current docs, so do not rely on new X_val arguments without checking. Never feed outer labels to early stopping. [HistGB early stopping](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)

Report paired baseline-minus-candidate errors on the same outer rows, target-wise counts, site-macro diagnostics in addition to official pooled metric, and all null results. A paired site bootstrap of fixed OOF predictions can describe sensitivity to sampled sites; it is conditional on fitted folds and does not include retraining/selection uncertainty or establish future-time confidence. Use it to detect unstable wins, not manufacture significance. If gains reverse across site partitions/coverage strata, freeze the simpler baseline.

**Definition of Done:** one reproduced baseline; at most three justified changes evaluated; untouched outer comparisons clearly distinguished from tuning; no restricted rows/IDs in public artifacts; selected pipeline produces a verified finite CSV; actual Kaggle score labeled separately; report states failed ideas, dependence on 81 sites, sparse CH4, unknown temporal transfer and private leaderboard uncertainty. A closed, reproducible negative result is preferable to an untested ensemble.
