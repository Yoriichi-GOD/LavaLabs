# SATQuery Trend Lab

A standalone Space Apps-oriented extension for **Be An Earth System Trend Detective!** Developed on 14 November 2026. It demonstrates a complete, bounded path from NASA source data to a trend, uncertainty, regional comparison and downloadable evidence. It has not been submitted, publicly hosted or approved for reuse eligibility.

## Open the prototype

Open **SATQuery_Trend_Lab.html** in a browser. It contains the data, map and application, and works without a server or live NASA API. Internet access is needed only if you follow an external source link. The source, manifest, CSV and evidence downloads work within the self-contained file.

Alternatively, from this directory run `python -m http.server 8772 --bind 127.0.0.1 --directory web` and open `http://127.0.0.1:8772`. This local address is not an eligible public submission link.

Try **Is Delhi getting wetter?**, select **Manaus**, then compare the three periods. The question box uses a fixed keyword matcher; it is not an LLM or a general scientific question-answering system.

## Actual scope

- NASA POWER monthly T2M and PRECTOTCORR, obtained from its public point API, sourced from MERRA-2.
- Six predetermined requested coordinates near Delhi, Manaus, Nairobi, Sydney, Fairbanks and Reykjavík. They were specified before inspecting the results. They select coarse model grid cells, not city-wide averages or local station measurements.
- January 1984–December 2025: 504 months per variable per location, 12 series, 6,048 monthly values. These are not independent experimental trials.
- Three fixed analysis periods: 1984–2025, 1984–2004 and 2005–2025. All are frozen and computed before browser interaction. Arbitrary locations, new variables and custom dates are not implemented.
- Annual temperature is day-weighted; precipitation converts mm/day to totals with actual calendar month lengths. Annual-summary month 13 is excluded. Null, sentinel and nonfinite values do not become zero. Inference requires 20 complete consecutive annual values.
- OLS slope per decade and fitted change; HAC lag-3 uncertainty with Student t reference and finite-sample correction; marginal 95% slope intervals; Holm-adjusted p-values over all **36** fixed comparisons. Lags 1 and 5 are retained as sensitivity checks. This is approximate, exploratory inference, not a calibrated scientific validation campaign.
- Linked map/table, fixed question matching, source downloads, CSV and an evidence receipt with exact source URL and hash.

Source hashes are verified before analysis. The static export contains retained outputs, not runtime server inference. Original response bytes are preserved in `data/` and `web/data/sources/`; the single-file version embeds their UTF-8 contents for exact download.

## Reproduce

The verified environment is Python 3.11.16 on Linux/WSL. Exact installed versions are in `requirements-lock.txt`; principal dependencies are pinned in `requirements.txt`.

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python acquire.py
.venv/bin/python -m unittest -v
.venv/bin/python analysis.py
.venv/bin/python export.py
node test_question.cjs
node --check web/app.js
```

To reproduce the frozen numerical results, **skip `acquire.py`** and use the supplied original responses. Reacquisition is a separate live-data run and can change metadata or values. `analysis.py` alone reports a 12-test family for its selected window; **the application uses `export.py`, which adjusts across all 36 tests**. Do not mix these p-values.

## Verification and limits

See `VERIFICATION.md`. The full pipeline caught and fixed a NumPy boolean JSON-serialization failure that isolated numerical tests did not catch. Controls cover aggregation, sentinel handling, known slopes, declines, unit/offset invariance, abstention, source tampering and actual-data export. They establish software behavior, not independent Earth-science accuracy.

The full-period temperature decline in the selected Delhi cell is counterintuitive and remains a model-product result. The day-weighted annual values agree with NASA's annual summaries to rounding; that checks aggregation, not independent physical truth. Independent observations, source-change/homogeneity checks and explanation of this result are still required before making a broader climate claim.

## Relationship to prior SATQuery

This folder does not change the existing SATQuery application or its historical benchmarks. Earlier image comparison, flood, terrain, model and evaluation work is prior work. This new module focuses on the selected Space Apps brief. Integration into the main shell and public publication remain separate steps. No organizer clearance for extending the prior platform has been established.

## Attribution and SI disclosure

OpenAI Codex assisted implementation, analysis code, debugging, tests and writing. NASA source values are not SI-generated or modified. The question box uses deterministic matching and no external model. No generated photographs, video, audio or NASA branding are used.

- [Official challenge](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/)
- [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/)
- [POWER meteorological sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/)
- [POWER methodology and spatial resolution](https://power.larc.nasa.gov/docs/methodology/)
- [statsmodels HAC](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)
- [statsmodels multiple testing](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)
- [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [statsmodels](https://www.statsmodels.org/), [Python](https://www.python.org/); transitive dependencies recorded in the lock file.
- Map: Natural Earth 1:110m land polygons, public domain, fetched from [the authors' repository](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson), blob `04811d72fff2701ec67587e30ad8942675b511e3`. [Terms](https://www.naturalearthdata.com/about/terms-of-use/). This map provides geographic context, not NASA trend data.
