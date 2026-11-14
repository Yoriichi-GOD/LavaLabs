"""Acquire declared SpaceNet reference files and independent optical/terrain inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import math
from pathlib import Path
import re

import requests
from rasterio.warp import transform_bounds
from shapely.geometry import box, shape

from research.datasets.cog import acquire as terrain_crop
from research.experiments.drainage_acquire import acquire as optical_crop
from research.terrain_exposure.io import save_json, sha256

PROTOCOL = Path(__file__).with_name("road-exposure-20261112.json")
SEARCH = "https://earth-search.aws.element84.com/v1/search"
ITEMS = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/"


def get(url, cap):
    with requests.get(url, timeout=(10, 45), stream=True) as response:
        response.raise_for_status()
        raw = bytearray()
        for part in response.iter_content(65536):
            raw.extend(part)
            if len(raw) > cap:
                raise ValueError("Source exceeds its transfer cap")
        return bytes(raw)


def reference_files(output):
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    population = json.loads(PROTOCOL.read_text())["population"]
    mapping_url = population["source"] + "Germany_Training_Public_label_image_mapping.csv"
    mapping = out / "mapping.csv"
    mapping.write_bytes(get(mapping_url, 65536))
    if sha256(mapping) != population["mapping_sha256"]:
        raise ValueError("Publisher mapping identity changed")
    rows = list(csv.DictReader(io.StringIO(mapping.read_text())))
    names = sorted(r["label"] for r in rows if r["post-event image 1"].startswith("10500500E6DD3C00_")
                   and not r["post-event image 2"].strip())
    if (len(names) != population["expected_tiles"] or len(set(names)) != len(names)
            or any(not re.fullmatch(r"0_\d+_\d+\.geojson", name) for name in names)):
        raise ValueError("Metadata selection changed")
    cap = population["max_annotation_bytes"]//len(names)
    def fetch(name):
        url = population["source"] + "annotations/" + name
        try:
            for attempt in range(3):
                try:
                    raw = get(url, cap)
                    break
                except (requests.ConnectionError, requests.Timeout):
                    if attempt == 2:
                        raise
            path = out / name
            path.write_bytes(raw)
            return {"file": name, "bytes": len(raw), "sha256": sha256(path), "url": url, "status": "ACQUIRED"}
        except Exception as error:
            return {"file": name, "status": "FAILED", "reason": str(error)[:160]}
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(fetch, names))
    save_json(out / "receipt.json", {"mapping_url": mapping_url, "mapping_sha256": sha256(mapping),
        "selected": len(names), "files": records, "semantic_labels_read": False,
        "annotation_bytes": sum(r.get("bytes", 0) for r in records), "protocol_sha256": sha256(PROTOCOL)})
    print({"selected": len(names), "acquired": sum(r["status"] == "ACQUIRED" for r in records)}, flush=True)


def predictor_files(output):
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(PROTOCOL.read_text())
    cfg = protocol["observations"]
    crs = cfg["crs"]
    wgs = protocol["population"]["image_envelope_wgs84"]
    left, bottom, right, top = transform_bounds("EPSG:4326", crs, *wgs, densify_pts=32)
    halo = cfg["domain_halo_m"]
    bbox = list(transform_bounds(crs, "EPSG:4326", left-halo, bottom-halo, right+halo, top+halo,
                                 densify_pts=32))
    query = {"collections": ["sentinel-2-l2a"], "bbox": bbox,
             "datetime": cfg["pre_dates"], "limit": 100}
    response = requests.post(SEARCH, json=query, timeout=(10, 45))
    response.raise_for_status()
    metadata = response.json()
    save_json(out / "pre-query.json", {"query": query, "response": metadata})
    context = metadata.get("context", {})
    if context.get("matched") != len(metadata["features"]) and any(
            link.get("rel") == "next" for link in metadata.get("links", [])):
        raise ValueError("Pre search results truncated")
    covering = [i for i in metadata["features"] if shape(i["geometry"]).covers(box(*bbox))]
    if not covering:
        raise ValueError("No full-envelope pre scene")
    covering.sort(key=lambda i: i["id"])
    covering.sort(key=lambda i: i["properties"]["datetime"], reverse=True)
    covering.sort(key=lambda i: i["properties"].get("eo:cloud_cover", 101))
    post = json.loads(get(ITEMS+"S2A_32ULB_20210718_1_L2A", 1048576))
    if not shape(post["geometry"]).covers(box(*bbox)):
        raise ValueError("Declared post scene does not fully cover halo")
    optical = {}
    for period, scene in [("pre", covering[0]), ("post", post)]:
        folder = out / period
        folder.mkdir()
        save_json(folder / "item.json", scene)
        records = {}
        for band in cfg["bands"]:
            asset = scene["assets"][band]
            calibration = asset.get("raster:bands", [{}])[0]
            if band != "scl" and not {"scale", "offset"} <= calibration.keys():
                raise ValueError("Explicit optical calibration required")
            path = folder / (band+".tif")
            receipt = optical_crop(asset["href"], bbox, path, product=f"Sentinel-2 L2A {scene['id']} {band}",
                license_url="https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice",
                max_pixels=2000000)
            records[band] = {"path": path.relative_to(out).as_posix(), "sha256": receipt["sha256"],
                "scale": calibration.get("scale", 1), "offset": calibration.get("offset", 0)}
        optical[period] = {"assets": records, "item": f"{period}/item.json",
                           "item_sha256": sha256(folder / "item.json"),
                           "datetime": scene["properties"]["datetime"], "id": scene["id"]}
        print({"period": period, "scene": scene["id"]}, flush=True)
    dem = []
    for lat in range(math.floor(bbox[1]), math.ceil(bbox[3])):
        for lon in range(math.floor(bbox[0]), math.ceil(bbox[2])):
            tile = f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM"
            path = out / f"dem-{lat}-{lon}.tif"
            receipt = terrain_crop(f"https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif",
                bbox, path, product="Copernicus GLO-30",
                license_url="https://registry.opendata.aws/copernicus-dem/", max_pixels=1000000)
            dem.append({"path": path.name, "sha256": receipt["sha256"]})
    save_json(out / "receipt.json", {"protocol_sha256": sha256(PROTOCOL),
        "bbox": bbox, "crs": crs, "optical": optical, "dem": dem,
        "predictor_selection": "Optical source metadata and declared reference image envelope only"})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["reference", "predictor"])
    p.add_argument("--output", required=True)
    a = p.parse_args()
    (reference_files if a.kind == "reference" else predictor_files)(a.output)
