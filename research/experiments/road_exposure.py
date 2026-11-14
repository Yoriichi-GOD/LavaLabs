"""Paired road screening on a sealed SpaceNet 8 cohort with a separate label stage."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import numpy as np
from rasterio.warp import reproject, Resampling
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape

from research.cases.process_campaign import metric_grid, warp
from research.evaluation.metrics import binary_metrics, ranking_metrics
from research.experiments.drainage_pilot import effective_calibration, regrid
from research.experiments.road_exposure_acquire import PROTOCOL
from research.terrain_exposure.graph import project
from research.terrain_exposure.hydrology import derive, topological_order
from research.terrain_exposure.io import save_json, sha256


METHODS = ("A_post", "B_change", "P_proximity", "C_terrain", "B_ndvi", "B_ndwi")
SHIFTS = ((0, 0), (30, 0), (-30, 0), (0, 30), (0, -30))
LABEL_AUDIT = Path(__file__).with_name("road-exposure-label-audit-20261112.json")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def checked_file(root, filename, digest):
    path = root / filename
    if sha256(path) != digest:
        raise ValueError(f"Source identity changed for {filename}")
    return path


def road_geometries(reference, receipt, crs):
    if len(receipt["files"]) != receipt["selected"] or any(
            r["status"] != "ACQUIRED" for r in receipt["files"]):
        raise ValueError("Declared reference cohort did not completely download")
    roads = defaultdict(list)
    counts = Counter()
    for record in receipt["files"]:
        src = checked_file(reference, record["file"], record["sha256"])
        data = read(src)
        if data["type"] != "FeatureCollection":
            raise ValueError("Expected GeoJSON FeatureCollection")
        for index, feature in enumerate(data["features"]):
            # Allowlist only pre-event highway membership and geometry during prediction.
            if not (feature.get("properties") or {}).get("highway"):
                continue
            counts["native_highway_features"] += 1
            geo = feature.get("geometry")
            if not geo or geo["type"] not in ("LineString", "MultiLineString"):
                counts["unusable_geometry"] += 1
                continue
            line = project(shape(geo), "EPSG:4326", crs)
            if line.is_empty or not line.is_valid or line.length < 20:
                counts["short_empty_or_invalid"] += 1
                continue
            roads[line.normalize().wkb_hex].append((record["file"], index, line))
    return roads, counts


def road_points(line):
    points, weights = [], []
    parts = [line] if line.geom_type == "LineString" else line.geoms
    for part in parts:
        if not part.length:
            continue
        count = math.ceil(part.length / 10)
        width = part.length / count
        points.extend(list(part.interpolate((j+.5)*width).coords[0])[:2] for j in range(count))
        weights.extend([width]*count)
    return np.asarray(points), np.asarray(weights)


def resample_flags(mask, source, target, method):
    out = np.zeros(target.shape, dtype="uint8")
    reproject(mask.astype("uint8"), out, src_transform=source.transform, src_crs=source.crs,
              dst_transform=target.transform, dst_crs=target.crs, resampling=method)
    return out > 0


def downstream_distances(hydro, seeds, support):
    """Propagate shortest distance to any seed in one topological pass."""
    if seeds.shape != hydro.grid.shape or support.shape != seeds.shape:
        raise ValueError("Candidate, support and drainage grids differ")
    reachable = np.full(seeds.size, np.inf)
    valid = (support & hydro.valid).ravel()
    reachable[(seeds.ravel() & valid)] = 0.
    next_cell = hydro.downstream.ravel()
    for current in topological_order(hydro.downstream, hydro.valid):
        target = next_cell[current]
        if target < 0 or not valid[target] or not np.isfinite(reachable[current]):
            continue
        distance = reachable[current] + math.dist(hydro.grid.centre(current), hydro.grid.centre(target))
        if distance <= 300 and distance < reachable[target]:
            reachable[target] = distance
    return reachable.reshape(seeds.shape)


def optical_maps(root, cfg, record, optical_grid):
    image = read(checked_file(root, record["item"], record["item_sha256"]))
    bands = {}
    for name, info in record["assets"].items():
        path = checked_file(root, info["path"], info["sha256"])
        scale, offset = effective_calibration(image, name, info)
        bands[name] = regrid(path, optical_grid, scale, offset, name == "scl")
    mask = np.isin(bands["scl"], cfg["valid_scl"])
    for name in ["green", "red", "nir", "swir16"]:
        mask &= np.isfinite(bands[name]) & (bands[name] >= 0)
    green, red, nir, swir = (bands[n] for n in ["green", "red", "nir", "swir16"])
    mask &= (green+swir > 1e-8) & (green+nir > 1e-8) & (nir+red > 1e-8)
    return {"valid": mask, "mndwi": green > swir, "ndwi": green > nir, "ndvi_high": nir-red > .2*(nir+red)}


def lookup(array, grid, points, missing):
    row = np.floor((points[:, 1]-grid.transform.f)/grid.transform.e).astype(int)
    col = np.floor((points[:, 0]-grid.transform.c)/grid.transform.a).astype(int)
    inside = (row >= 0) & (col >= 0) & (row < grid.shape[0]) & (col < grid.shape[1])
    result = np.full(len(points), missing)
    result[inside] = array[row[inside], col[inside]]
    return result


def road_features(points, weights, masks, g, terrain, t, proximity, path_distance):
    valid = lookup(masks["valid"], g, points, False) & lookup(terrain, t, points, False)
    coverage = float(weights[valid].sum()/weights.sum())
    if coverage < .8-1e-12:
        return {"coverage": coverage, "scores": None}
    points, weights = points[valid], weights[valid]
    fractions = {name: float(weights[lookup(masks[name], g, points, False)].sum()/weights.sum())
                 for name in ("A_post", "B_change", "B_ndvi", "B_ndwi")}
    p_distance = min(301., float(np.min(lookup(proximity, t, points, np.inf))))
    c_distance = min(301., float(np.min(lookup(path_distance, t, points, np.inf))))
    decision = {method: fraction >= .2-1e-12 for method, fraction in fractions.items()}
    decision.update(P_proximity=decision["B_change"] or p_distance <= 90,
                    C_terrain=decision["B_change"] or c_distance <= 90)
    return {"coverage": coverage, "scores": {**fractions,
        "P_proximity": [fractions["B_change"], -p_distance], "C_terrain": [fractions["B_change"], -c_distance]},
        "decision": decision, "euclidean_m": p_distance, "path_m": c_distance}


def prepare(reference, predictors, output, source_commit):
    reference, predictors, out = (Path(p).resolve() for p in [reference, predictors, output])
    out.mkdir(parents=True, exist_ok=False)
    protocol = read(PROTOCOL)
    cfg = protocol["observations"]
    reference_receipt, predictor_receipt = (read(p / "receipt.json") for p in [reference, predictors])
    if any(r["protocol_sha256"] != sha256(PROTOCOL) for r in [reference_receipt, predictor_receipt]):
        raise ValueError("Input acquisition protocol changed")
    g = metric_grid(predictor_receipt, cfg["optical_grid_m"])
    t = metric_grid(predictor_receipt, cfg["terrain_m"])
    pre, post = [optical_maps(predictors, cfg, predictor_receipt["optical"][period], g)
                 for period in ["pre", "post"]]
    common = pre["valid"] & post["valid"]
    temporal = common & post["mndwi"] & ~pre["mndwi"]
    masks = {"valid": common, "A_post": post["mndwi"], "B_change": temporal,
             "B_ndvi": temporal & ~post["ndvi_high"], "B_ndwi": temporal & post["ndwi"]}
    files = [checked_file(predictors, r["path"], r["sha256"]) for r in predictor_receipt["dem"]]
    z = warp(files, t, Resampling.bilinear)
    h = derive(z, np.isfinite(z), t, 100000, "fill")
    # Same terrain-grid source cells for proximity and route distance.
    route_support = resample_flags(common, g, t, Resampling.nearest) & h.valid
    seeds = resample_flags(temporal, g, t, Resampling.max) & route_support
    proximity = (distance_transform_edt(~seeds, sampling=t.transform.a) if seeds.any()
                 else np.full(t.shape, np.inf))
    path = downstream_distances(h, seeds, route_support)
    roads, counts = road_geometries(reference, reference_receipt, t.crs)
    rows = []
    for records in roads.values():
        filename, index, line = records[0]
        points, weights = road_points(line)
        variations = {}
        for dx, dy in SHIFTS:
            variations[f"{dx},{dy}"] = road_features(points+[dx,dy], weights, masks, g, h.valid, t, proximity, path)
        centroid = line.centroid
        rows.append({"id": f"{filename}:{index}", "members": [[f, i] for f,i,_ in records],
                     "length_m": line.length, "spatial_block": [int(centroid.x//500),int(centroid.y//500)],
                     "predictions": variations})
    counts["unique_road_geometries_ge20m"] = len(rows)
    counts["exact_duplicate_records_merged"] = sum(len(row["members"])-1 for row in rows)
    counts["nominal_common_observation_support"] = sum(
        row["predictions"]["0,0"]["scores"] is not None for row in rows)
    save_json(out / "predictions.json", rows)
    seal = {"source_commit": source_commit, "protocol_sha256": sha256(PROTOCOL),
            "reference_receipt_sha256": sha256(reference / "receipt.json"),
            "predictor_receipt_sha256": sha256(predictors / "receipt.json"),
            "predictions_sha256": sha256(out / "predictions.json"), "counts": dict(counts),
            "terrain_grid": t.describe(), "optical_grid": g.describe(), "terrain": h.summary,
            "paired_clear_optical_pixels": int(common.sum()), "new_water_pixels": int(temporal.sum()),
            "terrain_seed_cells": int(seeds.sum()), "flood_attributes_used": False}
    save_json(out / "seal.json", seal)
    print(seal["counts"], flush=True)


def binary_label(value):
    if type(value) is bool:
        return value
    if type(value) is str:
        return {"yes": True, "no": False, "true": True, "false": False}.get(value.strip().lower())
    return None


def review_metrics(rows, budget):
    n = int(len(rows)*budget)
    def order(row, method):
        p = row["predictions"]["0,0"]
        changed = method != "margin" and p["decision"]["B_change"] != p["decision"][method]
        return (not changed, abs(p["scores"]["B_change"]-.2), row["id"])
    error_ids = {r["id"] for r in rows if r["predictions"]["0,0"]["decision"]["B_change"] != r["label"]}
    result = {}
    for method in ["margin", "B_ndwi", "B_ndvi"]:
        selected = sorted(rows, key=lambda row: order(row, method))[:n]
        result[method] = {"reviewed": n, "errors": len(error_ids),
                          "captured": sum(row["id"] in error_ids for row in selected),
                          "random_expected": n*len(error_ids)/len(rows) if rows else None}
    return result


def metrics(rows, shift):
    eligible = [r for r in rows if r["predictions"][shift]["scores"] is not None]
    y = np.array([r["label"] for r in eligible], dtype=bool)
    result = {}
    for method in METHODS:
        p = [r["predictions"][shift] for r in eligible]
        score = [v["scores"][method] for v in p]
        decision = np.array([v["decision"][method] for v in p], dtype=bool)
        result[method] = {**ranking_metrics(score, y.tolist(), ks=(max(1,int(.2*len(y))),)),
                          "classification": binary_metrics(decision, y, np.ones_like(y))}
    return {"eligible": len(y), "positive": int(y.sum()), "methods": result}


def evaluate(reference, predictions, output):
    reference, predictions, out = (Path(p).resolve() for p in [reference, predictions, output])
    out.mkdir(parents=True, exist_ok=False)
    seal = read(predictions / "seal.json")
    if (seal["protocol_sha256"] != sha256(PROTOCOL)
            or seal["reference_receipt_sha256"] != sha256(reference / "receipt.json")
            or seal["predictions_sha256"] != sha256(predictions / "predictions.json")):
        raise ValueError("Seal identity changed")
    # First use of the flood attribute occurs here, after prediction sealing.
    lookup_by_file = {r["file"]: read(checked_file(reference, r["file"], r["sha256"]))["features"]
                      for r in read(reference / "receipt.json")["files"]}
    rows = []
    strict = []
    exclusions = Counter()
    for row in read(predictions / "predictions.json"):
        raw_labels = [(lookup_by_file[f][i].get("properties") or {}).get("flooded")
                      for f,i in row["members"]]
        labels = {binary_label(value) for value in raw_labels}
        known = labels-{None}
        if len(known) > 1:
            exclusions["conflicting_duplicate_labels"] += 1
            continue
        if row["predictions"]["0,0"]["scores"] is None:
            exclusions["insufficient_observation_support"] += 1
            continue
        if known:
            known_label = known.pop()
            strict.append({**row, "label": known_label})
            rows.append({**row, "label": known_label, "label_kind": "explicit"})
        elif all(value is None for value in raw_labels):
            rows.append({**row, "label": False, "label_kind": "missing_to_negative_benchmark_convention"})
        else:
            exclusions["unrecognized_flood_attribute"] += 1
    if not rows or len({r["label"] for r in rows}) != 2:
        raise ValueError("Evaluation requires eligible positives and negatives")
    stress = {f"{dx},{dy}": metrics(rows,f"{dx},{dy}") for dx,dy in SHIFTS}
    positives = [r for r in strict if r["label"]]
    strict_result = {"positive": len(positives), "negative": len(strict)-len(positives),
        "positive_hits": {method: sum(r["predictions"]["0,0"]["decision"][method] for r in positives)
                          for method in METHODS},
        "precision_and_f1_available": 0 < len(positives) < len(strict)}
    save_json(out / "rows.json", rows)
    summary = {"cohort": "Germany July 2021 same-date single Maxar scene road cohort",
        "scope": "Positive-only explicit reference and secondary agreement with SpaceNet 8 publisher binary convention",
        "counts": seal["counts"], "excluded": dict(exclusions), "spatial_blocks": len(
            {tuple(r["spatial_block"]) for r in rows}),
        "explicit_positive_only": strict_result,
        "binary_label_kinds": dict(Counter(r["label_kind"] for r in rows)),
        "label_audit_sha256": sha256(LABEL_AUDIT),
        "nominal": stress["0,0"], "registration_stress": stress,
        "review": review_metrics(rows,.2), "seal_sha256": sha256(predictions / "seal.json"),
        "rows_sha256": sha256(out / "rows.json"), "protocol_sha256": sha256(PROTOCOL)}
    save_json(out / "summary.json", summary)
    print({key: summary[key] for key in ["counts", "excluded", "spatial_blocks", "review"]},flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("prepare")
    e = commands.add_parser("evaluate")
    for sub in [p,e]:
        sub.add_argument("--reference", required=True)
        sub.add_argument("--output", required=True)
    p.add_argument("--predictors", required=True)
    p.add_argument("--source-commit", required=True)
    e.add_argument("--predictions", required=True)
    args = vars(parser.parse_args())
    action = args.pop("action")
    (prepare if action == "prepare" else evaluate)(**args)
