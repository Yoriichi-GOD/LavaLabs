# Methane literature and code: extract mechanisms, reject incompatible inputs

23 November 2026. Primary methods, author repositories and actual source files were read. No model/data downloads, installs, training, or public changes. Expected OBSCURA gains are unmeasured. Organizer applicability is recorded in [PUBLIC_DATA_CONTRACT.md](PUBLIC_DATA_CONTRACT.md).

## Varon et al.2021: multi-band/single-pass versus multi-pass

[Paper](https://amt.copernicus.org/articles/14/2771/2021/) sections3.2/3.3 distinguish a one-pass B11/B12 fractional residual from a temporal-reference correction. Methane sensitivity differs across these bands; heterogeneous surfaces can mimic absorption. The single-pass empirical scaling is estimated within the scene, but conversion to column enhancement uses radiative-transfer calculations and viewing/solar geometry. The best temporal method requires a clean reference pass. The original radiative-transfer code is available upon request, not an inspected turnkey package.

**Transferable idea:** fit a within-chip spectral background and preserve its negative residual tail rather than only a global band ratio. **Boundary:** on our L2A chips this is an uncalibrated spectral predictor, not the paper's gas retrieval. Absolute column/flux, reference subtraction and metre-scale plume thresholds are inapplicable. Also distinguish negative gas-absorption residuals from positive thermal excess. No claim that the released CH4 target is recoverable from those residuals.

## CH4Net2024: morphology helps, but task and domain differ

[Paper](https://amt.copernicus.org/articles/17/2583/2024/) methods2.1/2.2 and conclusions describe a U-Net trained with pixel masks from repeated L1C observations of23known semi-arid super-emitter sites. Single-pass inference is possible, but the main future-year test reuses those locations; one unseen regional site does not establish globally unseen-industry transfer. The output is a plume probability mask, explicitly not concentration. Thin clouds and surface heterogeneity cause errors.

[Author repository](https://github.com/anna-allen/CH4Net) is MIT; [models.py](https://github.com/anna-allen/CH4Net/blob/main/src/models.py) contains a configurable U-Net. [loader.py](https://github.com/anna-allen/CH4Net/blob/main/src/loader.py) expects author mask/raw-array paths, balances negative training scenes and selects bands by numeric slicing. README offers a12channelcommand while the paper describes13bands: verify actual channel mapping rather than assume compatibility. Our scalar standardized labels provide no plume masks; importing architecture does not reproduce the study. Reuse only a carefully adapted low-capacity image-regression mechanism if separately justified, not a pretrained methane detector by default.

## Wang et al.2024: matched filter's hidden input requirements

[Paper](https://www.mdpi.com/2072-4292/16/6/1023) methods use scene/background spectral statistics, methane absorption responses and radiative-transfer simulation. Crucially, the implementation's background refinement includes adaptive clustering of a **two-month cloud-free image history** despite the abstract's reference-free framing. It also uses L1C cloud masks and observation geometry. No public implementation link was identified in the article's availability section.

**Useful mechanism:** spectral-background separation and contamination screening. **Decision:** reject direct reproduction within OBSCURA; no same-site archive is available/allowed, and our labels/product are different. A generic covariance anomaly score is not automatically a methane matched filter. [Spectral Python](https://www.spectralpython.net/algorithms.html) supplies detector primitives, but requires a justified target signature/background model; library availability does not create those inputs.

## MARS-S2L2025/2026: strong deployment evidence, incompatible drop-in

[Full paper](https://arxiv.org/html/2511.21777v3) describes a16channel U-Net using current/reference information and a methane retrieval; its segmentation and quantification outputs are different from our standardized window targets. [Official UNEP repository](https://github.com/UNEP-IMEO-MARS/marss2l) documents L1C current-plus-background imagery, cloud masks, MBMP processing and flux computation. The code is LGPL-3.0; models/database have separate non-commercial share-alike terms. Its operational results do not validate an adaptation to anonymous L2A facility chips.

**Decision:** reference for robust false-positive control and genuinely unseen-site evaluation, not a model to install into this entry. Missing background passes/calibration and different targets dominate the fit issue. No outside scenes, trained contexts or weights were acquired.

## New single-scene transformer paper: code availability check

[Wu et al.2026 paper](https://www.sciencedirect.com/science/article/pii/S0924271626004065) indexed methods describe iterative B11/B12 regression, MAD residual screening and a normalized log residual before a transformer. Full publisher access returned403, so this is **indexed-method inspection, not a full-paper review**. Its linked [GFDAFormer repository](https://github.com/creativeXin/GFDAFormer) was verified empty. This cannot be called a usable implementation or a reproduced model. The lightweight background-screening hypothesis is conceptually interesting, but no detailed method or license implementation was adopted from this source.

## Prioritized implication

There is no evidence for adding a large methane model now. If later pursued, one cheap background-residual feature block should be tested with a matched learner, official label masks and site/environment separation. A negative residual over water/heterogeneous surfaces/clouds must be treated as potential artifact. CH4's sparse observations, noisy coarse label and L2A/product mismatch reduce its priority relative to an eligible fire-activity or aerosol feature experiment. This is a task-specific judgment, not a claim that methane prediction is impossible.

No new novelty, physical retrieval, expected accuracy or leaderboard result is claimed by this review.
