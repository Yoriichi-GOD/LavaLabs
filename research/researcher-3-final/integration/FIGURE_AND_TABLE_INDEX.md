# Figure and table index

Figure numbers follow the final manuscript. Publication figures are present as PNG and SVG under ../figures/publication_figures. The first eight figure pairs match the V2 files byte-for-byte. Captions state each comparison and limitation.

| Figure | Data and units | Role in the unified paper |
|---|---|---|
| 1. Evaluation stages | Conceptual observation, relationship and decision framework, derived from V2 methods | Use in introduction if Fig. 9 appears later |
| 2. Pooled spectral review | Frozen four reserve crops, known disagreement recall in percent at 10% and 20% | Main spectral benchmark |
| 3. Per-event spectral review | Four crops, percentage-point NDVI versus margin deltas | Supplement for heterogeneity |
| 4. Ahr fixed screening | SpaceNet endpoints on 199 supported road geometries, 44 positives, road counts | Main or paired with matched-budget table |
| 5. Ahr matched budgets | Equal counts 20/32/39/60, conditional benchmark precision and explicit-positive recall | Optional main results or supplement |
| 6. Fixed-slope terrain ablation | Separate six windows, 1,548,021 pixels, micro IoU and recall | Negative terrain control |
| 7. Ahr spatial overview | Sentinel-2, Copernicus DSM and SpaceNet geometry in EPSG:32632, 200 m bar | Illustration, no observed pathway |
| 8. Niger review disagreements | Retained Sentinel-2 false color and selected 80 × 80 disagreement examples | Illustration selected after score |
| 9. Evidence-state diagram | [Machine-readable protocol](../experiments/evidence_discrimination/PROTOCOL.json) and [policy](../experiments/evidence_discrimination/policy.py), conceptual | Main methodological contribution |
| 10. Ahr alternative witness | [Source geometry and coordinate receipt](../experiments/baseline_comparisons/AHR_CASE_FIGURE_RECEIPT.json), EPSG:32632 metres, one road, 30 m receptor perturbation | Supplement for model sensitivity |
| 11. Matched conditional error | [Matched table](../tables/comparison_results.csv), 42 consumed Canadian ADCP blocks, errors above 45° in percent, exact attainable tie ranges | Main diagnostic or use Table V in its place |

Fig. 11 shows measured angles under discrete matched issue counts. Horizontal point offsets are visual separation. Feasible tie ranges do not measure uncertainty over independent rivers. It covers the requested coverage–correctness comparison, so a second plot of the same data was unnecessary. The Ahr route plot uses the provider coordinates for the retained road geometry and saved model edges. All arrows represent computations.

| Table | Evidence and purpose |
|---|---|
| I | Four event-level spectral counts and recall, V2 event table |
| II | Leave-one-event-out sensitivity by comparison, V2 omission table |
| III | Reference visibility and workload, V2 pooled replay |
| IV | Ahr matched road budgets, V2 retained road metric table |
| V | The final local-angle comparison at five matched counts, with correct retention and possible tie range |
| [comparison_results.csv](../tables/comparison_results.csv) | Native and matched-count direction outcomes including error, coverage, retained agreement and false rejection |
| [claim_coverage.csv](../tables/claim_coverage.csv) | Same Ahr queue under A–F, explicit modeled and physical claim counts, G unavailable for this target |
| [evidence_categories.csv](../tables/evidence_categories.csv) | Descriptive counts for Ahr and Canadian diagnostic strata |
| [original_results_index.csv](../tables/original_results_index.csv) | Exact source paths, commits or release names, checksums and role |

