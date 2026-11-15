# Syapru Besi evidence

Open `/nepal` in the running LavaLabs workspace. The investigation starts on the NASA grid cell matched to Syapru Besi. Select either variable, click a neighboring cell, inspect sensitivity and download the analysis receipt. The event section opens the original saved radar pair and links to the exact saved Flood Lab run in 3D.

## Regional climate

The fixed request spans 27–29° N and 84–86° E. NASA POWER Monthly and Annual API v2.10.0 returned 15 shared MERRA-2 grid centres at 0.5° latitude by 0.625° longitude. Each cell-variable record contains 504 usable monthly values (1984–2025). Two regional responses and a separate point response are preserved in [UI/nepal/data](UI/nepal/data) with source URLs and SHA-256 checksums in `case.json`. The point at 85.335° E, 28.17° N matches all 504 months of both regional series at 85.625° E, 28.0° N. This verifies cell identity within the same product. [NASA POWER monthly documentation](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/)

The two variables use day-weighted annual temperature and annual precipitation totals. The existing trend kernel fits annual OLS with Bartlett HAC errors, finite-sample correction and Student t reference. Lag 3 is primary. Holm corrects the 30 cell-variable comparisons together. Lags 1 and 5 estimate sensitivity and are corrected separately, each over the same population. The slope intervals are marginal. A year requires all 12 months, and the inherited window checks require at least 20 consecutive complete annual values for inference. The legacy six-location screen retains its separate 36-test family.

| At the model cell matched to Syapru | Slope per decade | Marginal 95% slope interval | Primary adjusted p-value |
| --- | ---: | ---: | ---: |
| Air temperature | +0.041 °C | −0.034 to +0.117 °C | 1.0000 |
| Annual precipitation | +177.2 mm | +114.4 to +240.1 mm | 0.0000262 |

The fitted temperature slope at Syapru remains inconclusive and the precipitation slope clears the threshold in this analysis. Descriptive rainfall slopes for the two fixed halves are −28.4 mm/decade in 1984–2004 and +128.7 mm/decade in 2005–2025. Those fits have no separate p-values and do not test a change between periods. This is an exploratory test of one model product at regional scale. Independent climate corroboration, a test of a difference between cells, and attribution of the August 2026 flood are separate tasks. The grid shows signed change at the returned sample locations.

## Seasonality and unusual-year diagnostic

The challenge's Resources tab lists Acker, McMahon, Shen, Hearty and Casey (2009), [Time-Series Analysis of Remotely-Sensed SeaWiFS Chlorophyll in River-Influenced Coastal Regions](https://ntrs.nasa.gov/citations/20090042747), NASA NTRS 20090042747. Its Methods and Figure 15 derive calendar-month climatologies, monthly anomalies and annual mean anomalies; Statistical Methods, Table 6 and Figure 16 compare ordinary and robust linear regression. LavaLabs applies that approach to the retained POWER observations. The paper is a methodological resource; its SeaWiFS observations and Giovanni retrievals are outside this implementation.

For each of 15 cells and both variables, the builder requires 12 valid months in every selected year. It converts rainfall rates to monthly totals using actual calendar lengths, subtracts each calendar month's 1984–2025 mean, and averages the 12 departures each year. Rainfall annual departures are multiplied by 12 to express annual total differences. Temperature uses equal-month departures, so its diagnostic slope can differ slightly from the day-weighted primary series. The UI plots the seasonal cycle or annual departures and ordinary/robust lines; the diagnostic CSV includes all 504 monthly values, climatologies and departures.

The robust fit uses statsmodels RLM with Huber T, tuning 1.345, at most 100 iterations and tolerance 1e-10. This is an explicit adaptation of the paper's MATLAB robust regression. Years with regression weight below 0.5 are listed for inspection; this cutoff is a descriptive UI choice. A failed fit or incomplete series abstains. No extra p-values are introduced and the primary 30-test OLS/HAC/Holm family is unchanged.

At Syapru's matching cell, the rainfall diagnostic gives +177.2210 mm/decade (ordinary) and +177.6186 (Huber). Temperature gives +0.04209 °C/decade (ordinary, equal-month) and +0.04679 (Huber). Both fits retain the same direction for each variable. Agreement assesses sensitivity to this fitting choice within one product; it establishes neither independent corroboration nor flood attribution. The source PDF SHA-256 is `5209cee13b536f0b4df59b6e4fac9f631fafd1458f1e4d936d2cfab5edda0ab3`; source details and adaptation travel in the downloadable JSON receipt.

## Local event

The prior SATQuery run `event-fe47db331390` used Sentinel-1D observations from August 16 and 28, 2026. The Nepal builder verifies the historical artifact checksums and rereads the 10 m raster: 99,858 of 110,998 cells are valid, and 956 are coded new-water candidates (9.56 ha). The prior overlap calculation reports 2 mapped buildings and 185.8 m of road. The saved erosion and dilation audit moves road overlap from 0.0 m to 765.8 m, which shows sensitivity to the candidate boundary. The original run did not assess connectivity. This replay verifies the retained candidate arithmetic. Damage, physical closures, flood accuracy and causal attribution remain unestablished.

The event section uses the original radar previews, with their freeze hashes. The 3D handoff opens the measured source terrain and the existing RGB, candidate overlays and source trace. See the original [case research report](research/results/case-campaign-20261107/REPORT.md) for the wider terrain and optical work. Copernicus Sentinel data and OpenStreetMap assets retain the credits in [DATA_LICENSES.md](DATA_LICENSES.md).

## Reproduce and check

```sh
.venv-linux/bin/python scripts/bootstrap_demo.py --verify
.venv-linux/bin/python -m scripts.build_nepal_case
.venv-linux/bin/python -m pytest -q tests/test_nepal_case.py tests/test_seasonal_check.py
```

The builder uses frozen inputs. It verifies all three NASA source checksums, the grid and same-product point match, and the selected historical event artifacts. The regression checks include an independent numerical implementation of the primary HAC calculation and Holm adjustment, abstention on an incomplete year in the centre of the record, and checks that the published route serves the correct frozen data.

Diagnostic checks remove a known synthetic seasonal cycle, test an injected influential year, independently recalculate annual rainfall departures with leap-year month lengths, and verify all 30 real cell-variable outputs and their downloads.

## Design reference

The supplied [Lifeline project](https://github.com/kinnuworks/lifeline) informed how the investigation presents coverage, validation boundaries, sensitivity and reference evidence. Its [EMSR927 comparison](https://github.com/kinnuworks/lifeline/blob/main/runs/trishuli-2026/validation/emsr927.md) evaluates its own pipeline and has distinct target definitions, areas and data splits. LavaLabs uses its own analysis, coverage and source receipts. Lifeline code, weights, run data, performance numbers and conclusions are outside the implementation. OpenAI Codex assisted the new code, numerical checks and writing. Source data and prior event artifacts retain their provenance.
