"""Recount saved rows independently and package reproducible drainage results."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
import zipfile
from collections import defaultdict


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def checked_repeat(first, second):
    manifest = read(first / "manifest.json")["files"]
    require(manifest == read(second / "manifest.json")["files"], "Repeat manifest differs")
    for name, expected in manifest.items():
        require(sha(first / name) == sha(second / name) == expected, name)
    return len(manifest)


def recount_regional(folder):
    result = {}
    for case, summary in read(folder / "summary.json")["cases"].items():
        rows = read(folder / case / "unit-outcomes.json")
        samples = read(folder / case / "point-comparisons.json")
        require(len(rows) == summary["units"], f"{case} unit count")
        require(sum(row["samples"] for row in rows) == len(samples) == summary["fixed_samples"],
                f"{case} sample count")
        sources = {}
        for model in ["glo30", "glo90"]:
            values = [p[model + "_merit_cosine"] for p in samples
                      if p[model + "_merit_cosine"] is not None]
            counterpart = summary[model + "_merit"]
            counts = {
                "paired_samples": len(values),
                "at_least_90deg": sum(c <= 1e-12 for c in values),
                "over_45deg": sum(math.degrees(math.acos(c)) > 45 + 1e-9 for c in values),
                "over_1deg": sum(math.degrees(math.acos(c)) > 1 + 1e-9 for c in values),
            }
            require(all(counterpart[key] == value for key, value in counts.items()), f"{case} {model}")
            sources[model] = counts
        pairs = [row for row in rows if row["source_disagreement"] is not None]
        require(len(pairs) == summary["orientable_unit_pairs"], f"{case} orientable units")
        require(sum(row["glo30_orientation"] != row["merit_orientation"] for row in pairs)
                == summary["opposite_majority_unit_orientations"], f"{case} orientation comparison")
        table = {f"warning_{w}_comparator_disagree_{d}": sum(
            row["water_warning"] is w and row["source_disagreement"] is d for row in pairs)
            for w in [True, False] for d in [True, False]}
        require(table == summary["water_warning_comparator_contingency"], f"{case} warning association")
        result[case] = {"units": len(rows), "fixed_samples": len(samples),
                        "paired_sources": sources, "orientable_units": len(pairs),
                        "warning_association": table}
    return result


def angular_error(prediction, observed):
    px, py = prediction
    ox, oy = observed
    return math.degrees(math.atan2(abs(px * oy - py * ox), px * ox + py * oy))


def physical_recount(folder):
    blocks = read(folder / "blocks.json")
    summary = read(folder / "summary.json")
    require(len(blocks) == summary["coverage"]["eligible_blocks"], "Reference block count")
    models = sorted(blocks[0]["predictions"])
    totals = {}
    for model in models:
        combined = []
        for year, expected in summary["survey_years"].items():
            units = [b for b in blocks if str(b["year"]) == year]
            common = [b for b in units if all(b["predictions"][m]["vector"] is not None for m in models)]
            require(len(units) == expected["eligible_blocks"], f"{year} reference support")
            require(len(common) == expected["common_blocks_all_sources"], f"{year} common support")
            for group, key in [(units, "own_support"), (common, "matched_support")]:
                errors = []
                for block in group:
                    prediction = block["predictions"][model]
                    if prediction["vector"] is None:
                        continue
                    angle = angular_error(prediction["vector"], block["reference_vector"])
                    require(abs(angle - prediction["angle_deg"]) < 1e-6, "Stored direction error")
                    errors.append(angle)
                recorded = expected[key][model]
                require(len(errors) == recorded["available"], f"{year} {model} coverage")
                require(sum(a < 90 - 1e-9 for a in errors) == recorded["positive_cosine"],
                        f"{year} {model} hemisphere count")
                require(sum(a <= 45 + 1e-9 for a in errors) == recorded["at_most45deg"],
                        f"{year} {model} 45-degree count")
                if errors:
                    require(abs(median(errors) - recorded["median_angle_deg"]) < 1e-6,
                            f"{year} {model} median")
                if key == "own_support":
                    combined.extend(errors)
        totals[model] = {"eligible_blocks": len(blocks), "available": len(combined),
                         "positive_cosine": sum(a < 90 - 1e-9 for a in combined),
                         "at_most45deg": sum(a <= 45 + 1e-9 for a in combined),
                         "median_angle_deg": median(combined)}
    require(len({b["id"] for b in blocks}) == len(blocks), "Duplicate reference block")
    return totals


def verify_reference(archive, expected_sha, block_file):
    require(sha(archive) == expected_sha, "Observed archive identity")
    bins = defaultdict(list)
    all_rows = speed_eligible = 0
    with zipfile.ZipFile(archive) as package:
        catalog = json.loads(package.read("ro-crate-metadata.json"))
        rows = [entry for entry in catalog["@graph"] if entry["@id"].endswith(".csv")]
        require(len(rows) == 50, "Expected 50 published source records")
        count = 0
        for entry in rows:
            raw = package.read(entry["@id"])
            require(len(raw) == entry["bytes"] and digest(raw) == entry["sha256"], entry["@id"])
            count += len(raw)
            year = int(entry["@id"].split("_")[1])
            for line_no, row in enumerate(csv.reader(io.StringIO(raw.decode("utf-8-sig")))):
                if not row or not any(row):
                    continue
                try:
                    x, y, _, u, v = map(float, row)
                except ValueError:
                    if line_no:
                        raise
                    continue
                all_rows += 1
                points = bins[year, math.floor(x/180), math.floor(y/180)]
                speed = math.hypot(u, v)
                if math.isfinite(speed) and speed >= 0.1:
                    points.append((x, y, u, v, speed))
                    speed_eligible += 1
    records = {b["id"]: b for b in read(block_file)}
    eligible = 0
    for key, points in bins.items():
        uid = ":".join(map(str, key))
        coherence = (math.hypot(sum(u/s for x, y, u, v, s in points),
                                sum(v/s for x, y, u, v, s in points))/len(points)
                     if points else 0)
        if len(points) < 5 or coherence < 0.75:
            require(uid not in records, "Excluded tile appeared in result")
            continue
        eligible += 1
        record = records[uid]
        means = [sum(col)/len(points) for col in list(zip(*points))[:4]]
        require(record["points"] == len(points), "Reference block point count")
        require(math.isclose(record["coherence"], coherence, abs_tol=1e-9), "Reference coherence")
        require(all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(
            record["location"] + record["reference_vector"], means)), "Reference means")
    require(eligible == len(records), "Reconstructed reference block count")
    return {"published_csv_hashes_matched": len(rows), "uncompressed_csv_bytes": count,
            "rows_recounted": all_rows, "speed_eligible_rows_recounted": speed_eligible,
            "reference_tiles_reconstructed": len(bins), "eligible_blocks_reconstructed": eligible,
            "archive_sha256": expected_sha}


def run(root, data, out):
    root, data, out = map(Path, (root, data, out))
    regional = root / "merit-comparison-3"
    observed = root / "observed-control-1"
    regional_summary = read(regional / "summary.json")
    observed_summary = read(observed / "summary.json")
    acquisition = data / "merit-attempt-4" / "acquisition.json"
    require(sha(acquisition) == regional_summary["acquisition_sha256"], "Regional acquisition identity")
    out.mkdir(parents=True, exist_ok=False)
    audit = {
        "same_input_repeat_identical_files": {
            "regional": checked_repeat(regional, root / "merit-comparison-repeat"),
            "observed": checked_repeat(observed, root / "observed-control-repeat"),
        },
        "regional_recount": recount_regional(regional),
        "observed_pooled_descriptive_recount": physical_recount(observed),
        "reference_identity": verify_reference(
            data / "saskatchewan-attempt-1" / "sealed-observations.zip",
            observed_summary["reference_archive_sha256"], observed / "blocks.json"),
        "measurement_source_commit": observed_summary["source_commit"],
    }
    for actual, recorded in [
        ("rows_recounted", "all_rows"), ("speed_eligible_rows_recounted", "speed_eligible_rows"),
        ("reference_tiles_reconstructed", "all_year_spatial_tiles"),
        ("eligible_blocks_reconstructed", "eligible_blocks"),
    ]:
        require(audit["reference_identity"][actual] == observed_summary["coverage"][recorded], recorded)
    receipts = {
        "merit-regional": acquisition,
        "observations": data / "saskatchewan-attempt-1" / "acquisition.json",
        "observed-geometry": root / "geometry-1" / "geometry.json",
        "observed-dem": data / "saskatchewan-inputs-4" / "dem-acquisition.json",
        "observed-merit": data / "saskatchewan-inputs-4" / "merit-acquisition.json",
        "observed-predictors": root / "predictors-1" / "prediction-seal.json",
        "regional-run-manifest": regional / "manifest.json",
        "observed-run-manifest": observed / "manifest.json",
    }
    for name, path in receipts.items():
        if name == "observed-predictors":
            redacted = read(path)
            redacted["merit_file"] = Path(redacted["merit_file"]).name
            redacted["original_receipt_sha256"] = sha(path)
            write(out / (name + ".json"), redacted)
        else:
            (out / (name + ".json")).write_bytes(path.read_bytes())
    for tag, folder, files in [
        ("regional", regional, ["summary", "registration-stress"]),
        ("observed", observed, ["summary", "registration-heading-stress", "point-diagnostic"]),
    ]:
        for name in files:
            (out / f"{tag}-{name}.json").write_bytes((folder / (name + ".json")).read_bytes())
    write(out / "verification.json", audit)
    with (out / "observed-by-year.csv").open("w", encoding="utf-8", newline="") as stream:
        fieldnames = ["year", "support", "model", "reference_units", "available", "unavailable",
                      "positive_cosine", "at_most45deg", "median_angle_deg", "p90_angle_deg"]
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for year, row in observed_summary["survey_years"].items():
            for support in ["own_support", "matched_support"]:
                for model, values in row[support].items():
                    writer.writerow({"year": year, "support": support, "model": model, **values})
    write(out / "manifest.json", {"files": {f.name: sha(f) for f in sorted(out.iterdir())}})
    print(json.dumps({k: v for k, v in audit.items() if k != "regional_recount"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ["run-root", "data-root", "output"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    run(args.run_root, args.data_root, args.output)
