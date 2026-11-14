"""Claim scope decisions for the final R3 diagnostic."""
from dataclasses import dataclass
import math


CLAIMS = ("OBSERVED_CHANGE", "GEOMETRIC_SCREENING_CANDIDATE", "MODELED_TERRAIN_PATHWAY",
          "INDEPENDENTLY_SUPPORTED_PHYSICAL_EXPOSURE")
REQUIRED_MATCH = ("identity_verified", "independent_lineage", "target_matches",
                  "footprint_matches", "time_matches", "observed_support")


@dataclass(frozen=True)
class Reference:
    identity: str
    target: str
    verdict: str
    checks: dict

    def valid(self, target):
        return bool(self.identity and self.target == target
                    and self.verdict in {"supports", "contradicts"}
                    and all(self.checks.get(check) is True for check in REQUIRED_MATCH))


def assess(*, observed, geometric, nominal, strict, sensitive, auxiliary_missing,
           scale_unresolved, receptor_identified=True, references=()):
    """Separate model assertion scope from two independent physical targets."""
    reasons = []
    if not observed:
        reasons.append("NOMINAL_OBSERVATION_UNAVAILABLE")
    if not receptor_identified:
        reasons.append("RECEPTOR_IDENTITY_UNAVAILABLE")
    if not nominal:
        reasons.append("NO_NOMINAL_WITNESS")
    if auxiliary_missing:
        reasons.append("ALTERNATIVE_SUPPORT_UNAVAILABLE")
    if sensitive:
        reasons.append("ALTERNATIVE_RELATIONSHIP_CHANGED")
    if scale_unresolved:
        reasons.append("ASSET_SCALE_UNRESOLVED")
    modeled = observed and receptor_identified and nominal
    state = "C" if not (observed and receptor_identified) else (
        "A" if modeled and strict and not sensitive and not auxiliary_missing else
        "B" if modeled else "NO_MODELED_WITNESS")
    if modeled and state == "A":
        qualifier = "nominal_model_with_compatible_required_alternatives"
    elif modeled:
        qualifier = "nominal_model_only"
    else:
        qualifier = None
    reference_findings = {}
    for target in ("endpoint_exposure", "source_to_endpoint_traversal"):
        valid = [r for r in references if r.valid(target)]
        support = [r.identity for r in valid if r.verdict == "supports"]
        contradiction = [r.identity for r in valid if r.verdict == "contradicts"]
        unmatched = [{"identity": r.identity, "failed": [key for key in REQUIRED_MATCH
                                                        if r.checks.get(key) is not True]}
                     for r in references if r.target == target and not r.valid(target)]
        status = ("D" if contradiction else "F" if support else "UNKNOWN")
        reference_findings[target] = {
            "state": status, "qualified": bool(observed and receptor_identified and support and not contradiction),
            "supporting_ids": support, "contradicting_ids": contradiction, "unmatched": unmatched,
            "withholding_reason": ("MATCHED_INDEPENDENT_CONTRADICTION" if contradiction
                                   else "NO_MATCHED_INDEPENDENT_REFERENCE" if not support
                                   else "PREREQUISITE_OBSERVATION_OR_GEOMETRY_UNAVAILABLE"
                                   if not (observed and receptor_identified) else None),
        }
    return {
        "model_state": state, "scale_state": "E" if scale_unresolved else "NOT_FLAGGED",
        "qualified_claims": [name for name, flag in zip(CLAIMS, (
            observed, observed and receptor_identified and geometric, modeled,
            reference_findings["endpoint_exposure"]["qualified"]
        )) if flag], "modeled_scope": qualifier,
        "model_reasons": reasons, "physical_targets": reference_findings,
    }


def unit(vector):
    n = math.hypot(*vector)
    if not math.isfinite(n) or n == 0:
        raise ValueError("Invalid nonzero vector required")
    return tuple(v/n for v in vector)


def angle(x, y):
    cosine = math.fsum(a*b for a, b in zip(unit(x), unit(y)))
    return math.degrees(math.acos(max(-1., min(1., cosine))))


def direction_predict(record, cfg):
    """Use only frozen model vectors. The caller joins reference vectors after sealing."""
    nominal = record[cfg["nominal"]]
    if nominal is None:
        return {"nominal": None, "state": "C", "strict": False, "g_key": [0, 0.]}
    alternatives = {name: record[name] for name in cfg["alternates"]}
    errors = {name: angle(nominal, v) if v is not None else None for name,v in alternatives.items()}
    missing = [name for name, error in errors.items() if error is None]
    discordant = [name for name, error in errors.items() if error is not None
                  and error > cfg["agreement_degrees"]+1e-9]
    strict = not missing and not discordant
    tier = 2 if strict else 1 if not missing else 0
    result = math.hypot(*(math.fsum(component)/4 for component in zip(
        *(unit(v) for v in (nominal, *alternatives.values()))))) if not missing else 0.
    return {"nominal": nominal, "state": "A" if strict else "B", "strict": strict,
            "missing": missing, "discordant": discordant, "angles": errors,
            "e_tier": tier, "g_key": [int(not missing), round(result,12)]}
