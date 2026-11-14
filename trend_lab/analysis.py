"""Auditable annual trend analysis. SI-assisted code: OpenAI Codex.

HAC inference is exploratory and conditional on a linear trend with weakly
dependent residuals. It does not attribute causes or establish field accuracy.
"""

import calendar
import hashlib
import json
import math

import numpy as np
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

from config import END, REGIONS, ROOT, START, VARIABLES

METHOD = {
    "estimator": "ordinary least squares on complete annual values",
    "uncertainty": "Newey–West HAC, Bartlett kernel, lag 3, n/(n−2) correction; Student t reference with n−2 degrees of freedom",
    "multiplicity": "Holm family-wise adjustment across all 12 region × variable tests for the selected time window; invalid tests enter as p=1",
    "sensitivity": "Unadjusted slope confidence intervals and p-values also reported at HAC lags 1 and 5",
    "minimum_years": 20,
    "alpha": 0.05,
    "interpretation": "Exploratory, model-conditional evidence. Repeated exploration of different date windows is not covered by this correction. Statistical significance is not practical importance or causation.",
}


def annual_values(payload, variable, start=START, end=END):
    if payload["parameters"][variable]["units"] != VARIABLES[variable]["api_unit"]:
        raise ValueError("Unexpected source units")
    values = payload["properties"]["parameter"][variable]
    fill = payload["header"]["fill_value"]
    annual = []
    missing_years = []
    for year in range(start, end + 1):
        months = [values.get(f"{year}{month:02d}") for month in range(1, 13)]
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value == fill for value in months):
            missing_years.append(year)
            continue
        if variable == "PRECTOTCORR" and any(value < 0 for value in months):
            raise ValueError("Negative precipitation is invalid")
        days = [calendar.monthrange(year, month)[1] for month in range(1, 13)]
        value = sum(value * count for value, count in zip(months, days))
        if variable == "T2M":
            value /= sum(days)
        annual.append({"year": year, "value": value})
    return annual, missing_years


def fit_series(annual):
    years = np.asarray([row["year"] for row in annual], dtype=float)
    values = np.asarray([row["value"] for row in annual], dtype=float)
    if len(years) < METHOD["minimum_years"]:
        return {"status": "insufficient", "reason": "At least 20 complete years are required for this prototype's inference gate."}
    if not np.all(np.diff(years) == 1):
        return {"status": "incomplete", "reason": "Missing years break the annual spacing assumed by HAC; no significance is reported."}
    if not np.isfinite(values).all():
        return {"status": "invalid", "reason": "The series contains non-finite values."}
    if np.ptp(values) < 1e-12:
        return {"status": "constant", "reason": "Constant series; stochastic significance is undefined."}
    x = years - years.mean()
    design = sm.add_constant(x)
    model = sm.OLS(values, design).fit()
    if float(np.max(np.abs(model.resid))) < 1e-10:
        return {"status": "degenerate", "reason": "No residual variability; a stochastic confidence interval is not reported."}
    summaries = {}
    for lag in (1, 3, 5):
        robust = model.get_robustcov_results(cov_type="HAC", maxlags=lag, use_correction=True, use_t=True)
        interval = robust.conf_int(alpha=0.05)[1] * 10
        summaries[str(lag)] = {"ci95_per_decade": interval.tolist(), "p": float(robust.pvalues[1]), "standard_error_per_decade": float(robust.bse[1] * 10)}
    primary = summaries["3"]
    return {"status": "ok", "n": len(years), "slope_per_decade": float(model.params[1] * 10), "fitted_change": float(model.params[1] * (years[-1] - years[0])), "mean": float(values.mean()), "fit": [{"year": int(year), "value": float(value)} for year, value in zip(years, model.fittedvalues)], **primary, "hac_sensitivity": summaries}


def analyze(start=START, end=END):
    if not (START <= start <= end <= END):
        raise ValueError(f"Choose years between {START} and {END}.")
    if end - start + 1 < METHOD["minimum_years"]:
        raise ValueError("Choose a window of at least 20 years.")
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    entries = {entry["region"]["id"]: entry for entry in manifest["entries"]}
    results = []
    for region in REGIONS:
        entry = entries[region["id"]]
        raw = (ROOT / "data" / entry["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Source integrity check failed for {region['name']}; restore or reacquire the data.")
        payload = json.loads(raw)
        for variable in VARIABLES:
            annual, missing = annual_values(payload, variable, start, end)
            results.append({"region": region, "variable": variable, "annual": annual, "missing_years": missing, "source_sha256": entry["sha256"], "source_url": entry["url"], **fit_series(annual)})
    adjusted = multipletests([row.get("p", 1.0) for row in results], method="holm", alpha=0.05)[1]
    for row, probability in zip(results, adjusted):
        row["p_adjusted"] = float(probability) if row["status"] == "ok" else None
        row["significant"] = bool(row["status"] == "ok" and probability < 0.05)
    return {"title": "SATQuery Trend Lab", "start": start, "end": end, "variables": VARIABLES, "method": METHOD, "source": {"name": manifest["source"], "spatial_resolution": "0.5° latitude × 0.625° longitude (native meteorology grid)", "meaning": "NASA model/reanalysis values for the grid cell selected by each coordinate; not station measurements or a city-wide average", "si_disclosure": manifest["si_disclosure"]}, "results": results}


if __name__ == "__main__":
    output = analyze()
    (ROOT / "data" / "analysis.json").write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    for row in output["results"]:
        print(row["region"]["name"], row["variable"], row["status"], round(row.get("slope_per_decade", 0), 4), row["p_adjusted"])
