import calendar
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.trend_checks import seasonal_check


def monthly_fixture(with_outlier=False):
    values = {}
    for year in range(1984, 2026):
        for month in range(1, 13):
            value = 12 + 7 * np.sin(month * np.pi / 6) + (year - 1984) * .04 + .1 * np.cos(year)
            values[f"{year}{month:02}"] = value + (20 if with_outlier and year == 2025 else 0)
    return values


def test_seasonal_departures_remove_the_calendar_cycle_and_robust_fit_limits_an_outlier():
    values = monthly_fixture(with_outlier=True)
    result = seasonal_check(values, "T2M", 1984, 2025, -999)
    assert result["status"] == "ok"
    monthly = np.array([row["departure"] for row in result["monthly"]]).reshape(-1, 12)
    assert np.max(np.abs(monthly.mean(axis=0))) < 1e-12
    slope = np.polyfit(np.arange(42), monthly.mean(axis=1), 1)[0] * 10
    assert result["ols_slope_per_decade"] == pytest.approx(slope)
    assert abs(result["robust_slope_per_decade"] - .4) < abs(result["ols_slope_per_decade"] - .4)
    assert 2025 in result["downweighted_years"]
    values["200105"] = -999
    assert seasonal_check(values, "T2M", 1984, 2025, -999)["status"] == "incomplete"


def test_rainfall_month_lengths_and_annualization_match_total_anomalies():
    values = {key: abs(value) for key, value in monthly_fixture().items()}
    result = seasonal_check(values, "PRECTOTCORR", 1984, 2025, -999)
    totals = [sum(values[f"{year}{month:02}"] * calendar.monthrange(year, month)[1] for month in range(1, 13))
              for year in range(1984, 2026)]
    assert np.allclose([row["value"] for row in result["annual"]], np.array(totals) - np.mean(totals))
    assert result["ols_slope_per_decade"] == pytest.approx(np.polyfit(np.arange(42), totals, 1)[0] * 10)
    with pytest.raises(ValueError):
        seasonal_check({**values, "198402": -2}, "PRECTOTCORR", 1984, 2025, -999)


def test_new_diagnostics_and_resource_are_exported_for_each_real_cell():
    from fastapi.testclient import TestClient
    from lavalabs.server import create_app
    root = Path(__file__).resolve().parents[1]
    case = json.loads((root / "UI/nepal/data/case.json").read_bytes())["climate"]
    assert case["reference_method"]["document_id"] == "20090042747"
    for cell in case["cells"]:
        for variable, trend in cell["trends"].items():
            diagnostic = trend["seasonal_check"]
            assert len(diagnostic["monthly"]) == 504 and len(diagnostic["annual"]) == 42
            if variable == "PRECTOTCORR":
                assert diagnostic["ols_slope_per_decade"] == pytest.approx(trend["slope_per_decade"])
    with TestClient(create_app()) as client:
        stem = f"/api/lava/nepal/{case['site']['matching_cell']}/PRECTOTCORR"
        receipt = client.get(stem + "/json").json()
        assert receipt["climate"]["reference_method"]["document_id"] == "20090042747"
        export = client.get(stem + "/diagnostics")
        assert export.status_code == 200 and len(export.text.splitlines()) == 505
