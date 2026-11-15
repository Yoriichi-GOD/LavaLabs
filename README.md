# LavaLabs

LavaLabs is a Scientific Noir workspace for investigating Earth-system change. Explore long-term NASA POWER temperature and precipitation trends, then compare what shorter satellite observation windows can establish across four flood and drainage case studies.

Start with the [Nepal investigation](http://127.0.0.1:8780/nepal) after launching. Compare 15 NASA model cells across 42 years, then inspect the saved Syapru Besi event and follow the evidence into the 3D workspace. The [Disaster response map](http://127.0.0.1:8780/processor/response?run=event-fe47db331390) ranks welfare checks, road and bridge checks, and follow-up areas. The [Nepal evidence notes](NEPAL_EVIDENCE.md) record the data, results and replay commands.

| Workspace | What you can do |
| --- | --- |
| NASA trends | Select a variable, one of six model cells and one of three periods from 1984–2025. Compare slopes per decade, confidence intervals and significance across 36 fixed comparisons. Download CSV, the evidence receipt and original NASA data. |
| Terrain & flood | Rotate the Syapru Besi terrain, choose a cross-section, compare SAR and retained optical RGB, toggle overlays and trace questions to saved evidence. |
| Case studies | Compare Syapru Besi, Kedarnath, Varanasi and Sangam Vihar in 3D or on a 2D map. Select elevation, slope, height above drainage (HAND), or before/after/changed NDVI. Inspect dates, source sampling and valid coverage. |
| Research evidence | Inspect six preserved studies, including failed quality gates, drainage and observed-flow controls, and the Ahr road review. |
| Flood processor | Open the full Flood Lab workspace, saved runs, reports and evidence-backed Q&A. The original area/date pipeline is available with provider access. |

## Run locally

Use Python 3.11 on Linux or WSL. The checkout bundles the frozen demonstration and needs about 550 MB of free space for the first restore, plus the Python environment. The saved workflows work offline after installation.

```sh
git clone https://github.com/Yoriichi-GOD/LavaLabs.git
cd LavaLabs
python3.11 -m venv .venv-linux
.venv-linux/bin/python -m pip install -r requirements-lock.txt
.venv-linux/bin/python start.py
```

Open [LavaLabs](http://127.0.0.1:8780/#terrain). The same workspace navigation reaches terrain, case studies, research, Nepal investigation, NASA trends, and the Flood Lab processor. `start.py` starts one service on port 8780. Set `LAVALABS_PORT` to change the port for the whole app. On Windows with the scratch copy, run `start.ps1` from PowerShell to use its existing environment. Launch with `LAVALABS_LOCAL_ARCHIVE=1` to browse the additional saved runs in that local copy. The public repository ships two Nepal runs. New area/date acquisition requires its own provider credentials and network access. See the [Flood Lab access notes](components/floodlab/docs/data-access.md).

Run `.venv-linux/bin/python scripts/bootstrap_demo.py --verify` to check every archived member against the bundle manifest. The original two run freezes, 90 m terrain scene and full 30 m Nepal research graph keep their source hashes. The separate four-case display manifest verifies the accessible display grids. The [public file inventory](provenance/public-files.json) records the exported subset.

## NASA Space Apps contribution

LavaLabs answers **Be An Earth System Trend Detective!** with an inspectable path from variable selection to direction, location, magnitude and significance. The NASA trend workflow uses 6,048 monthly T2M and PRECTOTCORR values from six predetermined MERRA-2 model cells. It aggregates annual temperature by days and converts precipitation rate to monthly totals with calendar month lengths. It reports OLS slopes with HAC lag-3 uncertainty and Holm-adjusted p-values across 36 tests. The intervals describe individual slopes. The analysis is exploratory and applies to the selected model cells and fixed time windows. [Challenge brief](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) · [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) · [Trend method and tests](trend_lab/README.md)

The NASA workflow and this independent integration are the Space Apps contribution. The Flood Lab engine, Nepal 3D investigation and earlier case, terrain, NDVI, drainage and evaluation results come from SATQuery. The new case viewer exposes their measured layers, quality masks and source provenance. Two-date NDVI differences show the available optical observations. Their projection onto terrain is for inspection. Physical registration, surveyed drainage connectivity and independent flood exposure accuracy remain unresolved. See [scope and verification](VERIFICATION.md).

## Credits and SI disclosure

OpenAI Codex assisted code, calculation implementation, tests, interface work and documentation. The team supplied the volcano wordmark. The header displays an SI-generated indicator. The Codex-authored fallback mark also carries an SI label. Existing Scientific Noir and Flood Lab decorative art came from the SATQuery project. Its generation method is unconfirmed. Scientific source observations retain their original credits and hashes. The Q&A on the NASA trends page uses fixed matching. The Nepal workflows use bounded, source-linked analysis. [Data sources and terms](DATA_LICENSES.md) · [Code license](LICENSE) · [Logo placement](UI/assets/README.md)
