# Atmospheric Lab scientific/contract review

Reviewed 23 November 2026: `atmospheric_lab/{core,baseline,features,selection,experiment}.py`, all five local test files, BUILD_CONTRACT, INITIAL_RESULTS and MODEL_RESEARCH. This is a review of the v1 source before its image results became final evidence. No application source, browser, account or competition data changed. The parent reports 21 passing tests and successful private baseline replay; these are not independent test executions by this reviewer.

## Actionable findings

### [P1] Confirmation can retain a custom image family that loses to the official image control

`atmospheric_lab/experiment.py:108–116` computes confirmation results for table, official and the development winner, but accepts that winner whenever it beats **table only**. Example: table=1.00, official=0.90, spatial=0.95 retains spatial. This fails the intended question of improvement beyond the official 54 summaries and can retain added complexity after its advantage reverses on the second site partition. The existing fallback exports the official control, so the evidence is available but not used by the gate. BUILD_CONTRACT lines 9/19 and MODEL_RESEARCH's spatial-control requirement are the relevant specification.

**Verified reproduction:** executed the actual `retained=candidate` assignment and following conditional from the parsed v1 source, using only synthetic aggregate scores; it returned spatial/0.95 with official/0.90. No estimator or competition observations were needed.

**Small fix:** freeze a comparator and at most one novel challenger on development sites, then apply the deterministic gate below. Do not replace the rule with choosing the minimum of all confirmation scores: that would turn the small confirmation partition into another model search. Selection/evaluation reuse creates optimism even for a small method search. [scikit-learn nested-CV explanation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)

### [P2] Cache validity omits part of the extraction implementation

`atmospheric_lab/experiment.py:38–44` hashes the features module plus ordered IDs, but `extract_one` is defined in **experiment.py**, outside that hash. Its independently implemented clear-mask/500-pixel branch, three flags, scaling and `_spatial` invocation affect cached values (`experiment.py:23–32`). An extractor-only fix therefore leaves the fingerprint unchanged and silently reuses pre-fix matrices while printing that the cache is verified. The current cache test intentionally changes `extract_one` and expects a hit (`tests/test_extraction.py:21–24`), so it does not detect this provenance failure.

**Small fix:** include the exact `extract_one` source plus features-module source and an explicit extraction-schema version in the key; keep ordered IDs. Assert loaded matrix row counts, finite-or-NaN values, expected column names/counts and matching summary. Include a permitted stable input-release identifier if available. IDs alone do not prove pixel-content identity across replaced inputs; record this caveat rather than claiming a content checksum. Do not use forbidden file sizes/timestamps/geospatial metadata as model features or reconstruction signals.

**Regression:** same inputs and extraction version must hit; changed extractor semantics/source must miss; reordered IDs must miss; malformed matrix shape/Inf must fail or rebuild safely. Keep any synthetic fixtures separate from restricted inputs. Cache validation is the only integrity issue found here; no current result is proved corrupted by it.

## Proposed frozen confirmation rule

Use one numerical tolerance, e.g. `1e-10`, fixed **before inspecting confirmation results**. Lower MCRMSE wins; simpler families win ties. Preserve the v1 receipt and record when this corrected rule was fixed. Its disclosure matters if a v1 result had already been viewed.

1. On development results, select comparator **C** from `{table, official}`; ties choose table.
2. On development results, select at most one novel challenger **N** from `{no_fallback, spatial}`; ties choose no_fallback. N is eligible to challenge only if it strictly beats C by the fixed tolerance. Do not inspect the other novel family's confirmation score to replace N.
3. On confirmation, start with fallback=C. If C=official and official does not beat table by the tolerance, fallback=table. If development chose table, do not promote official because its confirmation score happens to be best.
4. Retain N only if it was development-eligible and beats **both table and official** confirmation MCRMSEs by the tolerance. Otherwise retain fallback.
5. Log C, N, eligibility, each comparison, fallback and rejection/acceptance reason. Report all predefined control scores. Confirmation remains an accept/reject gate; its finally selected score is **not** an untouched estimate of the selected system.

This is a deliberately conservative engineering rule, not a significance test or proof of private-test improvement. It prevents opportunistic selection among novel families on confirmation. No per-target gate, extra tolerance sweep or bootstrap-based acceptance condition should be added after the scores arrive.

**Required gate fixtures:** novel beats table but loses official; official development comparator fails table confirmation; development chose table while official wins confirmation; novel tie; both novel families differ on confirmation (only the frozen challenger can win); no eligible novel challenger. Tests should also show that changing confirmation labels cannot change development C/N/weights or `selection_before_confirmation.json`.

## Checks that appear correct

- **Metric:** `core.metric` masks observed truth per target, refuses any nonfinite prediction, pools row errors before each square root and averages the five RMSEs. It does not average fold RMSEs or misweight targets by their different label counts. This matches the audited [official metric](https://www.kaggle.com/competitions/obscura/overview#evaluation).
- **Site leakage and means:** generated folds are group-disjoint. `raw_oof` fits each target only on its finite training labels and assigns a training-fold mean. `nested_compare` uses inner OOF labels to tune weights, then applies them to outer predictions. Outer labels enter scoring, not fitting or weight selection. The existing outer-label perturbation test directly targets this boundary. GroupKFold is designed for nonoverlapping groups. [GroupKFold API](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)
- **Early stopping and transformations:** fixed `early_stopping=False`; raw standardized squared-error fits; convex mixtures with no extrapolation, fitted test-row weights or invalid FIRMS/log-target conversion. Full-training refit and final full-training OOF weight fitting after recipe selection are legitimate; their tuned inner errors must stay labeled as tuning.
- **Chip math:** reflectance is cast to float before NDVI/BSI subtraction, B11/B12 positions match the audited competition layout, and spatial differences use relative pixel geometry. No coordinates, metadata-derived predictors or physical-distance calculations appear. SCL/cloud concepts match [Copernicus documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html).
- **JSON and public boundary:** score/count values are converted to Python scalars; `_public_summary` excludes row-level predictions; `write_json(...allow_nan=False)` rejects nonstandard NaN/Infinity. No high-confidence JSON serialization defect was found by static review. The full experiment receipt still needs a real successful write/reopen check. Python documents the strict-JSON behavior of `allow_nan=False`. [Python JSON API](https://docs.python.org/3/library/json.html)
- **Reporting caveats:** receipt explicitly states that family selection uses development outer scores, confirmation is a gate, the earlier baseline saw all train sites and true temporal transfer remains untested. Those limitations are accurate and should survive the final report.

## Interpretation boundaries before closing

The implemented spatial block is sixteen **centre/outer means, tail contrasts, local gradients and coverage** values. It differs from MODEL_RESEARCH's proposed normalized-SWIR/residual/2x2 block and uses 20 valid regional pixels rather than that memo's 100. INITIAL_RESULTS line 26 separately records the actual frozen implementation. Report the actual implemented block; do not claim a residual retrieval, strict cloud-probability experiment or median-based spatial experiment ran. The strict-mask function exists but the v1 extractor does not call it.

The no-fallback comparison simultaneously changes fallback behavior and adds three coverage/quality flags. A gain supports that **combined variant**, not isolated causation by removing cloudy pixels. Its inherited official mask still includes classes not guaranteed to be clear ground; do not call it a fully cloud-free surface. No extra ablation is required to close if claims are kept at the variant level.

The accepted baseline public MCRMSE reported by the parent is 1.32129 versus site-CV 0.966382. That gap strengthens the need for conservative conclusions; it does not justify tuning weights to the public leaderboard. Preserve the genuine baseline submission and distinguish public score, development scores, confirmation-gate scores and private-unknown performance.

## Review evidence limits

Code and tests were inspected in full. The actual v1 gate was replayed through its AST with synthetic scalar scores. A broader independent estimator smoke run was attempted but WSL returned `E_ACCESSDENIED`; no full-suite rerun or restricted-data computation is claimed. The two findings are demonstrated source/logic defects, not an assertion that the ongoing Kaggle run failed. Fix these narrowly, run the new regression fixtures, replay the private experiment and verify its complete strict-JSON receipt before declaring the model/report frozen.
