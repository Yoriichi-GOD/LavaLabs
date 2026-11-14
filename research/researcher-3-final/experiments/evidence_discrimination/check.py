"""Independent accounting checks for the V3 release and repeat."""
import argparse
import csv
from itertools import combinations
from pathlib import Path

from run import FINAL, WORKSPACE, read, sha, rank_stats


COMPARISONS = (
    "tables/comparison_results.csv", "tables/claim_coverage.csv", "tables/evidence_categories.csv",
    "experiments/evidence_discrimination/AHR_CLAIMS.json",
    "experiments/evidence_discrimination/ADCP_DIRECTION_RANKINGS.json",
    "experiments/evidence_discrimination/PREDICTION_SEAL.json",
    "experiments/evidence_discrimination/FIXTURE_RESULTS.json",
    "experiments/baseline_comparisons/ADCP_REASON_COUNTS.csv",
    "experiments/validation/ADCP_BLOCK_SCORES.csv", "experiments/validation/ADCP_EVIDENCE_STRATA.csv",
    "experiments/validation/SUMMARY.json",
)


def lines(path):
    with path.open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def verify(repeat):
    for path in COMPARISONS:
        assert sha(FINAL/path)==sha(repeat/path),path
    base = FINAL/"experiments/evidence_discrimination"
    pilot = WORKSPACE/"cegs-novelty-20261112"
    frozen = read(pilot/"measurements/pilot/ahr_claim_predictions.json")["predictions"]
    final = read(base/"AHR_CLAIMS.json")
    # Canonicalize the original score ties by road ID.
    assert sorted((tuple(r["original_priority"]),k) for k,r in final.items())==sorted(
        (tuple(r["sealed_rank"]),k) for k,r in frozen.items() if r["proximity"])
    assert sum(r["modeled_scope"] is not None for r in final.values())==23
    assert sum(r["model_state"]=="A" for r in final.values())==3
    assert all(not any(v["qualified"] for v in r["physical_targets"].values()) for r in final.values())
    seal=read(base/"PREDICTION_SEAL.json")
    assert sha(base/"AHR_CLAIMS.json")==seal["road_claims_sha256"]
    assert sha(base/"ADCP_DIRECTION_RANKINGS.json")==seal["direction_rankings_sha256"]
    assert sha(base/"PROTOCOL.json")==seal["protocol_sha256"]
    assert sha(base/"FIXTURES.json")==seal["fixture_sha256"]
    fixtures=read(base/"FIXTURE_RESULTS.json")
    assert len(fixtures)==15 and all(f["expected"]==f["actual"] for f in fixtures)
    assert all(row["retained"] for row in final.values())

    tab=lines(FINAL/"tables/comparison_results.csv")
    for r in tab:
        if r["feasible"]=="False":
            assert not r["conditional_error"] and not r["correct_retained"]
            continue
        n,k,correct=int(r["eligible"]),int(r["issued"]),int(r["nominal_correct"])
        hits,misses,withheld,false=(float(r[c]) for c in ("correct_retained","incorrect_issued",
                                                  "incorrect_rejected","false_rejected"))
        assert abs(hits+misses-k)<1e-8 and abs(hits+false-correct)<1e-8
        assert abs(misses+withheld-(n-correct))<1e-8
        assert int(r["correct_min"])-1e-8<=hits<=int(r["correct_max"])+1e-8
        assert (not r["conditional_error"] if not k else abs(float(r["conditional_error"])-misses/k)<1e-9)
    matched={(r["arm"],int(r["issued"])):float(r["correct_retained"]) for r in tab
             if r["mode"]=="matched" and r["feasible"]=="True"}
    assert all(matched[arm,2]==1 for arm in "BEG")
    assert matched["E",14]==5 and matched["G",14]==4

    tie=[{"id":str(i)} for i in range(7)]
    score={str(i):i in {1,3,4} for i in range(7)}
    for k in range(8):
        values=[sum(score[r["id"]] for r in subset) for subset in combinations(tie,k)]
        expected,low,high=rank_stats(tie,score,k,lambda r:0)
        assert abs(expected-sum(values)/len(values))<1e-9 and (low,high)==(min(values),max(values))

    prior=FINAL.with_name("researcher-3-revision")
    original=list((prior/"figures").rglob("*.png"))+list((prior/"figures").rglob("*.svg"))
    assert len(original)==16
    for file in original:
        assert sha(file)==sha(FINAL/"figures/publication_figures"/file.relative_to(prior/"figures"))
    print("Verified 11 byte-identical replay artifacts, 60 invariant candidate scores/IDs, 15 fixture "
          "decisions, exact tie accounting, and 16 original PNG/SVG hashes.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat",type=Path,required=True)
    verify(parser.parse_args().repeat.resolve())
