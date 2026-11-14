"""Download original NASA responses, without an account or API key.

SI-assisted code: OpenAI Codex. NASA source values are not SI-generated.
"""

import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import END, REGIONS, ROOT, START, VARIABLES


def acquire():
    directory = ROOT / "data"
    directory.mkdir(exist_ok=True)
    entries = []
    for region in REGIONS:
        query = urlencode({"parameters": ",".join(VARIABLES), "community": "AG", "longitude": region["lon"], "latitude": region["lat"], "start": START, "end": END, "format": "JSON"})
        url = "https://power.larc.nasa.gov/api/temporal/monthly/point?" + query
        request = Request(url, headers={"User-Agent": "SATQuery-Trend-Lab/0.1 (Space Apps research prototype)"})
        with urlopen(request, timeout=90) as response:
            raw = response.read()
        data = json.loads(raw)
        for key, metadata in VARIABLES.items():
            if data["parameters"][key]["units"] != metadata["api_unit"]:
                raise ValueError(f"Unexpected {key} units: {data['parameters'][key]['units']}")
        if data["header"]["sources"] != ["MERRA2"]:
            raise ValueError("Source changed; review before use")
        filename = region["id"] + ".json"
        (directory / filename).write_bytes(raw)
        entries.append({"region": region, "file": filename, "url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "header": data["header"], "parameters": data["parameters"]})
        print(f"Saved {region['name']}: {len(raw):,} bytes", flush=True)
    manifest = {"schema": 1, "source": "NASA POWER / MERRA-2 reanalysis", "start": START, "end": END, "selection": "Six predetermined demonstration coordinates; no global coverage or city-scale resolution is claimed.", "si_disclosure": "OpenAI Codex assisted acquisition/analysis code and documentation. Original NASA data values are retained unchanged.", "entries": entries}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    acquire()
