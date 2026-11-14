"""Scientific software checks using known controls, not field validation."""

import calendar
import json
import unittest
from unittest.mock import patch

import numpy as np

from analysis import annual_values, fit_series
from export import make_bundle
from config import ROOT


def payload(variable, values, unit):
    return {"parameters": {variable: {"units": unit}}, "header": {"fill_value": -999}, "properties": {"parameter": {variable: values}}}


class AggregationTests(unittest.TestCase):
    def test_precipitation_rate_becomes_leap_year_total(self):
        values = {f"2020{month:02d}": 2 for month in range(1, 13)}
        values["202013"] = 999999
        annual, missing = annual_values(payload("PRECTOTCORR", values, "mm/day"), "PRECTOTCORR", 2020, 2020)
        self.assertEqual(annual[0]["value"], 732)
        self.assertEqual(missing, [])

    def test_temperature_is_day_weighted(self):
        values = {f"2021{month:02d}": month for month in range(1, 13)}
        annual, _ = annual_values(payload("T2M", values, "C"), "T2M", 2021, 2021)
        expected = sum(month * calendar.monthrange(2021, month)[1] for month in range(1, 13)) / 365
        self.assertAlmostEqual(annual[0]["value"], expected)

    def test_missing_month_and_fill_do_not_become_zero(self):
        values = {f"2020{month:02d}": 2 for month in range(1, 12)}
        for value in (None, -999, float("nan")):
            values["202012"] = value
            annual, missing = annual_values(payload("T2M", values, "C"), "T2M", 2020, 2020)
            self.assertEqual(annual, [])
            self.assertEqual(missing, [2020])

    def test_wrong_units_fail(self):
        with self.assertRaises(ValueError):
            annual_values(payload("T2M", {}, "K"), "T2M", 2020, 2020)


class TrendTests(unittest.TestCase):
    def make_series(self, slope=0.04):
        years = np.arange(1984, 2026)
        rng = np.random.default_rng(2301)
        values = 12 + slope * (years - years.mean()) + rng.normal(0, 0.15, len(years))
        return [{"year": int(year), "value": float(value)} for year, value in zip(years, values)]

    def test_known_slope_is_recovered_and_interval_contains_truth(self):
        result = fit_series(self.make_series())
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["slope_per_decade"], 0.4, delta=0.05)
        lo, hi = result["ci95_per_decade"]
        self.assertLess(lo, 0.4)
        self.assertGreater(hi, 0.4)
        self.assertLess(result["p"], 0.05)

    def test_offset_and_unit_scale_invariance(self):
        original = self.make_series()
        converted = [{"year": row["year"], "value": row["value"] * 1000 + 273.15} for row in original]
        first, second = fit_series(original), fit_series(converted)
        self.assertAlmostEqual(first["p"], second["p"], places=10)
        self.assertAlmostEqual(second["slope_per_decade"], first["slope_per_decade"] * 1000, places=7)

    def test_decline_sign(self):
        result = fit_series(self.make_series(-0.04))
        self.assertLess(result["slope_per_decade"], 0)
        self.assertLess(result["ci95_per_decade"][1], 0)

    def test_short_constant_gapped_and_perfect_series_abstain(self):
        original = self.make_series()
        self.assertEqual(fit_series(original[:10])["status"], "insufficient")
        self.assertEqual(fit_series([row for row in original if row["year"] != 2000])["status"], "incomplete")
        self.assertEqual(fit_series([{"year": row["year"], "value": 4} for row in original])["status"], "constant")
        self.assertEqual(fit_series([{"year": row["year"], "value": row["year"] * 0.2} for row in original])["status"], "degenerate")


@unittest.skipUnless((ROOT / "data" / "manifest.json").exists(), "NASA source data have not been acquired")
class RealDataIntegrationTests(unittest.TestCase):
    def test_all_windows_export_with_native_json_types_and_complete_coverage(self):
        result = make_bundle()
        serialized = json.dumps(result, allow_nan=False)
        self.assertIn("Holm", serialized)
        for window in result["windows"]:
            self.assertEqual(len(window["results"]), 12)
            for row in window["results"]:
                self.assertEqual(row["status"], "ok")
                self.assertEqual(row["missing_years"], [])
                self.assertEqual(row["n"], window["end"] - window["start"] + 1)
                self.assertGreaterEqual(row["p_adjusted"], row["p"] - 1e-14)

    def test_changed_source_bytes_are_rejected(self):
        from pathlib import Path
        original = Path.read_bytes

        def altered(path):
            value = original(path)
            return value + b" " if path.name == "delhi.json" else value

        with patch.object(Path, "read_bytes", altered):
            with self.assertRaisesRegex(ValueError, "integrity"):
                make_bundle()


if __name__ == "__main__":
    unittest.main()
