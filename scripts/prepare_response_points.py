"""Extract retained historical OSM points for the two packaged Nepal runs."""
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
from shapely import from_wkb
from shapely.geometry import mapping


RUN_SOURCES = {
    "event-fe47db331390": ("automatic/event-fe47db331390/historical-osm.parquet", "2026-08-25T00:00:00Z"),
    "nepal-syapru-004": ("osm_pre_event/nepal-corridor-20260727.parquet", "2026-07-27T00:00:00Z"),
}
PLACES = {"city", "town", "village", "hamlet", "isolated_dwelling", "suburb", "quarter", "neighbourhood"}
CARE = {"hospital", "clinic", "doctor", "doctors", "health_post"}


def extract(root):
    result = {}
    for run_id, (source, timestamp) in RUN_SOURCES.items():
        path = root / source
        points = []
        columns = ["osm_id", "osm_type", "version", "tags", "geom"]
        for row in pq.read_table(path, columns=columns).to_pylist():
            tags = dict(row["tags"])
            role = next((value for value in (tags.get("amenity"), tags.get("healthcare")) if value in CARE), None)
            if role is None and tags.get("place") not in PLACES:
                continue
            shape = from_wkb(row["geom"])
            if shape.is_empty:
                continue
            identifier = f"{row['osm_type']}/{row['osm_id']}"
            point = shape.representative_point()
            points.append({
                "id": identifier,
                "version": row["version"],
                "name": tags.get("name:en") or tags.get("name") or identifier,
                "kind": "care" if role else "settlement",
                "place_type": role or tags["place"],
                "point": list(mapping(point)["coordinates"]),
            })
        with path.open("rb") as file:
            digest = hashlib.file_digest(file, "sha256").hexdigest()
        result[run_id] = {
            "snapshot": timestamp, "source": source, "source_sha256": digest,
            "points": sorted(points, key=lambda point: point["id"]),
        }
    return {"license": "ODbL 1.0; © OpenStreetMap contributors", "source_url": "https://www.openstreetmap.org/copyright",
            "runs": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(extract(args.data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
