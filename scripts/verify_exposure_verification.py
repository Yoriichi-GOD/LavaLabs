"""Recount the sealed experiments and export their compact paper evidence."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
from itertools import groupby
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
import requests


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n",
                    encoding="utf-8", newline="\n")


def require(ok, name):
    if not ok:
        raise ValueError(f"Verification failed for {name}")


def water_recount(run, predictions, references, replay=None):
    summary = read(run / "summary.json")
    seal_path = predictions / "prediction-seal.json"
    require(sha(seal_path) == summary["prediction_seal_sha256"], "water prediction seal")
    seal = {r["id"]: r for r in read(seal_path)["records"]}
    if replay:
        repeat = read(replay / "summary.json")
        require(repeat.pop("replay") is True, "replay status")
        require(repeat == {k:v for k,v in summary.items() if k != "replay"}, "replayed water metrics")
    totals = {budget: Counter() for budget in summary["totals"]}
    boxes = {}
    for identity, recorded in summary["events"].items():
        pred_path = predictions / identity / "predictions.npz"
        ref_path = references / identity / "reference.tif"
        require(sha(pred_path) == seal[identity]["prediction_sha256"], identity+" prediction")
        require(sha(ref_path) == recorded["reference_sha256"], identity+" reference")
        with rasterio.open(ref_path) as src:
            qa, label = src.read()
            boxes[identity] = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)
        with np.load(pred_path, allow_pickle=False) as p:
            support = (p["valid"] & (qa == 1) & ((label == 1) | (label == 2)))
            water, margin = p["water"][support], p["margin"][support]
            ndwi, ndvi = p["ndwi_conflict"][support], p["ndvi_conflict"][support]
        truth = label[support] == 2
        wrong = water ^ truth
        require(len(wrong) == recorded["common_pixels"], identity+" common support")
        require(int(wrong.sum()) == recorded["baseline_errors"], identity+" errors")
        flags = {"margin": np.zeros(len(wrong), bool), "ndvi": ndvi, "ndwi": ndwi, "either": ndvi|ndwi}
        for name, flag in flags.items():
            # Independent stable partition of one margin sort. Tie order is original cell order.
            order = np.argsort(margin, kind="stable")
            ranked = np.concatenate([order[flag[order]], order[~flag[order]]])
            for budget, counts in recorded["review"].items():
                top = ranked[:int(float(budget)*len(wrong))]
                captured_fp = np.count_nonzero(wrong[top] & water[top])
                captured_fn = np.count_nonzero(wrong[top] & ~water[top])
                require(counts[name]["reviewed"] == len(top), identity+" review size")
                require(counts[name]["captured_false_positive"] == captured_fp, identity+" captured FP")
                require(counts[name]["captured_false_negative"] == captured_fn, identity+" captured FN")
                require(counts[name]["captured"] == captured_fp+captured_fn, identity+" captured errors")
                totals[budget][name] += int(captured_fp+captured_fn)
        for name, pred in {"mndwi": water, "mndwi_ndvi": water&~ndvi,
                           "mndwi_ndwi": water&~ndwi, "mndwi_both": water&~ndvi&~ndwi}.items():
            tn, fn, fp, tp = np.bincount(2*pred.astype(int)+truth.astype(int), minlength=4)
            counts = dict(tp=int(tp), fp=int(fp), fn=int(fn), tn=int(tn))
            require(all(recorded["hard_filter"][name][k] == v for k,v in counts.items()),
                    identity+" hard filters")
    for budget, counts in totals.items():
        require(all(summary["totals"][budget][method]["captured"] == n for method,n in counts.items()),
                "pooled review counts")
    return dict(totals), boxes


def average_precision(rows, method):
    def key(row):
        v = row["predictions"]["0,0"]["scores"][method]
        return tuple(v) if isinstance(v,list) else (v,)
    ordered = sorted(rows,key=key,reverse=True)
    positives = sum(r["label"] for r in rows)
    count = hit = 0
    ap = 0.
    for _, group in groupby(ordered, key):
        units = list(group)
        count += len(units)
        delta = sum(r["label"] for r in units)
        hit += delta
        ap += delta * hit / (count * positives)
    return ap


def road_recount(root):
    source = root / "ahr-reference-1"
    pred = root / "ahr-sealed-1"
    run = root / "ahr-results-2"
    replay = root / "ahr-results-replay"
    summary = read(run / "summary.json")
    require(sha(run / "rows.json") == summary["rows_sha256"], "road metric rows")
    require(sha(pred / "seal.json") == summary["seal_sha256"], "road prediction seal")
    require(sha(pred / "predictions.json") == read(pred / "seal.json")["predictions_sha256"], "road predictions")
    for name in ["summary.json","rows.json"]:
        require(sha(run/name) == sha(replay/name), "replayed road "+name)
    rows = read(run / "rows.json")
    support = Counter()
    actual = {}
    for item in read(source / "receipt.json")["files"]:
        path = source / item["file"]
        require(sha(path) == item["sha256"], item["file"]+" reference hash")
        actual[item["file"]] = read(path)["features"]
    for row in read(pred / "predictions.json"):
        yes = {actual[f][i]["properties"].get("flooded") for f,i in row["members"]}
        require(yes in [{"yes"}, {None}], "audited source attribute domain")
        support["positive_total" if "yes" in yes else "blank_total"] += 1
        if row["predictions"]["0,0"]["scores"] is not None:
            support["positive_eligible" if "yes" in yes else "blank_eligible"] += 1
    for row in rows:
        label = {actual[f][i]["properties"].get("flooded") for f,i in row["members"]}
        require(row["label"] == ("yes" in label), "road source-label join")
    for method, measured in summary["nominal"]["methods"].items():
        counts = Counter()
        for row in rows:
            prediction = row["predictions"]["0,0"]["decision"][method]
            counts["tp" if row["label"] and prediction else "fn" if row["label"]
                   else "fp" if prediction else "tn"] += 1
        require(all(measured["classification"][k] == counts[k] for k in ["tp","fp","fn","tn"]), method+" road counts")
        require(abs(average_precision(rows,method)-measured["average_precision"]) < 1e-12, method+" AP")
        require(summary["explicit_positive_only"]["positive_hits"][method] == counts["tp"],
                method+" explicit positive hits")
    return {"source_tile_hashes_verified": len(actual), "support": dict(support),
            "road_labels_recounted": len(rows), "road_replay_byte_identical": True}


def audit_dates(identities, protocol):
    rows = []
    for identity in identities:
        url = (f"https://huggingface.co/datasets/{protocol['dataset']}/resolve/{protocol['revision']}"
               f"/test/meta/{identity}.json")
        try:
            response = requests.get(url, timeout=(10,30))
            response.raise_for_status()
            if len(response.content)>512*1024:
                raise ValueError("metadata cap")
            meta = response.json()
            optical, reference = meta.get("s2_date"), meta.get("satellite date")
            lag = None if not optical or not reference else (
                datetime.fromisoformat(optical.replace("Z","+00:00")) -
                datetime.fromisoformat(reference.replace("Z","+00:00"))).total_seconds()/86400
            rows.append({"id":identity,"optical_date":optical,"reference_date":reference,"days":lag,
                         "reference_sensor":meta.get("satellite"),"metadata_url":url,
                         "metadata_sha256":hashlib.sha256(response.content).hexdigest()})
        except (requests.RequestException, ValueError) as error:
            rows.append({"id":identity,"status":"unavailable","reason":type(error).__name__,"metadata_url":url})
    return rows


def overlap(a,b):
    return min(a[2],b[2]) > max(a[0],b[0]) and min(a[3],b[3]) > max(a[1],b[1])


def run(root, dev, output):
    root, dev, out = map(Path,(root, dev, output))
    out.mkdir(parents=True, exist_ok=False)
    dev_run, hold_run = root/"spectral-dev-results-v2", root/"spectral-reserve-results"
    dev_metrics, dev_bounds = water_recount(dev_run,root/"spectral-dev-predictions",dev)
    held_metrics, held_bounds = water_recount(hold_run,root/"spectral-reserve-predictions",hold_run,
                                            root/"spectral-reserve-replay")
    road = road_recount(root)
    protocol = read(Path(__file__).resolve().parents[1]/"research/experiments/spectral-review-20261112.json")
    date_records = audit_dates(held_bounds,protocol)
    audit = {"status":"PASS","road":road,"development_review_recount":dev_metrics,
             "reserve_review_recount":held_metrics,"reserve_replay_exact_metrics":True,
             "dev_reserve_bbox_overlap":[[a,b] for a,x in dev_bounds.items() for b,y in held_bounds.items() if overlap(x,y)],
             "water_bounds_wgs84":{"development":dev_bounds,"reserve":held_bounds},
             "reserve_reference_date_audit":date_records,
             "reserve_disposition":"All four listed windows consumed in first verification; subsequent accesses are replays"}
    copies = {
        "spectral-development":dev_run/"summary.json", "spectral-reserve":hold_run/"summary.json",
        "spectral-development-seal":root/"spectral-dev-predictions"/"prediction-seal.json",
        "spectral-reserve-seal":root/"spectral-reserve-predictions"/"prediction-seal.json",
        "ahr-results":root/"ahr-results-2"/"summary.json", "ahr-seal":root/"ahr-sealed-1"/"seal.json",
        "ahr-reference-receipt":root/"ahr-reference-1"/"receipt.json",
        "ahr-input-receipt":root/"ahr-predictor-2"/"receipt.json",
    }
    for name, path in copies.items():
        (out/(name+".json")).write_bytes(path.read_bytes())
    write(out/"verification.json",audit)
    write(out/"manifest.json",{"files":{f.name:sha(f) for f in sorted(out.iterdir())}})
    print(json.dumps({"road":road,"held_review":held_metrics,
        "dev_reserve_overlap":audit["dev_reserve_bbox_overlap"],"date_audit":date_records},indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for option in ["run-root","dev-root","output"]:
        p.add_argument("--"+option,required=True)
    a = p.parse_args()
    run(a.run_root,a.dev_root,a.output)
