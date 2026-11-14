# Reproducibility

Run the core diagnostic with Python 3.14.6 or another compatible Python 3.11+ interpreter. It uses the standard library only. From this final package directory, the parent workspaces resolve automatically. Use --workspace to point to a copy of the preserved workspace. The source-index paths are relative to that workspace.

```powershell
python -B experiments/evidence_discrimination/run.py --output .runtime-r3-recheck
python -B experiments/evidence_discrimination/check.py --repeat .runtime-r3-recheck
```

The first command verifies the 44 V2, 44 CEGS, 9 compact exposure and 15 compact drainage artifacts, checks the frozen road prediction and ADCP block hashes, writes the label-independent order artifact and scores the fixed inputs. The previously inspected Canadian outcome values are never used to rank the predictions. The second command verifies candidate identity and score ties, all match-count accounting and byte equality with the released measurements. Use a fresh output directory for each repeat.

Key original sources relative to the workspace:

- Ahr code and nine-file compact exposure pack are in exposure-verification-20261112/repo at aee5e52c386e39e7576f6d3642869facd23716e7. The spectral protocol commit is adf9d672732a806d75575af1386cbd87f8924598 and the original road predictor seal records b5c5b1ff76fc2b9021521cd5b974f8e4608f41a8.
- Road outcome rows are in exposure-verification-20261112/repo/.runtime/exposure-verification/ahr-results-2/rows.json. They use the unchanged SpaceNet convention where explicitly noted.
- CEGS prediction and protocol seals are in cegs-novelty-20261112/measurements/pilot/pilot_seal.json. The original 22 fixtures and outcomes are in the same pilot's fault_control.py and measurements/faults.
- Canadian blocks are in drainage-validation-20261112/repo/.runtime/drainage-validation/observed-control-1/blocks.json, verified by that checkout's published compact observed-run-manifest.json. Measurement release commit 705279c3e9d6bb651d0063bf2bcd4305c4c930b1.
- V2 source, assets, pinned dependencies and the 277-input local replay archive are in exposure-verification-20261112/repo/research/manuscripts/researcher-3-revision. The [original results index](../tables/original_results_index.csv) gives exact file paths and SHA-256 values. Local SpaceNet geometries and third-party rasters retain original access and licensing terms.

The final outputs are archived in experiments/evidence_discrimination, experiments/baseline_comparisons, experiments/validation and tables. The V2-derived figures are copied byte-for-byte. For the three new figures, use the same scientific environment as the previous stage under WSL. Set workspace to the directory containing the preserved worktrees. This environment used Python 3.11.16, matplotlib 3.10.8, Shapely 2.2.0 and pyproj 3.7.2. See requirements-scientific.txt beside the figure script for its pinned environment.

```bash
workspace=/path/to/satquery-workspace
export PYTHONPATH="$workspace/drainage-consistency-20261112/repo/.runtime/drainage-deps"
"$workspace/research-campaign-20261107/repo/.runtime/validation-env/bin/python" experiments/baseline_comparisons/plot.py
```

For typesetting on Windows, the editable manuscript uses Python 3.12, python-docx 1.2.0, lxml 6.1.1 and the Word Office16 MathML-to-OMML transform. Desktop Word 16.0 performs PDF export. Run from this final package directory.

```powershell
python experiments/document_build/build_manuscript_docx.py
& experiments/document_build/export_manuscript_pdf.ps1 -Docx manuscript/SATQUERY_R3_FINAL.docx -Pdf manuscript/SATQUERY_R3_FINAL.pdf
```

A clean scientific replay requires access to the named preserved input worktrees or the corresponding original artifacts. The final manuscript files, summary results, protocols, category definitions and plots are present here. The reproduction test ran from a separate output directory against the verified local inputs. No fresh dependency install, raw-provider reacquisition or new physical validation was performed.

