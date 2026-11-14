# Verification receipt — 14 November 2026

## Passed

1. **NASA acquisition:** six successful public point-API downloads. Actual metadata: monthly/annual API v2.10.0, source MERRA2, T2M C, PRECTOTCORR mm/day, fill −999, January 1984–December 2025. All twelve series have 504 usable monthly values. Exact URLs, retrieval timestamps and SHA-256 hashes are in `data/manifest.json`.
2. **Python controls and integration:** `python -m unittest -v` passed **10 tests**. Coverage: leap-year precipitation aggregation; day-weighted temperature; missing/fill/nonfinite handling; unit mismatch; known positive and negative slopes; offset/unit-scale invariance; short, gapped, constant and perfect-series abstention; complete real-data JSON export; rejection of changed source bytes.
3. **JavaScript checks:** `node test_question.cjs` passed **10 assertions** covering supported locations/variables, accent normalization, refusal of forecasts and causal questions, unsupported dates/questions, ambiguous queries and p-value formatting. `node --check web/app.js` passed.
4. **Independent arithmetic/package check:** `python verify_package.py` passed, verifying six original source hashes/coordinates, exact embedded source bytes, 504-month coverage, **1,008 annual values across the three overlapping periods**, all **36 OLS slopes**, and independently recalculated Holm adjustment across 36 tests. Annual temperature aggregation also agrees with NASA's annual-summary fields within rounding tolerance. `PACKAGE_VERIFICATION.json` is the machine-readable receipt. The 1,008 count includes overlapping windows and is not independent data.
5. **Actual browser flow:** a served prototype loaded real data and charts. “Is Delhi getting wetter?” selected the correct variable and location, showed +49.90 mm/decade, adjusted p≈0.188 and an insufficient-evidence verdict. Region selection changed to Manaus; period selection changed to 2005–2025 with 21 annual values and updated results/source URL. An unsupported future question received a historical-only explanation while keeping the previous valid result.
6. **Browser exports:** the downloaded Manaus precipitation CSV contained 21 years, 2005–2025. Its values matched the corresponding downloaded evidence JSON. The self-contained snapshot also downloaded original Delhi source bytes through its embedded-data path after the local server was stopped; the downloaded hash was compared with the retained original.
7. **Responsive check:** the 390 × 844 viewport rendered the responsive layout. Read-only DOM inspection reported viewport width 390 and document width 375, with no horizontal overflow. Map targets remain within the content width. The temporary viewport override was reset.
8. **Preservation:** `git -C research-campaign-20261107/repo status --short` was empty before and after this work. Its recorded head remains `9d4ad50eaf50466cec380436bbf559ccb515e43f`. All new work is in a separate directory; no synced `sources/` material was changed.
9. **Submission summary:** 125 words, 901 characters; within the supplied 50–200 word suggestion and 1,500-character field limit.

The first full actual-data export exposed a NumPy boolean serialization failure after eight isolated controls had passed. It was fixed by converting the exported decision to a native boolean, and the integration suite now checks strict JSON serialization. The first Windows dependency setup could not resolve the package host; the verified analysis used a separate Linux/WSL environment. Those failures are not hidden by the passing final state.

## Not established

- Independent scientific accuracy, physical representativeness of every grid cell, robustness to strong/long-memory dependence or structural breaks, source homogeneity, causal attribution, forecast skill or user decision benefit.
- Whether the selected Delhi cooling trend is supported by an independent dataset. An API-side annual aggregation check is not independent climate evidence.
- Fresh Windows scientific-dependency installation. The standalone browser file does not need those packages; rebuild was tested with Python 3.11.16 on Linux/WSL.
- Exhaustive browser/device/accessibility coverage. The reported checks cover the routes described above, not every browser combination or all native file-opening behaviors.
- Public deployment, a finished seven-slide/video artifact, organizer approval to extend prior SATQuery work, or competition submission. No public upload or application submission was performed.

The application is a frozen demonstration of a documented, approximate analysis. Software tests and arithmetic agreement do not establish Earth-science truth.
