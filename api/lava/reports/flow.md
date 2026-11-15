# SATQuery drainage direction validation

12 November 2026. This follow-up to the [drainage pilot](../drainage-consistency-20261112/REPORT.md) tests whether modeled flow directions agree across terrain sources and how those sources compare with independently measured local river velocity.

## Results

On the 42 eligible South Saskatchewan survey blocks, filled Copernicus at 30 m placed 13 directions within 45° of measured flow. Filled Copernicus at 90 m and the MERIT-derived hydrography each placed 9 within 45°. MERIT had lower median angular error than the 30 m baseline in 2017, while the 30 m baseline had lower median error in 2015 and 2016. The full-coverage comparison supports retaining the 30 m baseline for this control. All sources showed substantial local angular error. The experiment estimates agreement on one braided river during the surveyed conditions. [Observed-flow release](https://doi.org/10.5285/e4fe2ebe-b207-47d5-8c77-9873afc63da9)

In the existing Nepal, Varanasi and Sangam Vihar windows, the Copernicus 30 m and MERIT-derived directions differed by at least 90° at 8.8%, 35.9% and 44.0% of paired locations, respectively. These measurements establish sensitivity to the choice of modeled source on the frozen sampling geometry. The three windows still have zero eligible independent physical direction labels. [MERIT-derived raster distributor](https://mghydro.com/watersheds/data/)

![Comparison of modeled directions and observed-flow agreement](direction-comparisons.png)

## Regional comparison on fixed samples

| Case | Fixed units | Fixed sample locations | Distinct native MERIT cells sampled | Copernicus 30 m vs MERIT, ≥90° | Copernicus 90 m vs MERIT, ≥90° | Opposite majority orientation, 30 m vs MERIT |
|---|---:|---:|---:|---:|---:|---:|
| Nepal | 68 | 1,690 | 218 | 148/1,688 (8.8%) | 119/1,682 (7.1%) | 1/67 |
| Varanasi | 2,184 | 56,763 | 7,498 | 20,364/56,701 (35.9%) | 17,559/56,486 (31.1%) | 691/2,120 |
| Sangam Vihar | 83 | 968 | 95 | 422/960 (44.0%) | 375/956 (39.2%) | 31/77 |

Natural units were selected from the original 30 m D8 network. Sangam Vihar units were clipped mapped drain geometries. The same 10 m interior locations were used for each source. Repeated samples share native cells. The result describes agreement on these geometries and cannot estimate network recall. Opposite unit orientation requires both sources to have a strict majority of local directions projected onto the unit tangent. Tied or perpendicular projections without a majority remain unknown.

The two Copernicus arms use the same historical DSM, regridded to 30 m and 90 m and conditioned using the pilot's fill rule. MERIT-derived directions remain on the original 3 arc second geographic grid. The evaluator samples the containing cell and transforms its center and downstream endpoint into the projected case CRS. It excludes terminal, ocean and depression codes. Pixel values were never interpolated as bearings. Differences combine source, native resolution, conditioning and domain effects.

The companion accumulation raster stores upstream grid-cell counts. Across unique sampled cells with positive counts, medians were 10 for Nepal, 2 for Varanasi and 1 for Sangam Vihar. Counts reflect the sampled cells rather than the basin as a whole. No physical upstream area was inferred by multiplying counts by a single cell area. The distributor's original MERIT version could not be verified. Elevation, HAND and channel-width bands were unavailable from this distributor. [Distributor raster processing](https://github.com/mheberger/delineator/tree/main/data_mgmt/0_raster) · [Producer specifications](https://global-hydrodynamics.github.io/MERIT_Hydro/)

The water warning uses the unchanged pilot threshold. Among clear units with a comparable majority orientation, the sources disagreed on 1/14 warned and 0/10 unwarned Nepal units, 593/1,883 warned and 85/217 unwarned Varanasi units, and 28/73 warned and 3/4 unwarned Sangam units. The warning showed no enrichment for source disagreement in Varanasi. Sangam had only four unwarned comparable units. These are associations with modeled disagreement. The earlier Sangam administrative proxy likewise showed low selectivity, with 45/48 annotation agreements still triggering the ungated warning.

At 30 m cardinal shifts of the MERIT lookup positions, the share of paired locations with ≥90° disagreement ranged from 7.2–10.8% in Nepal, 35.5–36.7% in Varanasi and 40.1–44.4% in Sangam Vihar. At 90 m shifts the corresponding ranges were 11.3–14.3%, 36.2–38.8% and 38.9–44.5%. These shifts quantify sensitivity under prescribed perturbations. Relative registration error was not measured.

## Comparison with observed river velocity

The NERC Environmental Information Data Centre release provides SonTek M9 acoustic Doppler current profiler (ADCP) measurements corrected for boat motion using RTK positioning. We acquired all 50 published cross-section CSVs for 2015–2017. The verification script matched all 50 hashes to the archive's published file metadata and reconstructed 14,468 rows. The 0.1 m/s speed floor retained 13,829 rows. Grouping by survey year and fixed 180 m grid cells produced 43 candidate blocks. The minimum of five points and directional coherence of 0.75 retained 42 blocks (5, 24 and 13 by year). One block lacked enough eligible points. The reference in each block is its mean eligible depth-averaged horizontal velocity, evaluated at the mean eligible position. [ADCP release](https://doi.org/10.5285/e4fe2ebe-b207-47d5-8c77-9873afc63da9)

| Terrain source and conditioning | Directions available / 42 | Error <90° / available | Error ≤45° / available | Median angular error |
|---|---:|---:|---:|---:|
| Copernicus 30 m, fill | 42/42 | 31/42 | 13/42 | 61.7° |
| Copernicus 30 m, no fill | 17/42 | 10/17 | 6/17 | 67.7° |
| Copernicus 90 m, fill | 42/42 | 27/42 | 9/42 | 76.3° |
| Copernicus 90 m, no fill | 36/42 | 23/36 | 7/36 | 76.3° |
| MERIT-derived, native | 42/42 | 24/42 | 9/42 | 86.8° |

The three sources with 42 directions share identical support in this table. The unfilled arms omit blocks without vectors, so their available-block proportions need to be read with coverage. Sink filling increased 30 m coverage from 17 to 42 blocks. Only 15 blocks were shared by all five arms. This subset excluded all 2015 blocks and most 2016 blocks. Within those 15 blocks, Copernicus 30 m fill returned 9 directions with error below 90° and 6 within 45°. MERIT returned 10 below 90° and 3 within 45°. See the per-year table for the other paired results. [Observed table](verified/observed-by-year.csv)

For the same 15 blocks, zero-heading 30 m shifts gave 7–12 below-90° agreements for Copernicus 30 m fill and 7–11 for MERIT. At 90 m shifts the ranges were 9–14 and 6–11. A ±2° rotation of the reference vectors at the original positions gave 5–6 within-45° agreements for Copernicus and 2–4 for MERIT. Neither perturbation measures the true geolocation or instrument heading error. [Sensitivity table](verified/observed-registration-heading-stress.json)

The analysis used UTM zone 13N, WGS84, because same-study orthomosaic and DSM metadata explicitly specify it. The ADCP description identifies UTM coordinate columns without directly specifying the zone or grid-versus-true-north convention. A geometry-only pass placed all coordinates inside the published envelope and the companion study area. The exact positional residual remains unknown. The dates within a year may be pooled in a block. Blocks share transects and river morphology, and the mean block location can fall between wetted branches. Local measured water motion and coarse terrain routing operate at different spatial scales. No uncertainty interval assuming independent points or basins was computed. [Companion orthomosaics](https://catalogue.ceh.ac.uk/documents/7473d4f9-c9a7-40ad-9f58-e58e25997fc5) · [Companion DSMs](https://catalogue.ceh.ac.uk/documents/13695138-227f-4d85-9049-0a9cba9e1867)

## Verdict on the pilot's open questions

| Question | Verdict |
|---|---|
| Does water continuity identify D8 errors? | The warning detects open-water disagreements. In Varanasi the two direction sources disagreed on 31.5% of warned units and 39.2% of unwarned units. Regional physical error precision and recall still require matched field labels. |
| Does persistent NDVI help direction inference? | Occupancy and continuity on an unoriented corridor are invariant under reversal. These descriptors alone cannot identify downstream direction. NDVI's incremental value as a reliability feature remains untested on an independent matched optical and field reference. |
| Does channel width give a reliable direction? | The width trend changes sign when line order reverses. It needs independently established orientation or a separately validated directional prior. Only 3 Nepal, 46 Varanasi and 0 Sangam units supported width estimates in the pilot. |
| Do known outlets improve direction? | A real outlet comparison is still open. No independently matched local outlet entered either experiment. The Canadian National Hydro Network work unit covers the control envelope and is a candidate source of map annotations. Local linkage, flow-direction field semantics and outlet evidence still need verification. [NHN catalog](https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977) |
| Which terrain errors can be identified? | Source and position sensitivity are now measured in three regional windows. Local angle errors are measured against velocity in the Canadian control. These comparisons cannot distinguish terrain bias from branch choice, conditioning, resolution, temporal mismatch or registration. |
| Does combining evidence make more correct decisions? | The change of source alone did not improve pooled agreement on the 42 complete-support control blocks. No matched optical-plus-outlet fusion arm ran. Its incremental value remains open. |
| Does the method transfer across settings? | The regional cases show distinct disagreement patterns. Sangam's mapped drains are about 1 m wide at the median and fail the terrain scale gate. Transfer to the three study regions requires local independent observations, and the braided river cannot stand in for those environments. |
| When should it abstain? | The measured coverage gaps support retaining explicit unknowns for missing vectors, unresolved drains and insufficient observations. To validate an abstention rule, measure error and coverage together on a separate eligible reference. |
| Does computational stability imply physical reliability? | No. The exact same-input repeats produced identical results, while the best full-coverage arm came within 45° in 13/42 blocks. A repeat verifies reproducibility. |
| What is new here? | The added contribution is the regional source comparison and a reproducible evaluation of local directions against an independent observed-velocity control. The closest prior methods already combine terrain, water mapping and outlet constraints. Unique method novelty and broad superiority remain unestablished. [Prior-work review](../drainage-consistency-20261112/PRIOR_RESEARCH.md) |

The experiments establish that local drainage directions are sensitive to the choice of terrain or hydrography source, and that a reproducible terrain vector can differ substantially from a physical current observation. For a paper, describe the study as a source-sensitivity and conditional field-reference evaluation. Claims about flood exposure, damage, regional routing accuracy or improvement from the full evidence stack still need task-specific observations and matched comparisons.

## Reproduction and integrity

- Measurement source commit `705279c3e9d6bb651d0063bf2bcd4305c4c930b1`. The predictor seal records `840ab73ab29debf97df2fda8376e6b786ccd6f71`, the tested predictor implementation before measurement values were parsed. Protocols were fixed before evaluation. The regional protocol's initial written warning threshold was corrected from 0.5 to the actual frozen pilot threshold of 0.2 before comparison scoring.
- Regional acquisition transferred 16,515,072 bytes of response bodies for six native windows, including direction and accumulation in each case. The Canadian archive was 415,866 bytes. Its native MERIT crop used 3,145,728 bytes of response bodies. A truncated remote Copernicus tile read was recovered by downloading the exact 24,728,621-byte public tile under a cap and cropping it locally. ETags and local hashes are in the receipts.
- Earlier attempts recorded transport timeouts, WSL name resolution and startup failure, and a blocked Windows geospatial library. The authorized Linux restart restored the original scientific runtime. A regional run failed summary serialization and the following run contained an invalid source identifier. Both were retained and excluded. The accepted run corrected these issues with unchanged metrics.
- The verifier reconstructed all 42 eligible blocks from the original CSV files and independently recomputed angles with vector dot and cross products. It recounted regional denominators and source disagreement from saved rows. All nine regional and five observed result files matched their same-input repeats byte for byte. The relevant software regression suite passed 81 tests.
- Full local runs are under `.runtime/drainage-validation/`. Accepted outputs are `merit-comparison-3` and `observed-control-1`. Raw source files remain in `research/datasets/local/drainage-validation-20261112/`. The scripts in `research/experiments/` implement acquisition, coordinate-only parsing, predictor sealing and evaluation. `scripts/verify_drainage_validation.py` and `scripts/plot_drainage_validation.py` regenerate the compact evidence and figure.
- The `day1-final` tag resolves to `f3945347cf0f0a4581aa1480c8fa1501a25da4b4`. This study is on the local research branch. The package contains the derived summaries and receipts. The existing application, previous research measurements and four reserved WorldFloods activations were outside the evaluation.

[Verified results and recount](verified/verification.json) · [Regional summary](verified/regional-summary.json) · [Observed summary](verified/observed-summary.json) · [Evidence manifest](verified/manifest.json) · [Source eligibility and licensing](SOURCE_ELIGIBILITY.md) · [Figure PDF](direction-comparisons.pdf)
