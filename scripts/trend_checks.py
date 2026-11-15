"""Seasonality and robust-fit diagnostics adapted from Acker et al. (2009).

OpenAI Codex assisted implementation. This extension uses the NASA challenge's
listed NTRS methods resource on the existing POWER observations.
"""
import calendar
import math
from numbers import Real

import numpy as np
from scipy.stats import linregress
import statsmodels.api as sm

REFERENCE = {
    "title": "Time-Series Analysis of Remotely-Sensed SeaWiFS Chlorophyll in River-Influenced Coastal Regions",
    "authors": "Acker, McMahon, Shen, Hearty and Casey (2009)",
    "url": "https://ntrs.nasa.gov/citations/20090042747",
    "pdf_url": "https://ntrs.nasa.gov/api/citations/20090042747/downloads/20090042747.pdf",
    "document_id": "20090042747",
    "pdf_sha256": "5209cee13b536f0b4df59b6e4fac9f631fafd1458f1e4d936d2cfab5edda0ab3",
    "application": "Calendar-month departures averaged by year, followed by ordinary and robust slope comparisons.",
    "adaptation": "Applied to POWER temperature and rainfall. Huber regression with tuning 1.345 is our robustness diagnostic; the paper uses MATLAB robust regression. Primary OLS/HAC/Holm inference is retained.",
    "paper_sections": "Methods and Figure 15; Statistical Methods, Table 6 and Figure 16",
}


def seasonal_check(values, variable, start, end, fill):
    if variable not in {"T2M", "PRECTOTCORR"}:
        raise ValueError("Unsupported diagnostic variable")
    months = [(year, month, values.get(f"{year}{month:02}"))
              for year in range(start, end + 1) for month in range(1, 13)]
    if any(not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value) or value == fill
           for year, month, value in months):
        return {"status": "incomplete", "reason": "Seasonal comparison requires all 12 months in every selected year."}
    if variable == "PRECTOTCORR" and any(value < 0 for year, month, value in months):
        raise ValueError("Rainfall rates must be nonnegative")
    if end - start + 1 < 20:
        return {"status": "insufficient", "reason": "At least 20 complete years are required."}
    # POWER rainfall arrives as mean daily rate. Convert each month to its total.
    converted = np.array([value * calendar.monthrange(year, month)[1]
                          if variable == "PRECTOTCORR" else value
                          for year, month, value in months], dtype=float).reshape(-1, 12)
    climatology = converted.mean(axis=0)
    departures = converted - climatology
    annual = departures.mean(axis=1) * (12 if variable == "PRECTOTCORR" else 1)
    years = np.arange(start, end + 1)
    if np.ptp(annual) < 1e-10:
        return {"status": "constant", "reason": "Annual departures have no trend variation to compare.",
                "climatology": climatology.tolist()}
    x = years - years.mean()
    design = sm.add_constant(x)
    ordinary = linregress(x, annual)
    if np.max(np.abs(annual - (ordinary.intercept + ordinary.slope * x))) < 1e-10:
        return {"status": "degenerate", "reason": "A perfect linear series has no residual variation for a robust-fit comparison."}
    robust = sm.RLM(annual, design, M=sm.robust.norms.HuberT(t=1.345)).fit(maxiter=100, tol=1e-10)
    if robust.fit_history["iteration"] >= 100:
        return {"status": "unconverged", "reason": "Robust fit did not converge in the diagnostic budget."}
    slope = float(robust.params[1] * 10)
    return {
        "status": "ok", "n": len(years),
        "monthly_unit": "mm/month" if variable == "PRECTOTCORR" else "degC",
        "annual_unit": "mm/year" if variable == "PRECTOTCORR" else "degC",
        "aggregation": "Mean of 12 calendar-month departures, multiplied by 12 for annual precipitation.",
        "baseline": [start, end], "climatology": climatology.tolist(),
        "monthly": [{"month": f"{year}-{month:02}", "value": float(converted[index // 12, month - 1]),
                     "climatology": float(climatology[month - 1]), "departure": float(departures[index // 12, month - 1])}
                    for index, (year, month, _) in enumerate(months)],
        "annual": [{"year": int(year), "value": float(value),
                    "ols_fit": float(ordinary.intercept + ordinary.slope * (year - years.mean())),
                    "robust_fit": float(fitted), "weight": float(weight)}
                   for year, value, fitted, weight in zip(years, annual, robust.fittedvalues, robust.weights, strict=True)],
        "ols_slope_per_decade": float(ordinary.slope * 10),
        "robust_slope_per_decade": slope, "r_squared": float(ordinary.rvalue ** 2),
        "slope_difference_per_decade": slope - float(ordinary.slope * 10),
        "same_direction": bool(np.sign(slope) == np.sign(ordinary.slope)),
        "downweighted_years": [int(year) for year, weight in zip(years, robust.weights, strict=True) if weight < .5],
        "interpretation": "Descriptive sensitivity on one NASA product. Diagnostic regression weights are statistical influence measures. The primary significance verdict uses the original annual OLS/HAC/Holm test.",
    }
