# OBSCURA: fire and flaring physics review

Research date: 2026-11-23. Read-only literature/source inspection; no imagery, weights, installations, training, paid services, or account changes. Expected competition improvement: **unmeasured**.

## Decision

There is a defensible, small experiment here: **sparse, position-independent SWIR anomalies with candidate-relative background and NIR confound checks**. It differs from whole-chip band summaries and center/ring statistics because it first finds spectrally unusual pixels anywhere in the chip and then summarizes their local context and spatial connectivity.

Do not attempt temperature, fire radiative power (FRP), flare gas volume, or methane emission retrieval. The competition images are confirmed **Level-2A surface reflectance**, scaled by 10,000, with unknown ground scale after facility-dependent framing. The target is a standardized FIRMS thermal-intensity statistic over a **fixed 10 km window**, not an annotated fire mask at the image acquisition. Those task facts were checked by the parent agent against the competition README; I did not independently reopen the private competition page.

A blank hotspot map cannot justify setting `t_firms` to an empirical floor: the target can include heat outside the visible chip, acquisition-time differences, or obscured sources. A hot pixel cannot establish that a source is a gas flare rather than another industrial or natural heat source.

## Four primary papers: methods and applicability

### 1. Massimetti et al. (2020): HOTMAP-derived spectral seeds plus cluster refinement

[Volcanic Hot-Spot Detection Using SENTINEL-2: A Comparison with MODIS–MIROVA Thermal Data Series](https://www.mdpi.com/2072-4292/12/5/820), DOI 10.3390/rs12050820. Read Sections 2.3.1–2.3.3 and artifact examples.

The method uses **TOA reflectances** B8A, B11, B12 at native 20 m. Warm seeds require B12/B11 ≥ 1.4, B12/B8A ≥ 1.2, B12 ≥ 0.15; hotter seeds require B11/B8A ≥ 2 and B11,B12 ≥ 0.5. Additional saturation/context tests recover corrupted hot cores. Connected clusters are refined using a reflectance-sum index and their intensity distribution, rather than counting every bright halo pixel. The paper documents cloud/plume halos and diffraction crosses; these can inflate apparent hotspot area. Validation concerns eight volcanoes and comparisons with MODIS–MIROVA, not this prediction task.

**Transfer:** preserve spectral conjunction and cluster/core descriptors as hypotheses. Do not call the TOA thresholds calibrated L2A fire detection, or the reflectance sum a measured temperature. No author GitHub implementation/license was established during this bounded search. ([Method and limitations](https://www.mdpi.com/2072-4292/12/5/820))

### 2. Marchese et al. (2019): two spectral regimes, with a crucial units distinction

[A Multi-Channel Algorithm for Mapping Volcanic Thermal Anomalies by Means of Sentinel-2 MSI and Landsat-8 OLI Data](https://www.mdpi.com/2072-4292/11/23/2876), DOI 10.3390/rs11232876. Read Sections 3, 4.2, and 6.

NHI uses **TOA radiance**, not raw reflectance:

`NHI_SWIR = (L_2.2 − L_1.6)/(L_2.2 + L_1.6)`

`NHI_SWNIR = (L_1.6 − L_0.8)/(L_1.6 + L_0.8)`.

The second contrast retains hotter sources emitting strongly at shorter SWIR wavelengths. The paper converts Sentinel-2 TOA reflectance to radiance using product calibration information. It identifies cloud-edge false alerts, obscured-source omissions, and saturation-related omissions; a radiance prefilter reduces weak-background artifacts. Published evidence concerns volcanic hotspots against independent observations.

**Transfer:** use separate B12-dominant and B11-dominant **surface-reflectance descriptors**, explicitly renamed proxies. Applying NHI zero thresholds to L2A reflectance is not an implementation of this paper: band-dependent irradiance factors and atmospheric processing matter. Native MSI ground sampling must not be assigned to resized competition pixels. ([Equations and error analysis](https://www.mdpi.com/2072-4292/11/23/2876))

### 3. Fisher and Wooster (2018): why excess SWIR is useful, and FRP is unavailable here

[Shortwave IR Adaption of the Mid-Infrared Radiance Method of Fire Radiative Power Retrieval for Assessing Industrial Gas Flaring Output](https://www.mdpi.com/2072-4292/10/2/305), DOI 10.3390/rs10020305. Read Sections 2, 3, and Appendix A1.

The paper approximates band-integrated Planck emission by a fourth-power law over a specified flare-temperature interval. Background-subtracted spectral radiance, pixel area, and a sensor-dependent coefficient provide FRP. Its assumed 1600–2200 K flare regime is not the lower-temperature vegetation-fire regime; SWIR FRP is unsuitable for the latter. Daytime reflected sunlight and saturation complicate retrieval. Its VIIRS comparison reports 0.5 MW bias and 1.6 MW scatter against NightFire for the selected flare population—**not independent OBSCURA accuracy**. Unsaturated channels can support Planck fitting when other bands saturate.

**Transfer:** motivates localized excess features and separate spectral regimes only. Unknown TOA radiance, solar geometry/calibration, ground area, and source mixture reject physical FRP/temperature fitting here. A reflectance ratio fitted to Planck's law would produce an unjustified physical number. No author code/license was verified. ([Derivation and validation](https://www.mdpi.com/2072-4292/10/2/305))

### 4. DAFI v2 (2023): flare identity depends on temporal persistence

[Multi-Temporal Satellite Investigation of Gas Flaring in Iraq and Iran: The DAFI Porting on Collection 2 Landsat 8/9 and Sentinel 2A/B](https://www.mdpi.com/1424-8220/23/12/5734), DOI 10.3390/s23125734. Read Sections 3.1–3.2 and radiative-power formulation.

DAFI processes harmonized Sentinel-2 **L1C radiances**, with cloud-probability <5% selecting clear pixels. It identifies hot NHI signals, including saturation cases, then uses ≥10% temporal occurrence to separate persistent flaring from episodic heat. Radiative power subtracts a monthly clear-background radiance estimate and includes pixel area. The study uses a 70 m hotspot buffer and a 300 m background buffer; it explicitly leaves buffer-size sensitivity for further study. The reported additional mapped sites concern its geographic/time-series study.

**Transfer:** reliability/context features are useful hypotheses; persistence classification, monthly backgrounds, metric buffers, and power retrieval are unavailable. Do not group supplied rows into reconstructed time series, infer dates/locations, or request outside observations. The paper's availability statement points to imagery on Earth Engine; no redistributable author GitHub implementation/license was established. ([Inputs and method](https://www.mdpi.com/1424-8220/23/12/5734))

## GitHub inspection and practical reuse

### Author-maintained, paper-associated Python code

Fusioka et al.'s [transfer-learning-landsat8-sentinel2 repository](https://github.com/Minoro/transfer-learning-landsat8-sentinel2) accompanies their [2024 JSTARS paper](https://doi.org/10.1109/JSTARS.2024.3436811). The repository declares **CC BY 4.0** and links model weights, which were not downloaded. Its README states the full thresholding pipeline expects complete scenes and metadata. Treat this as source reading, not a chip-ready package.

Inspected [`src/active_fire/general.py`](https://github.com/Minoro/transfer-learning-landsat8-sentinel2/blob/main/src/active_fire/general.py): `LiuAFI.transform` forms `(B12−B11)/B8A`, subtracts a 15×15 local mean for seeding, grows a neighborhood, checks spectral curvature, then handles saturated neighbors. `MurphyAFI.transform` uses ratio conjunctions and neighboring candidates. Its default solar-zenith correction needs metadata; `KatoNakamuraAFI.transform` explicitly needs reflectance-to-radiance conversion. The helper misleadingly named `generalized_normalized_difference_index` returns a **ratio**, not normalized difference. These implementations are by Fusioka's team, not verified original-author Liu/Murphy code. No execution validation was performed. ([Source](https://github.com/Minoro/transfer-learning-landsat8-sentinel2/blob/main/src/active_fire/general.py))

The relevant math needs only array operations and optional existing SciPy/OpenCV local filters/connected components. No GPU, external data, or pretrained weights are inherently needed. Runtime on all competition chips is **not measured**; profile a small batch before committing the extraction run.

### Official operational implementation: Data Desk

The maintainers' [burnoff method](https://github.com/data-desk-eco/burnoff/blob/main/METHOD.md) documents L1C SWIR candidate thresholds, touching-pixel groups, peak/core tests, and a useful sunlight veto: peak B8A rise over surrounding background must be <0.1 times its B12 rise. This is an operational heuristic, not a peer-reviewed accuracy guarantee. We read its method file and README; retrieval of `src/s2.c` failed, so this is **not a source-code audit**. No license was established from the inspected root listing; do not vendor its implementation on that basis. Its full extension expects georeferenced imagery and external scene access, which are outside this task. ([Repository](https://github.com/data-desk-eco/burnoff))

The maintainers' [s2e README](https://github.com/data-desk-eco/s2e) states that L1C is preferred because atmospheric correction can clip strong SWIR thermal signals. This is a maintainer-reported processing concern, not proof that the competition arrays suffered a particular clipping failure. It reinforces auditing actual histograms without inventing a radiance correction.

## Two falsifiable insights and one bounded experiment

Everything below is a **proposed OBSCURA experiment**, not a result reported by those papers.

### Insight A: tiny local anomalies can disappear in global summaries

**Paper → inputs:** Massimetti's spectral seeds/clusters plus the inspected local TAI implementation map to available B8A, B11, B12. Hypothesis: sparse contextual thermal-shape descriptors add held-out-site information beyond the existing summaries, even when chip-wide differences do not.

**Fixed extraction proposal:** convert supplied reflectance channels to float before differences. Use B8A—not broad B8—for the primary NIR proxy. Do not clip reflectance to 1 or label DN=10000 as saturation. Define `T=(r12−r11)/max(r8a,0.02)` and `C=r12−2*r11+r8a`; the denominator floor is numerical stabilization, not physics. For valid pixels, subtract the finite-pixel 15×15 mean of `max(T,0)` to obtain local score `D`. No tunable kernel search. From pixels satisfying `C>0` and `D>0`, retain the top 32 by D; preserve an explicit no-candidate state. Published L1C absolute thresholds are excluded from this feature block.

Six features: maximum D; mean of the top 8 D; sum of positive D over the selected set; selected-pixel count; number of 8-connected selected components; largest component's fraction of selected pixels. The constants are fixed engineering choices for a test on L2A arrays, **not calibrated fire thresholds**. Connectivity in pixels is only image-shape information. Use NaN plus the count for unavailable summaries rather than converting missing support into absence of thermal activity.

**Failure test:** if gains disappear under site-held-out evaluation, are driven by one site, or are no better than a matched bright-pixel control with the thermal conjunction removed, reject the claim that this captures useful transferable thermal structure. Jointly shuffling pixel positions across bands preserves spectra but destroys neighborhoods: losing apparent benefit under this shuffle supports spatial contribution; no loss means any benefit is spectral pooling only. Do not market either outcome as physical fire validation.

### Insight B: NIR excess and cloud context can distinguish a useful anomaly from reflected sunlight

**Paper/code → inputs:** burnoff's surrounding-background sunlight test, supported by the papers' reflected-sunlight caveats, maps to local B8A/B11/B12 and supplied SCL/cloud probability. Hypothesis: candidate-relative cross-band excess plus reliability descriptors reduce false fire-like signals.

**Six additional fixed features:** around each selected candidate, use the available 15×15 neighborhood excluding its central 3×3 and selected candidates. Require at least 16 eligible background pixels; otherwise record missing. Let `e_b = r_b(candidate) − median(r_b(background))`. Pool mean positive e12; maximum positive e11; median `e8a/max(e12,0.02)` among e12>0; fraction with `e8a < 0.1*e12` and e12>0; candidate cloudy fraction; valid-background fraction. This adapts an idea; the 0.1 threshold is not asserted to be optimal or calibrated for L2A.

Use the supplied cloud-probability channel after verifying its scale. Keep strict-clear and all-observed diagnostics; do not silently turn cloud masking into a declaration of no fire. SCL saturation/defect values, if present, are flags rather than measured temperatures. Avoid inferring sensor saturation solely from bright or repeated maxima.

**Failure test:** stratify error changes by supplied cloud fraction and compare to adding only cloud/reliability features. If only quality features help, retain the honest quality improvement and drop the thermal interpretation. Report the share of high target values with no candidate; substantial missing support is expected under the 10 km label/chip mismatch and forbids a hard zero/floor prediction rule.

### Evaluation and stop rule

Reuse the incumbent model, fixed site-separated folds, loss, seeds, early-stopping policy, and existing feature set. Compare exactly: M0 incumbent; M1 M0+Insight-A six features; M2 M1+Insight-B six features. Prefer the task's required aggregate metric and also report `t_firms` separately. Keep other targets unchanged initially. Use the same held-out predictions for paired per-site loss changes and a site-level bootstrap; random row splits are insufficient. All feature normalization/model fitting must remain inside training folds.

Before extraction: verify channel order, integer-to-float conversion, denominator guards, finite output, no-candidate cases, and mask scale on a tiny batch. Before modeling: inspect a fixed small set of anomaly overlays selected without targets, including bright cloud/roof examples. Do not use this check to start threshold hunting.

Run one explicit synthetic feature-control pair first. Against uniform background `(B8A,B11,B12)=(0.20,0.15,0.10)`, inject a compact SWIR-dominant patch `(0.21,0.40,0.80)` and a bright reflective control `(0.60,0.70,0.80)`. Both have the same B12 peak; the thermal-shaped toy has positive curvature and small NIR rise, whereas the reflective toy has zero curvature and a large NIR rise. Repeat at the center and two non-central interior positions. The features should distinguish these toy spectra without relying on location. This tests implementation sensitivity to the intended contrast only; the artificial patch is not a physically simulated flame, and the roof toy does not prove discrimination of real roofs.

Accept only a reproducible aggregate improvement with credible site-wise support and no material deterioration of the competition metric. If the interval for paired improvement includes zero, call the result inconclusive; if the ablation loses, reject it. After this one bounded comparison, freeze the result or stop this path. Do not respond to a failed physics proxy by expanding into segmentation training, geolocation recovery, or a physical retrieval that the inputs cannot support.

## Evidence boundaries

- Verified here: the cited paper methods/limitations and the specifically identified public GitHub pages/functions.
- Competition contract: relayed from the parent agent's current README check; no hidden metadata was used.
- Not verified: code execution, feature runtime, hotspot detection accuracy on supplied arrays, OBSCURA metric gains, or a physical connection between any single chip anomaly and the standardized 10 km FIRMS statistic.
- No source files under `sources/` were edited. No datasets or model weights were acquired.
