# LavaLabs: papers → mechanisms → a constrained experiment

Research completed23November2026. This pack answers the request to investigate the atmospheric task through primary papers, actual public implementations and library documentation. **No new model was trained; no gain or winning recipe is claimed.** This is local research, not an update to the submitted paper or public project. Existing selected submissions remain protected.

## Main finding

The most actionable missing representation is **sparse, co-located spectral structure with a local background**, rather than another replacement tabular learner. Our retained54summaries include maxima and pixelwise-ratio percentiles, so claiming that they contain no anomaly information would be wrong. However, separate band extrema discard co-location, rare events can fall below a percentile cutoff, and the failed16feature block summarized whole-center/ring means and gradients rather than candidate-relative structures anywhere in a chip. This supports a discriminating feature test; it does not establish an accuracy gain.

The literature also corrected a crucial applicability assumption: the organizer supplies **L2A surface reflectance**, unknown physical image extent, and **10kmwindow labels**. TOA/radiance retrievals, native20mthresholds and same-site reference histories cannot simply be imported. The specific public source check is in [PUBLIC_DATA_CONTRACT.md](PUBLIC_DATA_CONTRACT.md).

## Prioritized reading map

| Primary study | Mechanism to examine | Applicability decision |
|---|---|---|
| [Massimetti2020: Sentinel-2 volcanic hotspots](https://www.mdpi.com/2072-4292/12/5/820) | Joint SWIR/NIR seeds, connected clusters, artifact refinement | Adapt the spectral/context idea; published TOA thresholds and native-size assumptions are not calibrated for these L2A chips |
| [Marchese2019: normalized hotspot indices](https://www.mdpi.com/2072-4292/11/23/2876) | Separate spectral regimes help retain different heat signatures | Its equations use radiance. Independently named reflectance proxies need testing; do not call them the paper's retrieval |
| [Fisher & Wooster2018: industrial flaring SWIR](https://www.mdpi.com/2072-4292/10/2/305) | Background subtraction distinguishes thermal excess from reflected signal | Motivates excess descriptors; physical FRP/temperature requires absent calibration, area and source assumptions |
| [Mommert2020: industrial smoke characterization](https://arxiv.org/abs/2011.11344) | Spatial plume information in12-band L2A images; location-separated evaluation | Supports a small image-regression hypothesis; their smoke masks/classes are not our chemical/index labels |
| [AQNet2023: multimodal air-quality prediction](https://orca.cardiff.ac.uk/id/eprint/159613/1/1-s2.0-S0034425723001608-main.pdf) | Compact image/tabular fusion and target-specific comparisons | Architecture precedent only: actual S5P gas maps and station attributes are missing here |
| [Varon2021: multispectral methane](https://amt.copernicus.org/articles/14/2771/2021/) | Methane absorption residuals differ from hot positive SWIR anomalies | Background-residual hypothesis only; gas quantification/reference-based methods require absent inputs |
| [CH4Net2024](https://amt.copernicus.org/articles/17/2583/2024/) | Spatial plume morphology and single-pass inference | L1C pixel-mask training and mainly known-site time tests do not establish this task's transfer; not a drop-in regressor |
| [Pollution tracker2023](https://www.cambridge.org/core/journals/environmental-data-science/article/pollution-tracker-finding-industrial-sources-of-aerosol-emission-in-satellite-imagery/22F4760D7DF02B9243F0476371E31D4F) | Facility appearance plus deployment robustness failure | Useful framing/cloud stress lesson, not pollution-regression accuracy |
| [DAFIv2 2023](https://www.mdpi.com/1424-8220/23/12/5734) | Temporal persistence separates flaring from episodic activity | Persistence/history and physical buffers unavailable; do not reconstruct them |
| [MARS-S2L2025/2026](https://arxiv.org/html/2511.21777v3) | Current/reference comparison and stronger unseen-site testing | Different products/outputs and missing background imagery rule out direct pipeline use |

Method sections and code were reviewed for the selected routes, not every cited paper read cover to cover. Final Global-NO2 full text was restricted; its accessible predecessor and final author code were inspected. A new2026transformer paper had403fulltext access and an empty GitHub repository; those facts remain explicit in the methane note rather than being promoted into a usable method.

## GitHub and library findings

| Source | Verified useful material | Reuse boundary |
|---|---|---|
| [Minoro active-fire code](https://github.com/Minoro/transfer-learning-landsat8-sentinel2/blob/main/src/active_fire/general.py) | Pixelwise thermal indices,15x15context, spectral tests | Repo declaresCCBY4.0; audit units/metadata defaults. No weights needed. This is a later implementation of several algorithms, not every original author's code |
| [IndustrialSmokePlumeDetection](https://github.com/HSG-AIML/IndustrialSmokePlumeDetection) | L2A model/data code | GPL-3.0; released default pretrained backbone differs from paper's scratch claim. Do not import unreviewed defaults |
| [sentinel_industry](https://github.com/ManshaP/sentinel_industry) | Scratch optical source-context model and deployment code | MIT; training/deployment scripts, not a ready regression library |
| [AQNet](https://github.com/CoDIS-Lab/AQNet) and [Global-NO2](https://github.com/HSG-AIML/Global-NO2-Estimation) | Fusion architecture and input/split handling | No verified repository license; actual code needs unavailable S5P or source-specific settings. Read mechanisms, independently implement any accepted idea |
| [CH4Net](https://github.com/anna-allen/CH4Net) | U-Net and raw/mask loader | MIT; no compatible OBSCURA scalar-label training route verified |
| [Data Desk burnoff method](https://github.com/data-desk-eco/burnoff/blob/main/METHOD.md) | Operational local-NIR/SWIR reflected-light test | L1C application; code license unestablished. Cite facts, do not vendor implementation |
| [SciPy ndimage.label](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.label.html), [maximum_filter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.maximum_filter.html) | CPU-connected components and local extrema | Enough machinery for the proposed feature test; explicitly choose8connectivity rather than assume the4connected default |
| NumPy + existing sklearn HistGB | Float band math, masked local statistics, matched regularized learner | Existing stack; no new hosted inference, large checkpoint or external observations required |

This is source/API inspection, not execution verification of third-party packages. Licenses are artifact-specific; data/weights do not inherit a code license automatically.

## New testable insight

**Spatial pooling can erase the evidence that distinguishes a thermal-shaped anomaly from reflected brightness.** A useful feature should identify where B12/B11/B8A depart together from their immediate surroundings, preserve the strongest sparse components, and retain cloud/background reliability. It should work at different image positions and keep the global context available. The physical papers and operational implementations motivate this; accuracy on the supplied L2A arrays is unmeasured.

This is more specific than 'use another model' and differs from the existing center/ring block. It remains an adaptation of established ideas. Originality would have to come from a clearly specified, honestly evaluated adaptation; citing physics is not itself a novelty claim.

## One bounded experiment recommendation

1. Finish private target/site/tail error accounting using already saved predictions. Do not infer per-target public errors from the single leaderboard score.
2. Verify actual pixel ranges, band order, quality-mask support and whether candidate signals survive the supplied L2A processing on a small private batch. Stop if the proposed signal is unavailable; do not fabricate a TOA correction.
3. Freeze the compact sparse-context feature block described in [FIRE_PHYSICS_REVIEW.md](FIRE_PHYSICS_REVIEW.md), plus a brightness-only and quality-only control. The local numerical constants are engineering choices, not calibrated fire thresholds. No kernel/threshold search.
4. Verify synthetic equal-B12 thermal-shaped versus reflected-brightness controls at center/off-center positions. This establishes code sensitivity only, not real-fire detection. Preserve no-data/missing-support states.
5. Keep the existing learner, other four predictions and official metric fixed. Compare added fire features on the same nested site partitions and one label-free environmental stress partition. Never use a missing chip hotspot to force the10kmFIRMS target to its floor. Preserve the old .005pooled-gain,>=2/3fold-win and per-target-regression gates, require no pooled stress-set regression, and report site-bootstrap uncertainty. A FIRMS-only RMSE gain .025 corresponds to MCRMSE gain .005 if all other predictions stay fixed.
6. Only a passing, replayed, independently audited candidate gets a genuine scored export and matching source/report updates. A negative result closes this feature branch. It does not trigger an automatic larger CNN or threshold sweep.

Reserve, do not launch: [FUSION_GENERALIZATION_REVIEW.md](FUSION_GENERALIZATION_REVIEW.md) specifies a tiny official-input-trained AAI spatial model with a scrambled-image control. This is a separate possible investigation if still justified, not an extra promised experiment or a giant pretrained fallback.

## Research completion checks

- Organizer product level, band contract, target footprint and prohibited-data boundary rechecked live.
- Primary paper mechanisms distinguished from incompatible inputs and author performance claims.
- Actual GitHub files/defaults and licenses inspected where available; restricted/empty/missing sources recorded.
- Existing features compared with proposed mechanism; no duplicated global-summary claim.
- Concrete falsification controls and unchanged promotion/replay rules recorded.
- No model run, new score, physics retrieval, operational validation or win claimed.

Detailed notes: [fire](FIRE_PHYSICS_REVIEW.md), [fusion/generalization](FUSION_GENERALIZATION_REVIEW.md), [methane](METHANE_METHOD_REVIEW.md), [data contract](PUBLIC_DATA_CONTRACT.md). The user does not need to supply the literature or invent another domain insight for this work to continue.
