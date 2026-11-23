# LavaLabs

LavaLabs is a Scientific Noir workspace for investigating Earth-system change. Explore long-term NASA POWER temperature and precipitation trends, then compare what shorter satellite observation windows can establish across four flood and drainage case studies.

Start with the [Nepal investigation](http://127.0.0.1:8780/nepal) after launching. Compare 15 NASA model cells across 42 years, then inspect the saved Syapru Besi event in Terrain & Flood. The [Disaster response map](http://127.0.0.1:8780/?view=response&run=event-fe47db331390#terrain) ranks welfare checks, crossing checks, and follow-up areas on radar evidence or matching optical RGB. The [Nepal evidence notes](NEPAL_EVIDENCE.md) record the data, results and replay commands.

| Workspace | What you can do |
| --- | --- |
| Nepal investigation | Compare 15 regional NASA cells, inspect annual change and significance, then check calendar-month seasonality and ordinary versus robust fits. Export monthly departures and a source-linked analysis receipt before reviewing the saved local event. |
| NASA trends | Select a variable, one of six model cells and one of three periods from 1984–2025. Compare slopes per decade, confidence intervals and significance across 36 fixed comparisons. Download CSV, the evidence receipt and original NASA data. |
| Terrain & flood | Inspect 3D terrain and imagery. Pick an area, set the date, and analyze it with provider access. Review completed observations, ranked response checks, reports and Flood Lab evidence in the same workspace. |
| Case studies | Compare Syapru Besi, Kedarnath, Varanasi and Sangam Vihar in 3D or on a 2D map. Select elevation, slope, height above drainage (HAND), or before/after/changed NDVI. Inspect dates, source sampling and valid coverage. |
| Research evidence | Inspect six preserved studies, including failed quality gates, drainage and observed-flow controls, and the Ahr road review. |

## OBSCURA Atmospheric Lab

LavaLabs now includes a separate atmospheric research contribution for OBSCURA: five standardized atmospheric/thermal targets, missing-label masks, whole-site validation, conservative prediction mixtures and a verified 1,221-row export. Open [Research evidence](http://127.0.0.1:8780/#evidence) for the aggregate comparison and per-target confirmation results. Competition rows, identifiers, imagery and predictions remain private on Kaggle.

The measured development comparison retained the official image summaries and rejected our added cloud/spatial complexity. Confirmation MCRMSE was 0.862056 versus 0.887252 for the table mixture; this partition is an acceptance gate, not untouched final-test evidence. The retained image/blending candidate scored 1.15808 publicly, versus 1.32129 for the first raw table baseline (12.35% lower public-subset error). Site-CV and public scores still differ, so transfer remains a material limitation. See the [Obscura method and replay guide](research/obscura/README.md) and [research report](UI/atmospheric/LavaLabs-Obscura-Research.pdf). This work does not claim that the existing flood cases validate atmospheric predictions.

[Source-only Kaggle notebook](https://www.kaggle.com/code/saishreeksingh/lavalabs-atmospheric-lab-source-and-evidence?scriptVersionId=372991446) contains both frozen recipes with no row outputs. A later fixed Ordered CatBoost improved reused-development MCRMSE to 0.931200 but scored 1.16407 publicly; both accepted candidates are selected for final evaluation, and model search is closed. The report uses the requested two-column serif format.

## Run locally

Use Python 3.11 on Linux or WSL. The checkout bundles the frozen demonstration and needs about 550 MB of free space for the first restore, plus the Python environment. The saved workflows work offline after installation.

```sh
git clone https://github.com/Yoriichi-GOD/LavaLabs.git
cd LavaLabs
python3.11 -m venv .venv-linux
.venv-linux/bin/python -m pip install -r requirements-lock.txt
.venv-linux/bin/python start.py
```

Open [LavaLabs](http://127.0.0.1:8780/#terrain). Terrain & Flood contains the full processor and response workflow. Case Studies, Research Evidence, Nepal Investigation and NASA Trends have their own views. `start.py` starts one service on port 8780. Set `LAVALABS_PORT` to change the port for the whole app. On Windows with the scratch copy, run `start.ps1` from PowerShell to use its existing environment. Launch with `LAVALABS_LOCAL_ARCHIVE=1` to browse the additional saved runs in that local copy. The public repository ships two Nepal runs. New area/date acquisition requires its own provider credentials and network access. See the [Flood Lab access notes](components/floodlab/docs/data-access.md).

Run `.venv-linux/bin/python scripts/bootstrap_demo.py --verify` to check every archived member against the bundle manifest. The original two run freezes, 90 m terrain scene and full 30 m Nepal research graph keep their source hashes. The separate four-case display manifest verifies the accessible display grids. The [public file inventory](provenance/public-files.json) records the exported subset.

## Public demo

[Open LavaLabs on GitHub Pages](https://yoriichi-god.github.io/LavaLabs/). The site includes the two saved Nepal runs, their response maps and optical overlays, 3D terrain, the four measured case views, research reports, and NASA trends with downloads. The browser reads the generated files directly. Fresh satellite acquisition, server-side questions and new terrain cross-sections are available in the local Python app.

Build the Pages package from a clean checkout with the pinned Python dependencies installed:

```sh
python -m scripts.export_public_site --base /LavaLabs --output ./public-site
```

The exporter verifies the repository's demo archive before writing the package. GitHub Pages serves the root of the `gh-pages` branch. For a static host that serves at its domain root, use `--base ""`.

## NASA Space Apps contribution

LavaLabs answers **Be An Earth System Trend Detective!** with an inspectable path from variable selection to direction, location, magnitude and significance. The NASA trend workflow uses 6,048 monthly T2M and PRECTOTCORR values from six predetermined MERRA-2 model cells. It aggregates annual temperature by days and converts precipitation rate to monthly totals with calendar month lengths. It reports OLS slopes with HAC lag-3 uncertainty and Holm-adjusted p-values across 36 tests. The intervals describe individual slopes. The analysis is exploratory and applies to the selected model cells and fixed time windows. [Challenge brief](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) · [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) · [Trend method and tests](trend_lab/README.md)

The NASA workflow and this independent integration are the Space Apps contribution. The Flood Lab engine, Nepal 3D investigation and earlier case, terrain, NDVI, drainage and evaluation results come from SATQuery. The new case viewer exposes their measured layers, quality masks and source provenance. Two-date NDVI differences show the available optical observations. Their projection onto terrain is for inspection. Physical registration, surveyed drainage connectivity and independent flood exposure accuracy remain unresolved. See [scope and verification](VERIFICATION.md).

### A challenge-listed NASA method, applied

The Nepal investigation implements a diagnostic adapted from Acker et al. (2009), [Time-Series Analysis of Remotely-Sensed SeaWiFS Chlorophyll in River-Influenced Coastal Regions](https://ntrs.nasa.gov/citations/20090042747), a NASA resource listed for this challenge. For every selected cell and variable, it computes the 1984–2025 calendar-month climatology, 504 monthly departures, and 42 annual departures. Users can switch between the seasonal cycle and annual departures, compare ordinary and Huber robust trend lines, and download the monthly diagnostic CSV. The JSON receipt identifies the paper, PDF hash, adaptation and regression settings.

At the model cell matched to Syapru Besi, rainfall slopes are +177.2 mm/decade with ordinary regression and +177.6 with the robust diagnostic. This comparison checks sensitivity to unusual years within the same product. The primary annual OLS/HAC/Holm significance result remains separate. Temperature departures use equal-month means, while the primary annual temperature uses day weights. SeaWiFS observations and Giovanni retrievals are outside this implementation. Rebuild with `python -m scripts.build_nepal_case`; see [method and replay evidence](NEPAL_EVIDENCE.md).

## Credits and SI disclosure

OpenAI Codex assisted code, calculation implementation, tests, interface work and documentation. The team supplied the volcano wordmark. The header displays an SI-generated indicator. The Codex-authored fallback mark also carries an SI label. Existing Scientific Noir and Flood Lab decorative art came from the SATQuery project. Its generation method is unconfirmed. Scientific source observations retain their original credits and hashes. The Q&A on the NASA trends page uses fixed matching. The Nepal workflows use bounded, source-linked analysis. [Data sources and terms](DATA_LICENSES.md) · [Code license](LICENSE) · [Logo placement](UI/assets/README.md)
