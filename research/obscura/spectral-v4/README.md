# LavaLabs sparse spectral follow-up

Latest controlled result: **0.91950 development MCRMSE**, versus **0.93378** for the exact frozen control. FIRMS RMSE improves by **0.07142**; four gas/aerosol predictions are byte-identical. Public result: **1.13057**. Private performance is unknown.

The full 99-feature branch combines the official 29 table fields and 54 image summaries with four support and twelve sparse spectral/context descriptors. It uses B8A/B11/B12 reflectance shape, local background, candidate connectivity and coverage. These are engineering descriptors motivated by the cited SWIR literature, not a calibrated physical fire/temperature/FRP/emissions retrieval. No outside observations, recovered location/date or pretrained weights are used.

| Matched development method | MCRMSE |
|---|---:|
| Frozen table/image control | 0.9337828783 |
| Global quality only | 0.9337952465 |
| Local brightness control | 0.9306248678 |
| First six spectral descriptors | 0.9227634422 |
| Full twelve spectral descriptors | **0.9194996153** |
| Jointly shuffled spectral descriptors | 0.9198552401 |

The full branch is the sole predeclared candidate. It wins 2/3 original outer folds and improves two pooled environmental holdouts from 0.9662826536 to 0.9462006522. The fixed-OOF paired-site bootstrap 95 percentile gain interval is [0.00228788, 0.02501520]. All development is reused; this interval omits retraining and selection uncertainty. The shuffled control is almost as strong, so spatial structure alone is not a supported causal claim.

Nine feature/controller tests and two refit safety tests passed. A separate saved-array audit checked exact truth/site identity, every target denominator/RMSE and protected targets. Full fitting reproduced the original complete CSV hash before replacing only FIRMS. Final FIRMS uses 0.75 of the fitted 99-feature branch plus 0.25 of its training mean; weights are selected by five-fold whole-site OOF on all training rows. First four outputs use the original frozen mixtures. No public score fits a parameter or ensemble.

## Reproduce and inspect

Use the [public guarded Kaggle source](https://www.kaggle.com/code/saishreeksingh/lavalabs-atmospheric-lab-source-and-evidence). Make a private copy, attach only the official OBSCURA data and enable only the spectral run flag. CPU two threads; no GPU or newly downloaded model is needed. All chip arrays, IDs, derived features, OOF values and CSVs stay private on Kaggle. The public notebook contains source and aggregates only.

The private fresh replay is version 373122625. It succeeded in 767.2 seconds and reproduced every expected metric and the exact CSV hash before the single genuine scoring submission. Public source version 373134416 is Public, Apache-2.0, with zero output files. Final selections are spectral 1.13057 and original HistGB 1.15808; CatBoost is unselected. Rank was 50 at the post-submission snapshot; ranking can change. Interactive extraction took 572.7 seconds; grouped extraction/comparison 690.53 seconds; full refit 28.36 seconds. Timing is hardware dependent. Quick Save archival runtime is not training runtime.

Candidate private CSV SHA-256: `ae6287bd5aee9269d6d5eb6ffe8e77f7b60db3714c7b275e59154474a2a2055a`.

Five sites contribute 52.5% of control FIRMS squared error. Above the development 90th-percentile target, RMSE changes from 2.63674 to 2.47266 (260 observations); the other 2,337 change from 0.71317 to 0.66111. These descriptive strata have different denominators and are not independent tests.

## Research and attribution

- Massimetti et al. (2020): https://www.mdpi.com/2072-4292/12/5/820
- Fisher and Wooster (2018): https://www.mdpi.com/2072-4292/10/2/305
- Marchese et al. (2019): https://www.mdpi.com/2072-4292/11/23/2876
- Official starter, Apache-2.0: https://www.kaggle.com/code/zelza0/obscura-starter-baseline

The optical inputs are L2A reflectance and chip physical area is unknown. Literature radiance thresholds/FRP retrievals are not directly claimed to apply. No third-party fire code is vendored. OpenAI Codex assisted implementation, tests, research, analysis and writing; organizer observations are unchanged.

Previous cloud/spatial, foundation-model, deeper-tree and CatBoost results remain recorded. This update supersedes earlier statements that all custom features failed; the earlier global feature variants did fail. Earlier flood/NDVI/terrain cases are preserved separately and do not validate the atmospheric model.
