"""Export the fixed, frozen demo for a browser without live API dependency.

SI-assisted code: OpenAI Codex. Statistical plots use unmodified NASA inputs.
"""

import json
import shutil

from statsmodels.stats.multitest import multipletests

from analysis import analyze
from config import ROOT

WINDOWS = [(1984, 2025), (1984, 2004), (2005, 2025)]


def make_bundle():
    windows = [analyze(start, end) for start, end in WINDOWS]
    rows = [row for window in windows for row in window["results"]]
    adjusted = multipletests([row.get("p", 1.0) for row in rows], method="holm", alpha=0.05)[1]
    for row, probability in zip(rows, adjusted):
        row["p_adjusted"] = float(probability) if row["status"] == "ok" else None
        row["significant"] = bool(row["status"] == "ok" and probability < 0.05)
    for window in windows:
        window["method"]["multiplicity"] = "Holm family-wise adjustment across all 36 fixed demo tests: 6 coordinates × 2 variables × 3 time windows; invalid tests enter as p=1."
    return {"schema": 1, "kind": "Frozen real-data demonstration; browser controls inspect precomputed analyses, not a live NASA query", "windows": windows}


if __name__ == "__main__":
    bundle = make_bundle()
    destination = ROOT / "web" / "data"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "analysis.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "data" / "manifest.json", destination / "manifest.json")
    sources = destination / "sources"
    sources.mkdir(exist_ok=True)
    for path in (ROOT / "data").glob("*.json"):
        if path.stem not in ("analysis", "manifest"):
            shutil.copyfile(path, sources / path.name)
    embedded = {
        "bundle": bundle,
        "manifest": json.loads((destination / "manifest.json").read_text(encoding="utf-8")),
        "land": json.loads((ROOT / "web" / "land.geojson").read_text(encoding="utf-8")),
        "originals": {entry["region"]["id"]: (sources / entry["file"]).read_bytes().decode("utf-8") for entry in json.loads((destination / "manifest.json").read_text(encoding="utf-8"))["entries"]},
    }
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="style.css">', '<style>' + (ROOT / "web" / "style.css").read_text(encoding="utf-8") + '</style>')
    html = html.replace('<script src="app.js" defer></script>', '')
    frozen = json.dumps(embedded, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    scripts = '<script type="application/json" id="frozen-data">' + frozen + '</script><script>' + (ROOT / "web" / "app.js").read_text(encoding="utf-8") + '</script>'
    html = html.replace('</body>', scripts + '</body>')
    (ROOT / "SATQuery_Trend_Lab.html").write_text(html, encoding="utf-8")
    (ROOT / "web" / "snapshot.html").write_text(html, encoding="utf-8")
    print(f"Exported {len(bundle['windows'])} windows; {sum(len(window['results']) for window in bundle['windows'])} analyses")
