# Can additional evidence improve flood screening and review?

12 November 2026. Two experiments address the open question from the [drainage validation report](../drainage-validation-20261112/REPORT.md). The first asks whether spectral evidence helps find errors in a water result under a fixed review budget. The second asks whether potential downstream paths improve road screening against high-resolution visual annotations. Both use fixed rules, identical support across methods, and prediction seals before evaluation.

**Results.** NDVI modestly improved the prioritization of water-map errors on the four held-out windows. The prespecified combined NDWI and NDVI rule performed worse than the margin baseline. In the Ahr Valley road comparison, adding terrain paths increased recall over direct overlap. Straight-line proximity was stronger than terrain routing on both the explicit positive comparison and the publisher-convention diagnostic. The full claim of improved exposure accuracy remains open.

![Matched-budget water review and road screening](review-and-exposure.png)

## Experiment 1. Can NDVI or NDWI help verify an existing water result?

The baseline classifies water with MNDWI > 0. Its review list prioritizes cells nearest that threshold. Three alternatives use the same budget and the same water decisions. They move flagged cells up the list, with MNDWI margin breaking ties. The NDVI flag marks predicted water with NDVI > 0.2. The NDWI flag marks a disagreement between the zero-threshold NDWI and MNDWI decisions. The combined flag uses either. These indices share reflectance inputs and serve as spectral consistency checks.

We retained the six previously consumed development windows and ran a first evaluation on all four originally reserved WorldFloodsv2 windows. The held-out windows did not overlap the six development window bounding boxes. The common held-out support contains **966,993 clear and eligible pixels** and **103,633 baseline disagreements** with the curated water labels. The budget is applied separately within each event on that evaluation support. The reference clear mask was used only at evaluation, so this is a review simulation conditional on known and clear support. No analyst corrections or field validation were measured. [WorldFloodsv2 source](https://huggingface.co/datasets/isp-uv-es/WorldFloodsv2)

| Fixed review budget | MNDWI margin | NDVI flag first | NDWI flag first | Either flag first |
|---|---:|---:|---:|---:|
| 10%, 96,697 reviewed | 20,473 (19.76%) | **21,645 (20.89%)** | 15,928 (15.37%) | 15,974 (15.41%) |
| 20%, 193,396 reviewed | 33,886 (32.70%) | **34,376 (33.17%)** | 20,217 (19.51%) | 20,249 (19.54%) |

Counts refer to baseline disagreements captured for review. Percentages divide by the same 103,633 disagreements. NDVI added **1,172** captured disagreements at 10% and **490** at 20%, improving three windows and tying one at both budgets. The gain concentrated on false positives. At 20%, NDVI captured 1,668 additional baseline false positives and 1,178 fewer false negatives. The primary combined rule failed at both budgets. At 20%, its capture was below the random expectation of about 20,726. The combined rule had gained 3,777 captures on the six development windows. Its held-out decline shows why development results alone were insufficient.

| Held-out activation | Optical minus reference time | Baseline errors | NDVI extra captures at 10% | NDVI extra captures at 20% | Combined extra captures at 20% |
|---|---:|---:|---:|---:|---:|
| EMSR422 | +10 min | 2,661 | 0 | 0 | 0 |
| EMSR438 | +5.68 days | 3,579 | +180 | +77 | +84 |
| EMSR466 | +17 min | 92,425 | +759 | +247 | −13,922 |
| EMSR9284 | +1.28 days | 4,968 | +233 | +166 | +201 |

EMSR466 accounts for most baseline errors. Its reference source is also Sentinel-2, so this is agreement with a curated map and has shared sensor lineage. Excluding EMSR466 as a descriptive sensitivity check leaves NDVI gains of 413 and 243 captures at the two budgets. The four windows cannot estimate a population-wide improvement. The reference maps include permanent water, and differences in acquisition time can account for some disagreements. [Date and support audit](verified/verification.json)

As a hard filter, requiring NDVI ≤0.2 increased pooled F1 from 0.8936 to 0.8956 while mean event F1 declined from 0.8600 to 0.8557. It removed 7,900 baseline false positives and 4,585 true positives. Three of four event F1 scores fell. The combined hard filter fell to 0.8023 pooled F1. These results favor evaluating NDVI as a review cue and retaining the underlying prediction. They provide limited support for automatic classification changes.

## Experiment 2. Does terrain improve road exposure screening?

The cohort includes all 122 native SpaceNet 8 Germany annotation tiles tied exclusively to Maxar catalogue image `10500500E6DD3C00`, collected 18 July 2021. The independent post-event Sentinel-2 scene was acquired the same day at 10:36:55 UTC. Maxar's exact time was unavailable. The pre-event scene was selected by declared catalogue rules and acquired 3 July at 10:36:53 UTC. Earth Search reports different processing baselines for the pair. Both were converted using the corresponding explicit reflectance calibration and offset convention. The optical analysis grid is 20 m, with 30 m GLO-30 terrain. These data estimate spatial association at coarser scale than the Maxar reference and have no measured physical registration residual. [SpaceNet 8 paper](https://elib.dlr.de/191307/1/Hansch_SpaceNet_8_-_The_Detection_of_Flooded_Roads_and_Buildings_CVPRW_2022_paper.pdf) · [Source inventory](SOURCE_ELIGIBILITY.md)

The prediction stage used supplied road geometries. The target was visual road coverage by water or rubble as defined by the benchmark. It does not provide surveyed water depth, physical blockage or traffic passability. We retained 525 road geometries of at least 20 m from 572 highway features. Of those, 199 met the shared clear optical and terrain support rule. Of 138 explicitly flood-flagged geometries of sufficient length, **44** met that support rule. The other 94 lacked adequate observations. Reported recalls condition on those 44 eligible explicit positives.

| Screening rule | Explicit positives found | Recall on 44 |
|---|---:|---:|
| Post-event MNDWI overlap | 6 | 13.6% |
| Before/after MNDWI overlap | 6 | 13.6% |
| Change overlap + D8 downstream path within 90 m | 22 | 50.0% |
| Change overlap + straight-line distance within 90 m | **38** | **86.4%** |
| Change overlap + NDVI gate | 6 | 13.6% |
| Change overlap + NDWI gate | 4 | 9.1% |

The path and proximity methods use the same change-candidate seeds on the same terrain grid. Direct overlap means at least 20% of the supported road length intersects the candidate mask. D8 paths are potential drainage routes and terminate at missing observation support. The positive-only comparison establishes that terrain found more flagged roads than overlap alone. Proximity captured 16 more positives than terrain with the same fixed 90 m threshold. An independent outlet was unavailable.

All remaining eligible references had blank flood attributes. The strict explicit-label evaluation therefore has zero known negatives and cannot estimate precision, F1 or AP. A separate diagnostic uses the published convention that treats blank flood attributes as negative. The dataset paper also allows obscured roads to have blank attributes. These scores measure agreement with that coding on 44 positive and 155 conventionally negative roads. [Publisher's reference conversion](https://github.com/SpaceNetChallenge/SpaceNet8/blob/main/baseline/utils/gt_geojson_to_wkt_csv.ipynb)

| Method | TP | FP by convention | FN | F1 by convention | AP by convention |
|---|---:|---:|---:|---:|---:|
| Before/after MNDWI overlap | 6 | 0 | 38 | .240 | .398 |
| D8 downstream path | 22 | 10 | 22 | .579 | .574 |
| Straight-line proximity | 38 | 22 | 6 | **.731** | **.737** |

The D8 rule produced fewer benchmark false alarms and missed more benchmark positives than proximity. The ordering by AP held under all four 30 m cardinal lookup shifts, with 187–193 nominal-cohort roads supported after shifting. Shifting assesses sensitivity and does not estimate actual registration error. In the 39-road review simulation, the index flags and the direct-overlap margin each caught 9 of 38 benchmark disagreements. This road test supplies no evidence of an NDVI or NDWI review gain at the tested budget.

## Paper claims supported by this evidence

- **Supported on the held-out water benchmark.** An NDVI flag found a modest additional share of disagreements at the same review budget. The gain was more pronounced at 10% review and concentrated on false positives.
- **Failed under the prespecified comparison.** Combining NDVI and NDWI disagreement indiscriminately made the review list worse. The gain seen on the development windows did not transfer to the held-out windows.
- **Supported for positive recall on this road cohort.** Terrain routing added 16 explicitly flagged roads over direct overlap. Straight-line proximity added 32. The results favor proximity for recall under these thresholds.
- **Still open.** Overall infrastructure exposure accuracy requires confirmed unexposed segments and comparable acquisition coverage. Improvement beyond proximity, usefulness of independently sourced outlets, and transfer across terrains require separate labeled events and same-support comparisons.

## Verification and reproduction

- The spectral protocol was committed at `adf9d672732a806d75575af1386cbd87f8924598` before first reserve evaluation. A reporting bug treated the tie rule as a scoring method in the development aggregation. Commit `8488510` corrected the aggregation before the reserve evaluation, with the scores and sealed predictions unchanged. All four reserve windows are now consumed.
- The road cohort and scores were committed at `cabc836`. Prediction source `b5c5b1ff76fc2b9021521cd5b974f8e4608f41a8` sealed the predictions before the flood attributes were used. The first strict join stopped when it found no explicit negatives. A separate label audit then specified the publisher-convention diagnostic using the same prediction seal. The initial STAC acquisition stopped on a pagination link. A recorded completeness check confirmed that all 72 matching records were returned and the same declared selection was resumed.
- The independent recount verified all 122 road source hashes, reproduced confusion counts and AP from the rows, and reproduced water review hits from the sealed arrays. The road replay is byte-identical. The spectral replay matches all metric fields. The scientific regression suite passed 86 checks.
- Complete local runs are under `.runtime/exposure-verification/`. The compact package contains protocol-linked seals, acquisition receipts, reported metrics and the independent recount. `scripts/verify_exposure_verification.py` and `scripts/plot_exposure_verification.py` reproduce the package and figure. Raw benchmark files remain local.

[Verified evidence](verified/verification.json) · [Held-out water scores](verified/spectral-reserve.json) · [Road scores and positional stress](verified/ahr-results.json) · [Artifact hashes](verified/manifest.json) · [Figure PDF](review-and-exposure.pdf)
