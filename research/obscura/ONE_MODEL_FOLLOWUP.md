# One fixed follow-up: regularized CatBoost CPU

Research only, 23 November 2026. No package installation, training, account action, dataset access or source change was performed. Current measured results are supplied by the parent: v2 retained the official image family; development MCRMSE 0.9337828783 versus table 0.9375793435, confirmation 0.862056 versus table 0.887252; custom variants were rejected. Only 14/4,439 chips missed the 500-clear-pixel threshold. Raw table public MCRMSE is 1.32129; the image submission's genuine score is pending. This note does not independently validate those runs.

## Why one experiment is justified

Try **one shallow Ordered CatBoost model on exactly the retained 29+54 inputs**. The original CatBoost paper introduces ordered boosting to reduce an internal training prediction shift; its categorical-feature machinery is not a rationale here because all permitted predictors are numerical. Ordered boosting changes the fitting method, while symmetric trees constrain the form of interactions. This provides a distinct, bounded model bias without inventing new observations or expanding image features. [Prokhorenkova et al., NeurIPS 2018](https://proceedings.neurips.cc/paper_files/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html)

The docs say Ordered can help small datasets but costs more computation. That is a motivation to test, not evidence of a gain for these 81 sites. Internal ordering **does not** solve facility leakage, temporal shift or sparse-label uncertainty; whole-site outer/inner splits remain necessary. [Ordered boosting option](https://catboost.ai/docs/en/references/training-parameters/common#boosting_type)

CO/FIRMS weakness leaves room to test an alternative response surface, but neither weak scores nor a different library imply learnable signal. The cloud change affects too few chips to justify another feature campaign now; that count does not itself prove cloud handling irrelevant. Preserve the accepted HistGB control and its measured results even if CatBoost loses.

## Exactly one proposed configuration

All numeric settings below are **predeclared engineering choices**, not an optimized configuration or literature result. Keep the same settings for all five targets and folds.

```python
CatBoostRegressor(
    loss_function='RMSE',
    iterations=400,
    learning_rate=0.03,
    depth=3,
    grow_policy='SymmetricTree',
    boosting_type='Ordered',
    l2_leaf_reg=10.0,
    bootstrap_type='Bernoulli',
    subsample=0.8,
    sampling_frequency='PerTree',
    rsm=0.8,
    random_strength=1.0,
    random_seed=2026,
    nan_mode='Min',
    boost_from_average=True,
    use_best_model=False,
    task_type='CPU',
    thread_count=2,
    verbose=False,
    allow_writing_files=False,
)
```

Depth three permits at most eight leaves per symmetric tree. L2, subsampling and feature subsampling constrain the proposed fit. **Do not port HistGB's `min_samples_leaf=40` into `min_data_in_leaf=40`: CatBoost documents the latter only for Depthwise/Lossguide, not SymmetricTree.** No extra depth, seed, round-count or regularization sweep. [Tree and regularization parameter definitions](https://catboost.ai/docs/en/references/training-parameters/common)

Use no eval_set, early_stopping_rounds or overfitting detector. Otherwise validation labels can silently select iteration count or saved trees. Save/log the resolved parameter dictionary and installed CatBoost version. `allow_writing_files=False` prevents auxiliary training files; write intended private receipts/model files explicitly if needed. [fit API](https://catboost.ai/docs/en/concepts/python-reference_catboostregressor_fit), [output settings](https://catboost.ai/docs/en/references/training-parameters/output)

## Input, target and missing-value contract

- Reuse the **unchanged verified official feature cache**, columns and order. No IDs, site_key, categorical site encodings, reidentification, environmental acquisitions, new feature selection or new image pass.
- One regressor per target, trained only on rows with observed finite labels **inside that training partition**. Reject infinite labels; do not treat them as ordinary missing values. Require at least two label-bearing sites before fitting; fail clearly if the planned folds cannot satisfy this.
- Convert numeric predictor arrays explicitly to float32 or float64, allowing IEEE NaN but rejecting Inf and object/string columns. Keep standardized signed targets and raw RMSE; no FIRMS hurdle, Poisson, log transform or clipping negative predictions.
- Set `nan_mode='Min'` explicitly: native numeric missing handling considers separating NaNs from observed values. Do not replace NaNs with zero or fit an imputer globally. Quantization/borders must be fitted from each fitting partition; do not pre-quantize a joint train/validation/test Pool. [Official missing-value behavior](https://catboost.ai/docs/en/concepts/algorithm-missing-values-processing?lang=en)

No special handling of categorical features is needed. Do not pass site_key as CatBoost group_id: it belongs to the split controller, not the predictor/model feature contract.

## Comparison and conservative inner fitting

Freeze this protocol before new CatBoost scores. Use the same group partitions and target masks for both pipelines. Recompute any comparison not available on those exact partitions; a cached score from different sites is not a paired control.

Within each outer training set, produce three-fold inner OOF predictions for fixed CatBoost on 83 inputs. Reuse matched raw HistGB table and official predictions if their source/config/fold identity is verified. Fit the existing small target-wise convex mixture with **HistGB table as B, CatBoost as E, and inner-fold training means**. The comparator is the already defined HistGB table/official mixture, tuned using the same inner rows. Refit the required base estimators on outer training labels only, apply the selected weights, and compare on outer sites. Report raw CatBoost as well as mixed results so shrinkage cannot hide model weakness.

This adds one estimator family, not a three-way stacking search. Preserve the existing amplitude/image-weight grid and tie policy. No learning thresholds, weights or target switches from public scores. Do not use the prior confirmation scores to choose a new CatBoost configuration.

**The prior confirmation set has already influenced retention. Any later CatBoost evaluation on it is reused development evidence.** Even a newly arranged grouped CV on these 81 sites is part of an iterative development campaign, not new independent confirmation. Inner grouping protects direct fitting/selection boundaries; it does not erase campaign-level selection optimism. [Nested selection/evaluation distinction](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)

Suggested single decision: retain HistGB unless the fixed CatBoost mixed pipeline improves the paired pooled development metric beyond numerical tolerance and the improvement is not confined to one outer fold/site cluster. State that this is a conservative development decision, not statistical significance. Preserve per-target errors/counts and fold directions. If the choice is unstable or the gain disappears, stop and document rejection; do not rescue it with another CatBoost configuration.

## Required failure tests before a full run

1. **Label masks:** missing target rows never reach fit; all held-out/test rows still receive five finite predictions. Infinite target/predictor inputs fail; numeric NaNs are accepted. Include an all-NaN predictor column and mixed missingness in a small synthetic fit.
2. **No direct leakage:** changing an outer fold's labels changes its scores but cannot change that fold's fitted models, predictions or chosen inner weights. Split sites remain disjoint at both levels.
3. **No implicit selection:** resolved parameters show CPU/Ordered/400/depth3 and no early-stop/best-iteration selection; the completed ordinary model has 400 trees. Inspect actual runtime API compatibility before promising this.
4. **Identity and replay:** target/feature order matches the controller; IDs never enter model arrays. Same version/seed/input gives matching predictions within a declared numerical tolerance; a saved/reloaded model reproduces them. Do not claim bit identity across different library versions or platforms.
5. **Degenerate partition:** too few observed labels/sites, an entirely constant feature matrix or unsupported constructor option fails clearly rather than returning fabricated predictions. If a target is constant, a predeclared partition-mean fallback is acceptable, recorded explicitly; no full-data mean may be used inside a fold.
6. **Finish:** final export's 1,221 ordered string IDs and finite columns pass the existing checks; receipt strictly serializes/reopens without arrays, NaN/Inf or private row dumps. Cache/source/version hashes identify the exact tested recipe.

## Hard compute and scope cap

One estimator at a time, two CPU threads. Time the first two representative target/fold fits, including a label-rich target. The full three-outer/three-inner/five-target comparison requires **45 inner +15 outer =60 new CatBoost fits**; if retained, five-fold final OOF plus full refits adds **30**, for **90 maximum**. Existing matched HistGB prediction reuse must not bypass provenance checks.

Allow **at most two hours wall time** for dependency check, failure fixtures, comparison and any final refit. If first-fit timings project the remaining work beyond that cap, or the fixed settings are unsupported, reject/defer the experiment and keep the proven control. Do not shorten rounds, change Ordered to Plain or add GPU as an unlogged second candidate. These are budget limits, not measured runtime estimates.

Closure is one fixed recipe tested and either retained with qualified evidence or rejected with an explicit reason. No DNN, TabPFN, external weights, additional environmental data, account action or submission is authorized by this research note.
