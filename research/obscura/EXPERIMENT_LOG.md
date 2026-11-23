# Atmospheric experiment log

## Run 1: controlled image summaries, 23 November 2026

Private Kaggle draft, source-module hash `2aaa18821d182e1d5835984e5e58081eedcd756b3f92f6656f64877fd8edbc25`. Interactive output completed; not a verified saved replay. All restricted inputs and row outputs remained on Kaggle.

Data: 3,218 training rows, 1,221 test rows, 81 sites, 4,439 chips. Fixed 20% whole-site confirmation split (seed 2026); development comparison uses three seeded outer site folds and three inner site folds. Inner-only convex mixtures with amplitudes 0/.25/.5/.75/1 and image weights 0/.5/1. Fixed shallow HistGradientBoosting settings; no leaderboard tuning.

| Family | Predictors | Development pooled nested MCRMSE |
|---|---:|---:|
| Table | 29 | 0.9375793434856433 |
| Table + official summaries | 83 | 0.9337828782984863 |
| Table + no-fallback/quality variant | 86 | 0.9362702230645311 |
| Table + spatial variant | 102 | 0.9366078818446638 |

Official beat table in all three development folds. Spatial beat official in only the third fold. Development chose official; confirmation table 0.8872517261752882 versus official 0.8620563381127063. The initial selection retained official. These figures are measured aggregate notebook output. There is no image public/private score yet.

Extraction: 449.2 s. Full run: 606.849 s. The no-fallback change includes three additional quality flags, so it cannot identify the causal effect of masking alone. Spatial descriptors use means/gradients and relative pixels; the more elaborate residual/2x2 features proposed in MODEL_RESEARCH were not implemented. No direct gas retrieval was performed.

Two source-review findings were fixed before these image scores were read: novel acceptance must beat the official control as well as table; cache identity must include the extractor and validate its matrices. The corrected gate does not change this run's chosen official family, but needs a fresh private saved replay and full receipt before promotion. Confirmation is an accept/reject partition, not untouched final-test evidence. Earlier raw-baseline inspection included all training sites. Development family-selection scores have selection optimism, and no future-period validation is possible with withheld dates.

## Browser interruption

The Download Notebook action failed to return, stalling browser control for approximately one hour. No downloaded notebook was found in the named local Downloads path. Connection recovered and current outputs were inspected; no duplicate prediction submission was sent. Avoid repeating that download path; use aggregate text receipts and saved version replay.

## Run 2: corrected control gate and reproducibility replay

Source-module SHA256 `e878c89e8a00143e35c1f6819f7c926fdf9e7fd90c2cb081d053d5d3407b405c`. The corrected interactive run reproduced all metric values above: 608.654 s including 446.265 s extraction. Fresh saved Kaggle version **372947210** displayed Successful: pipeline 794.109 s, extraction 608.504 s, viewer 821.9 s including setup. Metric values, final weights and prediction hash matched the interactive run exactly. The selected and official-control CSVs are identical: `007abb84e2f53b01d7ca71929647d83ea6803e2cb186871fd61f3cda38892c20`.

The genuine Kaggle submission used `submission_official_control.csv` from that saved version; it is byte-identical to `submission_selected.csv`. Success/Complete and **public MCRMSE 1.15808** were visibly confirmed. This is 12.35% lower error than the first raw table submission (1.32129), on the public subset only. The gain combines images and blending; it cannot isolate either. No final selection checkbox was set yet. Private score remains unknown.

Observed threshold coverage: 14 / 4,439 chips insufficient (0.3154%). Confirmation target counts: CH4 216, NO2 605, CO 614, AAI/FIRMS 621. Official confirmation RMSEs: CH4 .93573643, NO2 .93361437, CO 1.16290624, AAI .62732598, FIRMS .65069867. All restricted rows and identifiers remain private. Curated aggregate evidence is in `integration/UI/atmospheric/results.json`.

## Current closure state, 23 November (supersedes earlier snapshots)

Fixed Ordered CatBoost completed successfully in saved version **372977582**, using the same 83 inputs, 90 CatBoost fits and 758.705 seconds (442.297 seconds extraction; viewer 784.9 seconds). CatBoost 1.2.10; fixed depth3/400 rounds/.03/L2=10, two CPU threads, no early stopping or parameter sweep. Source SHA256 `2a8e41d2af52ef93dfc54468c48d0e01d3a749ca8176d63d30a236339b173536`. Full aggregate receipt and source are preserved separately in `frozen-catboost/`.

Reused-development nested MCRMSE **0.931199791586064** versus HistGB official **0.9337828782984863**, with 2/3 matched fold wins. Fold scores Cat/HistGB: .8436719303/.8435111601, 1.0232146119/1.0267258816, .8919039937/.8965204214. The fixed development gate passed; the earlier confirmation partition was not rescored. This is iterative development, not independent confirmation.

Full-training Cat export passed the 1,221-row finite/order contract; private CSV SHA256 `be5f8926b4d90991f191d9e223f71b772d5577d830e2a652f16ed0afe4b141e6`. Genuine submission accepted with **public 1.16407**, slightly worse than v2 **1.15808**. Model search stops here; no fourth submission or public-score mixture fitting. Both accepted recipes are visibly selected as the final Kaggle candidates, **2/2**, baseline unchecked. Private results unknown.

Thirty atmospheric tests passed in 20.92 seconds and thirty integrated app/legacy checks passed in 26.93 seconds. Browser checks exercised all five target choices, retained six old studies and proved recoverable missing-receipt behavior. At 390 px there was no DOM horizontal overflow. Independent visual review found no app defect, but one loaded mobile target capture remains incomplete after viewport failures; full visual sign-off is not claimed.

The report now covers both actual runs and the public reversal. The output-free combined source notebook is quick-saved on Kaggle and contains both guarded private-copy recipes. The user approved Apache-2.0 publication, but Kaggle requires account phone verification before making it public. Devpost story, report link and finalization remain release work. No Devpost submission success is claimed.

## Final release verified, 23 November 2026

The user completed Kaggle phone verification and approved Apache-2.0 publication. Public source-only version **372991446** contains both frozen recipes, zero output files, and the verified source-module hashes. Only code and aggregate evidence were released; private scored notebooks and row outputs remain private.

Main implementation commit **05534e4** and Pages commit **ced5762** were pushed to the separate LavaLabs repository. The live atmospheric evidence loaded correctly. Its public research PDF is byte-identical to the three-page, two-column serif report: SHA256 `bad2737b39144e30a888dc2764cb752befa9133b12fd501f9f2fe94fc208fe9c`. All 41 original paragraphs, five tables and eleven references are retained; the supplied reference PDF influenced formatting only. Every paper page was rendered and inspected.

The Devpost story, four technology tags, real interface screenshot/caption, volcano thumbnail, three public reviewer links and final research PDF were saved. The user approved the final Official Rules/Devpost Terms checkbox at action time. **Submit project succeeded; the page visibly changed to Submitted to OBSCURA.** Entry: https://devpost.com/software/lavalabs-atmospheric-lab . No video was required by the actual form/final checklist; the optional field remains blank. Cross-source video wording is inconsistent, so no claim of universal organizer interpretation is made.

Kaggle visibly confirms **2/2** final selections, v2 **1.15808** and fixed CatBoost **1.16407**; baseline unselected. The loaded 390x844 mobile target capture closed the independent UI review: **ship** at the narrow interface scope, no material fixes. The serving/privacy regression passed again after the final PDF update. Existing prior research and untracked files were preserved. Private scores, prize qualification, future-time transfer and field utility remain unknown. Model search is closed.
