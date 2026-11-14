"""Compare fixed-budget spectral error triage against a simple margin baseline."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from research.experiments.worldfloods_component import remote_window, confusion, ratios
from research.terrain_exposure.io import Grid, save_json, sha256


HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "spectral-review-20261112.json"
DEV = HERE / "worldfloods-blind-20261107.json"
RESERVE = HERE / "worldfloods-reserve-20261107.json"
REVIEW_METHODS = ("margin", "ndwi", "ndvi", "either")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def grid(src):
    return Grid(src.shape, src.transform, src.crs.to_string())


def asset(protocol, identity, role):
    return (f"https://huggingface.co/datasets/{protocol['dataset']}/resolve/"
            f"{protocol['revision']}/test/{role}/{identity}.tif")


def features(data):
    green, red, nir, swir = np.asarray(data, dtype=float)
    valid = np.isfinite(data).all(0) & (data > 0).all(0)
    def index(a, b):
        return np.divide(a-b, a+b, out=np.zeros(a.shape), where=valid)
    mndwi, ndwi, ndvi = index(green, swir), index(green, nir), index(nir, red)
    water = mndwi > 0
    return {"valid": valid, "water": water, "margin": abs(mndwi),
            "ndwi_conflict": water != (ndwi > 0),
            "ndvi_conflict": water & (ndvi > .2)}


def prepare_one(identity, output, dev_root, protocol):
    folder = output / identity
    folder.mkdir()
    if dev_root:
        retained = dev_root / identity
        input_path = retained / "input.tif"
        receipt = read(retained / "input.source.json")
        if sha256(input_path) != receipt["sha256"] or receipt["selected_bands"] != [3, 8, 12]:
            raise ValueError("Retained input identity changed")
        with rasterio.open(input_path) as source:
            green, nir, swir = source.read()
            expected = grid(source)
        window = Window(*receipt["window"])
        red, source_grid, _ = remote_window(asset(protocol, identity, "S2"),
            folder / "red.tif", [4], window, expected)
        data = np.stack([green, red[0], nir, swir])
        input_hashes = [receipt["sha256"], sha256(folder / "red.tif")]
    else:
        data, source_grid, window = remote_window(asset(protocol, identity, "S2"),
            folder / "input.tif", [3, 4, 8, 12])
        input_hashes = [sha256(folder / "input.tif")]
    prediction = folder / "predictions.npz"
    np.savez_compressed(prediction, **features(data))
    return {"id": identity, "status": "PREDICTIONS_SEALED", "window": list(window.flatten()),
            "grid": source_grid.describe(), "input_sha256": input_hashes,
            "prediction_sha256": sha256(prediction)}


def prepare(output, dev_root=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    dev_root = Path(dev_root).resolve() if dev_root else None
    protocol = read(PROTOCOL)
    identities = read(DEV if dev_root else RESERVE)["ids"]
    save_json(output / "population.json", {"ids": identities, "protocol_sha256": sha256(PROTOCOL),
        "population": "DEVELOPMENT_REPLAY" if dev_root else "RESERVE_FIRST_EVALUATION"})
    def job(identity):
        try:
            result = prepare_one(identity, output, dev_root, protocol)
        except Exception as error:
            result = {"id": identity, "status": "INPUT_FAILED",
                      "reason": f"{type(error).__name__}: {error}"[:300]}
        print(json.dumps({"id": identity, "status": result["status"]}), flush=True)
        return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(job, identities))
    save_json(output / "prediction-seal.json", {"records": records, "protocol_sha256": sha256(PROTOCOL),
        "population_sha256": sha256(output / "population.json"), "reference_pixels_read": False})


def review_counts(selected, mistakes, water):
    reviewed = len(selected)
    captured = int(mistakes[selected].sum())
    errors = int(mistakes.sum())
    return {"observations": len(mistakes), "reviewed": reviewed, "errors": errors, "captured": captured,
            "missed": errors - captured, "captured_false_positive": int((mistakes[selected] & water[selected]).sum()),
            "captured_false_negative": int((mistakes[selected] & ~water[selected]).sum()),
            "random_expected_captured": reviewed * errors / len(mistakes) if len(mistakes) else 0.0}


def review_metrics(counts):
    div = lambda a, b: a/b if b else None
    return {**counts, "review_precision": div(counts["captured"], counts["reviewed"]),
            "error_recall": div(counts["captured"], counts["errors"]),
            "unreviewed_error_rate": div(counts["missed"], counts["observations"]-counts["reviewed"])}


def score(prediction, label, protocol):
    valid = prediction["valid"] & (label[0] == 1) & np.isin(label[1], [1, 2])
    truth = (label[1] == 2)[valid]
    water = prediction["water"][valid]
    margin = prediction["margin"][valid]
    ndwi = prediction["ndwi_conflict"][valid]
    ndvi = prediction["ndvi_conflict"][valid]
    errors = water != truth
    prioritization = {"margin": np.zeros_like(water), "ndwi": ndwi, "ndvi": ndvi, "either": ndwi | ndvi}
    ranks = {name: np.lexsort((np.arange(len(margin)), margin, ~flag)) for name, flag in prioritization.items()}
    review = {}
    for budget in protocol["review_budget_fractions"]:
        n = int(len(margin)*budget)
        review[str(budget)] = {name: review_metrics(review_counts(order[:n], errors, water))
                              for name, order in ranks.items()}
    hard = {"mndwi": water, "mndwi_ndwi": water & ~ndwi, "mndwi_ndvi": water & ~ndvi,
            "mndwi_both": water & ~ndwi & ~ndvi}
    return {"common_pixels": len(water), "baseline_errors": int(errors.sum()),
            "review": review, "hard_filter": {name: ratios(confusion(p, truth, np.ones_like(truth)))
                for name, p in hard.items()}}


def evaluate(predictions, output, dev_root=None, reference_root=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    predictions = Path(predictions).resolve()
    protocol = read(PROTOCOL)
    population = read(predictions / "population.json")
    seal_file = predictions / "prediction-seal.json"
    seal = read(seal_file)
    if (seal["protocol_sha256"] != sha256(PROTOCOL)
            or seal["population_sha256"] != sha256(predictions / "population.json")
            or [record["id"] for record in seal["records"]] != population["ids"]):
        raise ValueError("Frozen protocol or population identity mismatch")
    events, failures = {}, []
    for record in seal["records"]:
        identity = record["id"]
        if record["status"] != "PREDICTIONS_SEALED":
            failures.append(record)
            continue
        folder = output / identity
        folder.mkdir()
        try:
            pred_file = predictions / identity / "predictions.npz"
            if sha256(pred_file) != record["prediction_sha256"]:
                raise ValueError("Prediction identity mismatch")
            expected = record["grid"]
            if dev_root or reference_root:
                ref = Path(dev_root or reference_root).resolve() / identity / "reference.tif"
                receipt = read(ref.with_suffix(".source.json"))
                if sha256(ref) != receipt["sha256"]:
                    raise ValueError("Retained reference identity mismatch")
                with rasterio.open(ref) as src:
                    if grid(src).describe() != expected:
                        raise ValueError("Reference grid mismatch")
                    label = src.read()
            else:
                ref = folder / "reference.tif"
                label, actual, _ = remote_window(asset(protocol, identity, "gt"), ref, [1, 2],
                    Window(*record["window"]))
                if actual.describe() != expected:
                    raise ValueError("Reference grid mismatch")
            if label.shape[0] != 2 or not np.isin(label, [0, 1, 2]).all():
                raise ValueError("Unexpected reference schema")
            with np.load(pred_file, allow_pickle=False) as data:
                result = score(data, label, protocol)
            result["reference_sha256"] = sha256(ref)
            events[identity] = result
            save_json(folder / "metrics.json", result)
            print(json.dumps({"id": identity, "status": "SCORED",
                "common_pixels": result["common_pixels"], "errors": result["baseline_errors"]}), flush=True)
        except Exception as error:
            failures.append({"id": identity, "status": "SCORING_FAILED",
                             "reason": f"{type(error).__name__}: {error}"[:300]})
    fields = ["observations", "reviewed", "errors", "captured", "missed", "captured_false_positive",
              "captured_false_negative", "random_expected_captured"]
    totals = {str(f): {method: review_metrics({
        key: sum(row["review"][str(f)][method][key] for row in events.values()) for key in fields
    }) for method in REVIEW_METHODS} for f in protocol["review_budget_fractions"]}
    hard = {method: ratios({key: sum(row["hard_filter"][method][key] for row in events.values())
                            for key in ["tp", "fp", "fn", "tn"]})
            for method in ["mndwi", "mndwi_ndwi", "mndwi_ndvi", "mndwi_both"]}
    save_json(output / "summary.json", {"population": population["population"],
        "selected": len(population["ids"]), "scored": len(events), "events": events, "failures": failures,
        "totals": totals, "hard_filter_totals": hard, "prediction_seal_sha256": sha256(seal_file),
        "protocol_sha256": sha256(PROTOCOL), "replay": bool(reference_root)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--output", required=True)
    p.add_argument("--dev-root")
    p = commands.add_parser("evaluate")
    p.add_argument("--output", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--dev-root")
    p.add_argument("--reference-root")
    args = vars(parser.parse_args())
    action = args.pop("command")
    (prepare if action == "prepare" else evaluate)(**args)
