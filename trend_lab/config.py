"""Fixed, disclosed sampling frame. SI-assisted code: OpenAI Codex, 2026-11-14."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
START, END = 1984, 2025
REGIONS = [
    {"id": "delhi", "name": "Delhi", "country": "India", "lat": 28.614, "lon": 77.209},
    {"id": "manaus", "name": "Manaus", "country": "Brazil", "lat": -3.119, "lon": -60.022},
    {"id": "nairobi", "name": "Nairobi", "country": "Kenya", "lat": -1.286, "lon": 36.817},
    {"id": "sydney", "name": "Sydney", "country": "Australia", "lat": -33.869, "lon": 151.209},
    {"id": "fairbanks", "name": "Fairbanks", "country": "United States", "lat": 64.838, "lon": -147.716},
    {"id": "reykjavik", "name": "Reykjavík", "country": "Iceland", "lat": 64.147, "lon": -21.94},
]
VARIABLES = {
    "T2M": {"name": "Air temperature", "api_unit": "C", "unit": "°C", "aggregation": "day-weighted annual mean", "description": "Temperature at 2 metres"},
    "PRECTOTCORR": {"name": "Precipitation", "api_unit": "mm/day", "unit": "mm", "aggregation": "annual total from monthly mean daily rates", "description": "Bias-corrected precipitation"},
}
NASA_DOCS = "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/"
