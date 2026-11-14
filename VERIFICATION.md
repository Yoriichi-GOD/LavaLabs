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

The NASA panel returned a Delhi-area precipitation slope of +49.90 mm/decade with a Holm-adjusted p-value of 0.188 for 1984–2025. Its direct exports returned a 42-row annual CSV, a JSON evidence attachment and the original NASA response. The clean checkout restored all 54 demo files and their original checksums. The evidence bundle includes the cases, two Nepal runs and the full terrain replay. This check used the already installed pinned Python packages.

## Repeat the checks

```sh
.venv-linux/bin/python scripts/bootstrap_demo.py --verify
.venv-linux/bin/python -m pytest -q tests trend_lab/test_analysis.py
(cd components/floodlab && ../../.venv-linux/bin/python -m pytest -q tests)
(cd trend_lab && node test_question.cjs)
```

The public checkout skips the test that requires the original EMSR geometry files. The original reference hash check runs with those files in the full local copy. Original case and graph manifests remain authoritative for the full working research sets. The public inventory identifies the subset in Git.

The four case labels identify Syapru Besi, Kedarnath, Varanasi and Sangam Vihar. The Ahr and Canadian ADCP studies are separate controls. The Nepal terrain surface is a historical DSM. The higher-resolution post-event surface missed its coverage threshold. These records support software replay and evidence review. Independent flood exposure accuracy, drainage hydraulics and human analyst benefit remain open research questions.
