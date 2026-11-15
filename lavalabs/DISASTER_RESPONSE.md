# Disaster response

Open `/processor` and select a completed real flood run. The response panel also appears after a new real run completes. It links to the run’s action map and downloadable JSON brief on the same server.

| Priority | Trigger | Follow-up |
| --- | --- | --- |
| 1 · Check people | A mapped structure intersects candidate water, or an observed historical settlement point lies within 250 m of a candidate pixel footprint. | Verify occupancy, welfare and urgent needs with local contacts. Direct intersections precede proximity checks. |
| 2 · Verify access | A mapped bridge or road intersects the candidate mask. | Confirm condition and passability from a safe approach with local authorities. Bridges precede road segments. Within each type, longer intersections appear first. |
| 3 · Check again | An observed settlement point has no nearby candidate, a settlement point is unobserved, or a connected radar gap of nine or more pixels has a pixel centre within 250 m of a candidate centre. | Request ground reports and follow up when official warnings or observations change. |

The 250 m distance is a review radius. It has no calibration to flood extent or severity. The historical road scenarios are shown independently from water-based priorities. The actions help people verify what is urgent. Individual urgency, active road closures, a safe path, hospital readiness and future inundation require current inputs. The map records observed and unobserved pixels separately. A point without candidate contact describes that point and observation only.

## Nepal replay

- **26 August 2026, narrow scene** (`event-fe47db331390`). Two direct structure overlaps. Three mapped settlement points are within 250 m of candidates: an unnamed hamlet at 143.2 m, Pajung at 176.6 m, and Syabru Besi at 178.9 m. Two bridge intersections measure 10.1 m and 8.5 m. The narrow road graph captured no destination hubs.
- **Alternate scene and wider access network** (`nepal-syapru-004`). Syabru Besi had a modeled pre-event route to Rasuwa District Hospital. Both modeled disruption scenarios remove the route within the historical network. The graph ends at the study boundary, so real access is unknown. In this scene Pajung and Bahun Danda fall on unobserved pixels. The mapped hospital lies outside the image.

The historical points are reproducible with `python scripts/prepare_response_points.py components/floodlab/data lavalabs/response-points.json` when the two retained inputs are present. The public checkout includes the derived points with both input SHA-256 values. New automatic runs store settlement and mapped care coordinates in the frozen topology audit. Older runs without linked points still receive mapped intersections and coverage checks. Raster, feature and access evidence are checked against the run's freeze map before use.

[OpenStreetMap contributors and ODbL](https://www.openstreetmap.org/copyright) · [Nepal DHM](https://www.dhm.gov.np/) · [Nepal health facility registry](https://nhfr.mohp.gov.np/)

Lifeline's presentation of settlement access and proposed actions informed the response workflow. LavaLabs computes its own priorities from the listed inputs. [Lifeline repository](https://github.com/kinnuworks/lifeline) · [Lifeline Devpost entry](https://devpost.com/software/flood-damage-from-space)

OpenAI Codex assisted the implementation and action wording. Original observations and historical map data retain their provenance.
