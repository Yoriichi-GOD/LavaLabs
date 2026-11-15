# Scope and verification

## Definition of done

- Independent project with its own services, environment, data and Git history.
- Scientific Noir UI with a replaceable volcano mark.
- Complete copied Flood Lab engine and local research, with a portable two-run public demonstration.
- Nepal 3D, source imagery, investigation trace and four measured case views.
- NASA variable selection, region and period comparison, trend estimates, significance and exports.
- Public checkout starts using only its bundled data and installed packages.

## Observed workflows

The browser rendered the saved 90 m Syapru Besi terrain and both optical dates. A cross-section returned 128 valid samples across 2,160 m. The contextual investigation returned a saved water-candidate summary and a three-tool trace. All four NDVI maps loaded with dates, source sampling, statistics and blank unsupported cells. Six reports were available in Research evidence. The processor returned an evidence-backed road topic answer. An invalid area request was rejected before acquisition.

The NASA panel returned a Delhi-area precipitation slope of +49.90 mm/decade with a Holm-adjusted p-value of 0.188 for 1984–2025. Its direct exports returned a 42-row annual CSV, a JSON evidence attachment and the original NASA response. The current archive verifies all 58 demo members, including the retained optical inputs for both saved runs. The evidence bundle includes the cases, two Nepal runs and the full terrain replay. These checks use the installed pinned Python packages.

On 15 November 2026, the 152-test LavaLabs regression suite passed, including eight subtests. Six focused Nepal and diagnostic tests also passed after checking the direct replay command. The diagnostic removes a synthetic seasonal cycle, limits an injected influential year's effect, checks real calendar-month rainfall arithmetic, and exports complete 504-month diagnostics for all 30 cell-variable series. The primary trend result fields were compared with the preceding case bundle and remained identical.

The generated Pages package was checked in a browser at 1440 px and 390 px: both diagnostic views rendered, variable and cell changes updated the result, CSV downloads had 504 data rows, JSON receipts identified NTRS 20090042747, and neither width overflowed. The existing public workflows retained 16 response pins, the optical toggle, 601 saved water candidates on terrain support, four cases, six research reports and both Nepal and legacy NASA downloads. The package has 349 files and uses saved evidence; these checks establish software behavior and replay, with the scientific limits below.

## Repeat the checks

```sh
.venv-linux/bin/python scripts/bootstrap_demo.py --verify
.venv-linux/bin/python -m pytest -q tests trend_lab/test_analysis.py
(cd components/floodlab && ../../.venv-linux/bin/python -m pytest -q tests)
(cd trend_lab && node test_question.cjs)
```

The public checkout skips the test that requires the original EMSR geometry files. The original reference hash check runs with those files in the full local copy. Original case and graph manifests remain authoritative for the full working research sets. The public inventory identifies the subset in Git.

The four case labels identify Syapru Besi, Kedarnath, Varanasi and Sangam Vihar. The Ahr and Canadian ADCP studies are separate controls. The Nepal terrain surface is a historical DSM. The higher-resolution post-event surface missed its coverage threshold. These records support software replay and evidence review. Independent flood exposure accuracy, drainage hydraulics and human analyst benefit remain open research questions.
