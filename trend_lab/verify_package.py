"""Independent, standard-library checks of retained and exported arithmetic.

This does not validate the significance model against independent observations.
SI-assisted code: OpenAI Codex.
"""

import calendar
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify():
    html = (ROOT / "SATQuery_Trend_Lab.html").read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="frozen-data">(.*?)</script>', html, re.S)
    assert match, "Missing self-contained data"
    embedded = json.loads(match.group(1))
    assert 'src="app.js"' not in html and 'href="style.css"' not in html
    assert html == (ROOT / "web" / "snapshot.html").read_text(encoding="utf-8")
    bundle = embedded["bundle"]
    assert bundle == json.loads((ROOT / "web" / "data" / "analysis.json").read_text(encoding="utf-8"))
    originals = {}
    for entry in embedded["manifest"]["entries"]:
        raw = (ROOT / "data" / entry["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        assert embedded["originals"][entry["region"]["id"]].encode("utf-8") == raw
        source = json.loads(raw)
        assert source["header"]["sources"] == ["MERRA2"]
        assert source["geometry"]["coordinates"][:2] == [entry["region"]["lon"], entry["region"]["lat"]]
        originals[entry["region"]["id"]] = source
    checked_annual = 0
    tests = []
    for window in bundle["windows"]:
        assert len(window["results"]) == 12
        for row in window["results"]:
            source = originals[row["region"]["id"]]
            months = source["properties"]["parameter"][row["variable"]]
            assert len([key for key in months if key[-2:] != "13"]) == 504
            assert row["status"] == "ok" and len(row["annual"]) == row["n"]
            for point in row["annual"]:
                year = point["year"]
                values = [months[f"{year}{month:02d}"] for month in range(1, 13)]
                assert all(math.isfinite(value) and value != source["header"]["fill_value"] for value in values)
                days = [calendar.monthrange(year, month)[1] for month in range(1, 13)]
                expected = sum(value * count for value, count in zip(values, days))
                if row["variable"] == "T2M":
                    expected /= sum(days)
                    # NASA annual summaries provide an independent API-side aggregation check.
                    assert abs(expected - months[f"{year}13"]) <= 0.025
                assert abs(expected - point["value"]) < 1e-9
                checked_annual += 1
            years = [point["year"] for point in row["annual"]]
            values = [point["value"] for point in row["annual"]]
            mean_x, mean_y = sum(years) / len(years), sum(values) / len(values)
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(years, values)) / sum((x - mean_x) ** 2 for x in years)
            assert abs(slope * 10 - row["slope_per_decade"]) < 1e-8
            tests.append(row)
    assert len(tests) == 36
    ordered = sorted(enumerate(tests), key=lambda item: item[1]["p"])
    previous = 0
    for rank, (_, row) in enumerate(ordered):
        previous = min(1, max(previous, (len(tests) - rank) * row["p"]))
        assert abs(previous - row["p_adjusted"]) < 1e-12
        assert row["significant"] == (previous < 0.05)
    receipt = {"source_files": len(originals), "analyses": len(tests), "annual_values_recounted": checked_annual, "checks": ["embedded raw-source bytes and hashes", "source coordinates and source type", "complete monthly coverage", "annual aggregation including NASA annual temperature summaries", "independent OLS slope formula", "independent Holm correction over 36 tests", "self-contained packaging"], "result": "pass", "scope": "Software, source integrity and arithmetic; not independent scientific validation or causal attribution."}
    (ROOT / "PACKAGE_VERIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    verify()
