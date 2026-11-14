"""Reproduce the bounded final R3 evaluation from the preserved inputs."""
import argparse
from collections import Counter
import csv
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path

from policy import Reference, angle, assess, direction_predict


HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
WORKSPACE = FINAL.parents[4]
ARMS = tuple("ABCDEFG")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+"\n",
                    encoding="utf-8", newline="\n")


def csv_file(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check_manifest(root, manifest, field):
    entries = read(manifest)[field]
    for name, digest in entries.items():
        if sha(root/name) != digest:
            raise ValueError(f"Frozen artifact changed: {root/name}")
    return len(entries)


def road_replay(roads, spec):
    rules = spec["ahr"]
    expected = {"cohort": 199, "queue": 60, "nominal": 23, "strict": rules["strict_expected_paths"]}
    selected = {k: r for k,r in roads["predictions"].items() if r["proximity"]}
    if len(roads["predictions"]) != expected["cohort"] or len(selected) != expected["queue"]:
        raise ValueError("Frozen road support or queue size changed")
    typed = {}
    for k, r in selected.items():
        required = [r["worlds"][name] for name in rules["required_variants"] if name in r["worlds"]]
        original = r["claims"]
        observed = original["OBSERVED_CHANGE"]["eligible"]
        geo = original["GEOMETRIC_SCREENING_CANDIDATE"]["eligible"]
        nominal = bool(r["nominal_route_coordinates"])
        strict = original["MODELED_TERRAIN_PATHWAY"]["eligible"]
        if nominal and len(required) != len(rules["required_variants"]):
            raise ValueError("Required world is absent from the original witness packet")
        new = assess(observed=observed, geometric=geo, nominal=nominal, strict=strict,
                     sensitive=any(not x["passed"] and x["reason"] != "INSUFFICIENT_OBSERVATION_SUPPORT"
                                   for x in required),
                     auxiliary_missing=any(x["reason"] == "INSUFFICIENT_OBSERVATION_SUPPORT" for x in required),
                     scale_unresolved=True)
        typed[k] = {
            "candidate_id": k, "original_priority": r["sealed_rank"], "retained": True,
            "nominal": nominal, "strict": strict, "observed": observed, "geometric": geo,
            "input_checks": original,
            "dependencies": ["shared_pre_post_Sentinel_2_pair", "shared_Copernicus_DSM",
                             "frozen_SpaceNet_road_geometry"],
            "nominal_path_coordinates_utm32n": r["nominal_route_coordinates"],
            "sensitivity": r["worlds"], **new,
        }
    if sum(r["nominal"] for r in typed.values()) != expected["nominal"] or sum(
            r["strict"] for r in typed.values()) != expected["strict"]:
        raise ValueError("Frozen modeled-claim denominators differ")
    return typed


def road_metrics(typed, source):
    labels = {r["id"]:r["label"] for r in source}
    positives = sum(labels.values())
    if len(labels) != 199 or positives != 44 or sum(labels[k] for k in typed) != 38:
        raise ValueError("Ahr label join did not reproduce original endpoint recall")
    choices = {
        "A": lambda r:r["nominal"], "B": lambda r:r["strict"],
        "C": lambda r:r["observed"] and r["nominal"], "D": lambda r:r["observed"] and r["nominal"],
        "E": lambda r:r["modeled_scope"] is not None, "F":lambda r:False,
    }
    rows = []
    for arm in ARMS:
        selector = choices.get(arm)
        issues = [k for k,r in typed.items() if selector(r)] if selector else []
        rows.append({"population":"Ahr fixed proximity queue","arm":arm,"queue":60,"known_endpoints":38,
                     "endpoint_reference_positives":positives,"modeled_issued":len(issues) if selector else None,
                     "modeled_coverage":len(issues)/60 if selector else None,
                     "known_positive_endpoints_with_model":sum(labels[k] for k in issues) if selector else None,
                     "physical_exposure_issued":0 if selector else None,
                     "physical_traversal_issued":0 if selector else None,"physical_traversal_truth":0,
                     "conditional_physical_error":None,
                     "reason":"NO_ENSEMBLE_BASELINE_FOR_THIS_TARGET" if not selector
                              else "NO_MATCHED_INDEPENDENT_TRAVERSAL_REFERENCE"})
    return rows


def rank_stats(rows, good, budget, key):
    if len(rows) < budget:
        return None
    remaining = budget
    expected = low = high = 0
    for _, tied in groupby(sorted(rows, key=key, reverse=True), key=key):
        tied = list(tied)
        take = min(remaining,len(tied))
        hits = sum(good[r["id"]] for r in tied)
        expected += take*hits/len(tied)
        low += max(0,take-len(tied)+hits)
        high += min(take,hits)
        remaining -= take
        if remaining == 0:
            break
    return expected,low,high


def direction_scores(predictions, good, budgets):
    rows = [r for r in predictions if r["id"] in good]
    n, positives = len(rows), sum(good.values())
    nominal = [r for r in rows if r["nominal"] is not None]
    if len(nominal) != n:
        raise ValueError("Report is defined on common nominal/reference eligibility")
    strict = [r for r in nominal if r["strict"]]
    pools = {"A":nominal,"B":strict,"C":nominal,"D":nominal,"E":nominal,"F":[],"G":nominal}
    key = {arm: (lambda r:0) for arm in ARMS}
    key.update(E=lambda r:r["e_tier"], G=lambda r:tuple(r["g_key"]))
    baseline = positives
    output = []
    for arm in ARMS:
        cuts = [("native",len(pools[arm]))] if arm != "G" else []
        cuts += [("matched",budget) for budget in budgets]
        for mode,k in cuts:
            result = rank_stats(pools[arm],good,k,key[arm])
            hit,low,high = result if result is not None else (None,None,None)
            output.append({
                "mode":mode,"arm":arm,"eligible":n,"nominal_correct":baseline,"requested_issued":k,
                "issued":k if result is not None else None,"feasible":result is not None,
                "coverage":k/n if result is not None else None,"correct_retained":hit,
                "correct_min":low,"correct_max":high,"incorrect_issued":k-hit if hit is not None else None,
                "incorrect_rejected":n-baseline-k+hit if hit is not None else None,
                "false_rejected":baseline-hit if hit is not None else None,
                "conditional_error":(k-hit)/k if hit is not None and k else None,
                "conditional_error_min":(k-high)/k if high is not None and k else None,
                "conditional_error_max":(k-low)/k if low is not None and k else None,
            })
    strata = []
    for tier, label in [(2,"complete_and_compatible"), (1,"complete_and_discordant"),
                        (0,"auxiliary_variant_unavailable")]:
        group = [r for r in rows if r["e_tier"] == tier]
        hits = sum(good[r["id"]] for r in group)
        strata.append({"evidence_stratum":label,"units":len(group),"within_45":hits,
                       "over_45":len(group)-hits,"agreement":hits/len(group) if group else None})
    reasons = []
    for category, key in (("alternate_missing","missing"),("alternate_discordant","discordant")):
        for variant,count in sorted(Counter(v for r in rows for v in r[key]).items()):
            reasons.append({"category":category,"variant":variant,"count":count})
    return output,strata,reasons


def fixtures(spec):
    rows=[]
    for f in spec["cases"]:
        refs = [Reference(**record) for record in f["references"]]
        result = assess(**(spec["base"]|f["change"]),references=refs)
        e,t = (result["physical_targets"][name] for name in ("endpoint_exposure","source_to_endpoint_traversal"))
        actual = [result["model_state"],result["modeled_scope"],e["qualified"],t["qualified"],
                  e["state"],t["state"],result["scale_state"]]
        if actual != f["expected"]:
            raise ValueError(f"Fixture {f['name']}: {actual} != {f['expected']}")
        rows.append({"case":f["name"],"expected":f["expected"],"actual":actual,"passed":True,**result})
    return rows


def main(workspace, output):
    folders = {name:output/name for name in ("tables","experiments/evidence_discrimination",
                                            "experiments/baseline_comparisons","experiments/validation")}
    for directory in folders.values():
        directory.mkdir(parents=True,exist_ok=True)
    tables, pred, base, validation = folders.values()
    if (pred/"PREDICTION_SEAL.json").exists():
        raise ValueError("Use a fresh output path for scoring")
    cfg = read(HERE/"PROTOCOL.json")
    pilot = workspace/"cegs-novelty-20261112"
    repo = workspace/"exposure-verification-20261112/repo"
    drainage = workspace/"drainage-validation-20261112/repo"
    old = repo/"research/manuscripts/researcher-3-revision"
    compact = repo/"research/results/exposure-verification-20261112/verified"
    canadian = drainage/"research/results/drainage-validation-20261112/verified"
    integrity = {
        "V2_files":check_manifest(old,old/"evidence/PACKAGE_MANIFEST.json","artifact_sha256"),
        "CEGS_files":check_manifest(pilot,pilot/"PACKAGE_MANIFEST.json","files"),
        "exposure_compact":check_manifest(compact,compact/"manifest.json","files"),
        "drainage_compact":check_manifest(canadian,canadian/"manifest.json","files"),
    }
    ahr = pilot/"measurements/pilot/ahr_claim_predictions.json"
    if sha(ahr) != read(pilot/"measurements/pilot/pilot_seal.json")["claim_predictions_sha256"]:
        raise ValueError("Ahr prediction seal invalid")
    typed = road_replay(read(ahr),cfg)
    dump(pred/"AHR_CLAIMS.json",typed)

    data = drainage/".runtime/drainage-validation/observed-control-1/blocks.json"
    if sha(data) != read(canadian/"observed-run-manifest.json")["files"]["blocks.json"]:
        raise ValueError("Canadian block file no longer matches the frozen result")
    # The source already contains consumed scores. The ranking code receives only IDs
    # and vectors. Scoring never alters the separately written prediction artifact.
    frozen = read(data)
    if len(frozen)!=42 or len({r["id"] for r in frozen})!=42:
        raise ValueError("Unexpected ADCP support")
    directions = [{"id":r["id"],"year":r["year"],**direction_predict(
        {name:v["vector"] for name,v in r["predictions"].items()},cfg["direction"])} for r in frozen]
    dump(pred/"ADCP_DIRECTION_RANKINGS.json",directions)
    seal = {"protocol_sha256":sha(HERE/"PROTOCOL.json"),"fixture_sha256":sha(HERE/"FIXTURES.json"),
            "road_claims_sha256":sha(pred/"AHR_CLAIMS.json"),
            "direction_rankings_sha256":sha(pred/"ADCP_DIRECTION_RANKINGS.json"),
            "input_ahr_sha256":sha(ahr),"input_adcp_sha256":sha(data),"source_integrity":integrity,
            "code":{name:sha(HERE/name) for name in ("policy.py","run.py")},
            "scope":"Retrospective artifact separation. Canadian reference outcomes were already consumed."}
    dump(pred/"PREDICTION_SEAL.json",seal)

    label_file = repo/".runtime/exposure-verification/ahr-results-2/rows.json"
    if sha(label_file)!=read(compact/"ahr-results.json")["rows_sha256"]:
        raise ValueError("Ahr label rows do not match prior seal")
    road = road_metrics(typed,read(label_file))
    threshold = cfg["direction"]["agreement_degrees"]
    lookup = {r["id"]:r for r in directions}
    angle_rows=[]
    for f in frozen:
        pred_row=lookup[f["id"]]
        err = angle(pred_row["nominal"],f["reference_vector"])
        if not math.isclose(err,f["predictions"][cfg["direction"]["nominal"]]["angle_deg"],abs_tol=1e-7):
            raise ValueError("Retrospective angle does not match original result")
        angle_rows.append({"id":f["id"],"year":f["year"],"evidence_tier":pred_row["e_tier"],
                           "angle_deg":err,"agrees_within_45":err<=threshold+1e-9})
    good={r["id"]:r["agrees_within_45"] for r in angle_rows}
    if sum(good.values())!=13:
        raise ValueError("Historical Canadian denominator does not match")
    outcomes,strata,reasons=direction_scores(directions,good,cfg["direction"]["coverage_counts"])
    cases=fixtures(read(HERE/"FIXTURES.json"))

    csv_file(tables/"comparison_results.csv",outcomes)
    csv_file(tables/"claim_coverage.csv",road)
    categories=[{"cohort":"Ahr","category":key,"count":val,"interpretation":cfg["states"].get(key,"No positive-length nominal witness")}
                for key,val in sorted(Counter(r["model_state"] for r in typed.values()).items())]
    categories+= [{"cohort":"Ahr","category":key,"count":value,"interpretation":cfg["states"][key]}
                  for key,value in (("C",sum(r["model_state"]=="C" for r in typed.values())),
                                    ("D",0),("E",60),("F",0))]
    categories+= [{"cohort":"ADCP","category":r["evidence_stratum"],"count":r["units"],
                   "interpretation":f'{r["within_45"]} within 45 degrees in the consumed diagnostic'} for r in strata]
    csv_file(tables/"evidence_categories.csv",categories)
    csv_file(validation/"ADCP_BLOCK_SCORES.csv",angle_rows)
    csv_file(validation/"ADCP_EVIDENCE_STRATA.csv",strata)
    csv_file(base/"ADCP_REASON_COUNTS.csv",reasons)
    dump(pred/"FIXTURE_RESULTS.json",cases)
    dump(validation/"SUMMARY.json",{"ahr":road,"direction_native":[r for r in outcomes if r["mode"]=="native"],
                                     "strata":strata,"fixtures_passed":len(cases)})
    print(f"Scored {len(typed)} road records, {len(good)} consumed ADCP blocks and {len(cases)} new fixtures.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace",type=Path,default=WORKSPACE)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    main(a.workspace.resolve(),a.output.resolve())
