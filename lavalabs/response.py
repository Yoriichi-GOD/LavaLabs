"""Field-verification priorities from saved flood evidence. OpenAI Codex assisted."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt, find_objects, label
from shapely.geometry import Point, box, shape
from shapely.ops import transform

from jai_extension.flood_bridge import BridgeError, parse_json

POINTS = Path(__file__).with_name("response-points.json")
SCENE = "event-fe47db331390"
CORRIDOR = "nepal-syapru-004"
CONTACT_RADIUS = 250
START_ACTIONS = (
    "Request a welfare check. Confirm who is present, who needs urgent help and how responders can reach them.",
    "Verify the crossing and its approaches with local authorities before sending a team or arranging a transfer.",
    "Verify the coverage gaps and keep a local contact on the alert list. Recheck when official warnings or field reports change.",
)
FALLBACK = (
    "Ask local contacts where urgent help is needed. The retained analysis supplies no first-check site.",
    "Ask local authorities to verify access and a receiving destination before assigning transport.",
    "Check official warnings and request ground reports for unobserved or unmapped areas.",
)


def point_snapshot(run_id, osm_snapshot, topology):
    raw = POINTS.read_bytes()
    source = parse_json(raw)["runs"].get(run_id)
    if source:
        if source["snapshot"] != osm_snapshot:
            raise BridgeError(409, "Response map and run use different OSM snapshot dates")
        return source["points"], {
            "snapshot": source["snapshot"], "source": source["source"],
            "source_sha256": source["source_sha256"],
            "extract_sha256": hashlib.sha256(raw).hexdigest(),
        }
    locations = {row["id"]: row for group in ("settlements", "care_sites")
                 for row in topology.get(group, []) if row.get("point") is not None}
    return list(locations.values()), {"snapshot": osm_snapshot, "source": "Frozen historical topology audit"}


def inspect_point(mask, affine, point):
    """Statically screen the observed pixel, then check local candidate proximity."""
    col, row = (~affine) * point
    col_index, row_index = int(np.floor(col)), int(np.floor(row))
    height, width = mask.shape
    if not (0 <= col_index < width and 0 <= row_index < height):
        return "outside", None
    value = mask[row_index, col_index]
    if value == 255:
        return "unobserved", None
    if value == 2:
        return "candidate", 0.0
    x_radius = int(np.ceil(CONTACT_RADIUS / affine.a)) + 1
    y_radius = int(np.ceil(CONTACT_RADIUS / -affine.e)) + 1
    left, top = max(0, col_index - x_radius), max(0, row_index - y_radius)
    window = mask[top:row_index + y_radius + 1, left:col_index + x_radius + 1]
    rows, cols = np.nonzero(window == 2)
    if not len(rows):
        return "no_contact", None
    dx = np.maximum(0, np.abs(cols + left + .5 - col) - .5) * affine.a
    dy = np.maximum(0, np.abs(rows + top + .5 - row) - .5) * -affine.e
    metres = float(np.hypot(dx, dy).min())
    return ("nearby", round(metres, 1)) if metres <= CONTACT_RADIUS else ("no_contact", None)


def raster_image(mask, *, overlay=False):
    palette = np.array([(17, 22, 25, 255)] * 256, dtype=np.uint8)
    palette[1] = (28, 62, 71, 255)
    palette[2] = (232, 151, 77, 255)
    palette[255] = (66, 69, 78, 255)
    if overlay:
        palette[0] = palette[1] = (0, 0, 0, 0)
        palette[2] = (49, 227, 255, 210)
        palette[255] = (42, 37, 58, 124)
    buffer = io.BytesIO()
    Image.fromarray(palette[mask]).save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def nearby_gaps(mask, affine):
    """Find a few distinct unobserved patches near mapped water for follow-up."""
    gaps, _ = label(mask == 255)
    if not gaps.any() or not (mask == 2).any():
        return []
    distance = distance_transform_edt(mask != 2, sampling=(-affine.e, affine.a))
    options = []
    for index, window in enumerate(find_objects(gaps), start=1):
        if window is None:
            continue
        patch = gaps[window] == index
        if patch.sum() < 9:
            continue
        nearest = np.where(patch, distance[window], np.inf)
        row, col = np.unravel_index(nearest.argmin(), nearest.shape)
        metres = nearest[row, col]
        if metres <= CONTACT_RADIUS:
            xy = affine * (window[1].start + col + .5, window[0].start + row + .5)
            options.append((round(float(metres), 1), index, xy))
    return sorted(options)[:3]


def access_context(connectivity, topology, selected):
    hubs = {entry.get("node_id"): entry for entry in topology.get("hubs", [])
            if entry.get("node_id") is not None}
    rows = []
    for entry in connectivity:
        if entry["id"] not in selected:
            continue
        hub = hubs.get(entry.get("nearest_pre_event_hub"), {})
        rows.append({
            "id": entry["id"], "name": selected[entry["id"]],
            "status": entry["status"],
            "before": entry.get("connected_before"),
            "optimistic": entry.get("connected_after_optimistic"),
            "conservative": entry.get("connected_after_conservative"),
            "boundary_truncated": entry.get("boundary_truncated"),
            "hub_name": hub.get("name"),
            "hub_id": hub.get("id"),
            "distance_before_m": entry.get("distance_before_m"),
        })
    return rows


def build(bridge, run_id, *, include_map=True):
    bridge.require(run_id)
    files, freeze_raw = bridge.freeze(run_id)
    sources = {}

    def data(name):
        value, digest = bridge.verified(run_id, name, files)
        sources[name] = digest
        return value

    result = parse_json(data("result.json"))
    manifest = parse_json(data("manifest.json"))
    if result.get("run_id") != run_id or type(result.get("synthetic")) is not bool or result["synthetic"] is not manifest.get("synthetic"):
        raise BridgeError(422, "Response run identity could not be verified")
    if result["synthetic"]:
        raise BridgeError(422, "Disaster response is available for real observation runs")
    mask, grid, coverage, sources["prediction.tif"] = bridge.mask(run_id, files=files)
    if any(coverage[key] != result["summary"][result_key] for key, result_key in
           (("candidate_pixels", "new_water_pixels"), ("valid_pixels", "valid_pixels"), ("total_pixels", "total_pixels"))):
        raise BridgeError(409, "Response raster and saved summary disagree")
    layers = parse_json(data("layers.geojson"))["features"]
    exposure_raw = data("exposure.csv")
    exposure = bridge.exposure_table(exposure_raw, sources["exposure.csv"], "water")["rows"]
    topology = parse_json(data("topology-audit.json")) if "topology-audit.json" in files else {}
    connectivity = parse_json(data("connectivity.json")) if "connectivity.json" in files else []
    osm_rows, osm_source = point_snapshot(run_id, manifest.get("osm_snapshot"), topology)

    project = Transformer.from_crs(4326, grid["crs"], always_xy=True).transform
    unproject = Transformer.from_crs(grid["crs"], 4326, always_xy=True).transform
    footprint = box(*grid["bounds"])
    affine = Affine(*grid["transform"][:6])
    osm_in_study = []
    care = []
    priorities = {1: [], 2: [], 3: []}

    def marker(identifier, title, role, p, coordinate, detail, evidence):
        return {"id": identifier, "name": title, "kind": role, "priority": p, "xy": list(coordinate),
                "lonlat": [round(value, 6) for value in unproject(*coordinate)],
                "detail": detail, "evidence": evidence}

    for site in osm_rows:
        xy = project(*site["point"])
        state, metres = inspect_point(mask, affine, xy)
        fallback_name = "Unnamed mapped facility" if site["kind"] == "care" else "Unnamed mapped settlement"
        name = site["name"] if site["name"] != site["id"] else fallback_name
        if site["kind"] == "care":
            if footprint.distance(Point(xy)) <= 15000:
                care.append({"id": site["id"], "name": name, "lonlat": site["point"], "xy": xy,
                             "state": state, "distance_from_scene_m": round(footprint.distance(Point(xy))),
                             "place_type": site.get("place_type")})
            continue
        if state == "outside":
            continue
        osm_in_study.append({"id": site["id"], "name": name, "state": state, "distance_m": metres})
        p = 1 if state in {"candidate", "nearby"} else 3
        detail = f"The mapped settlement point is {metres:g} m from the nearest water candidate." if state == "nearby" else {
            "candidate": "The mapped settlement point falls inside a radar water candidate.",
            "unobserved": "The radar pair could not assess the pixel at this mapped settlement point.",
            "no_contact": "The point was observed and no water candidate lies within the screening radius.",
        }[state]
        priorities[p].append(marker(site["id"], name, "settlement", p, xy, detail,
                                    {"state": state, "distance_m": metres, "source": "Historical OSM + radar grid"}))

    geometries = {feature.get("id"): feature for feature in layers if feature.get("id")}
    candidate = [feature for feature in layers if feature["properties"]["kind"] == "new-water-candidate"]
    candidate_geom = transform(project, shape(candidate[0]["geometry"])) if candidate else None
    for row in exposure:
        if row["status"] != "exposed":
            continue
        feature = geometries.get(row["id"])
        if feature is None or candidate_geom is None:
            raise BridgeError(409, "Exposed feature has no corresponding saved map geometry")
        overlap = transform(project, shape(feature["geometry"])).intersection(candidate_geom)
        if overlap.is_empty:
            raise BridgeError(409, "Saved map cannot locate a reported intersection")
        point = overlap.representative_point()
        p = 1 if row["kind"] == "building" else 2
        tags = feature["properties"].get("tags", {})
        label = {"building": "Mapped structure", "bridge": "Mapped bridge", "road": "Mapped road segment"}[row["kind"]]
        name = tags.get("name:en") or tags.get("name") or tags.get("ref") or label
        amount = f'{row["exposed"]:.1f} {"m²" if p == 1 else "m"}'
        detail = (f"The mapped footprint overlaps water candidates by {amount}. Verify occupancy and immediate needs."
                  if p == 1 else f"The mapped crossing or road overlaps water candidates along {amount}. Check physical condition and passability.")
        priorities[p].append(marker(row["id"], name, row["kind"], p, (point.x, point.y), detail,
                                    {"overlap": row["exposed"], "unit": row["unit"], "source": "Frozen feature intersection"}))

    for rank, (metres, index, xy) in enumerate(nearby_gaps(mask, affine), start=1):
        priorities[3].append(marker(f"coverage-gap/{index}", f"Radar gap {rank}", "gap", 3, xy,
                                    f"This unobserved patch comes within {metres:g} m of a candidate by pixel centres. Ask for a ground report when warnings change.",
                                    {"state": "unobserved", "distance_m": metres, "source": "Frozen radar grid"}))

    priorities[1].sort(key=lambda v: (v["kind"] != "building", v["evidence"].get("distance_m") or 0, v["id"]))
    priorities[2].sort(key=lambda v: (v["kind"] != "bridge", -v["evidence"]["overlap"], v["id"]))
    priorities[3].sort(key=lambda v: (v["evidence"]["state"] != "unobserved", v["name"], v["id"]))
    omitted = {p: max(0, len(sites) - 8) for p, sites in priorities.items()}
    priorities = {p: sites[:8] for p, sites in priorities.items()}
    context = access_context(connectivity, topology, {v["id"]: v["name"] for v in osm_in_study})
    lead = next((v["name"] for v in priorities[1] if v["kind"] == "settlement" and not v["name"].startswith("Unnamed")),
                priorities[1][0]["name"] if priorities[1] else None)
    roads = []
    exposed_ids = {site["id"] for site in priorities[2]}
    lines = sorted((feature for feature in layers if feature["properties"]["kind"] in ("road", "bridge")),
                   key=lambda feature: (feature.get("id") not in exposed_ids, feature.get("id", "")))
    for feature in lines[:250] if include_map else []:
        clipped = transform(project, shape(feature["geometry"])).intersection(footprint).simplify(4)
        for line in getattr(clipped, "geoms", (clipped,)):
            if line.geom_type == "LineString" and not line.is_empty:
                roads.append({"xy": list(line.coords), "check": feature.get("id") in exposed_ids})

    return {
        "run_id": run_id, "event_name": result["event_name"], "event_date": manifest.get("event_time"),
        "observations": [manifest[key]["datetime"] for key in ("pre", "post")],
        "scope": "Retrospective satellite screening and field-verification planning",
        "priorities": [{"level": p, "action": START_ACTIONS[p-1] if sites else FALLBACK[p-1],
                        "sites": sites, "more": omitted[p]} for p, sites in priorities.items()],
        "lead": lead, "settlements": osm_in_study, "access": context,
        "care": care_directory(care),
        "coverage": coverage, "contact_radius_m": CONTACT_RADIUS, "osm": osm_source,
        "map": {"bounds": grid["bounds"], "crs": grid["crs"], "transform": grid["transform"],
                "width": grid["width"], "height": grid["height"], "png": raster_image(mask),
                "overlay": raster_image(mask, overlay=True), "roads": roads} if include_map else None,
        "nearby_run": CORRIDOR if run_id == SCENE else SCENE if run_id == CORRIDOR else None,
        "nepal": run_id in (SCENE, CORRIDOR) or 80 <= grid["bbox_wgs84"][0] <= 88.2 and 26.3 <= grid["bbox_wgs84"][1] <= 30.5,
        "sources": sources, "freeze_sha256": hashlib.sha256(freeze_raw).hexdigest(),
        "si_disclosure": "OpenAI Codex assisted code and action wording. Coordinates and intersections derive from the listed sources.",
    }


def care_directory(rows):
    # OSM can describe one facility with both a building footprint and an amenity node.
    kept = []
    for row in sorted(rows, key=lambda entry: (not entry["id"].startswith("node/"), entry["distance_from_scene_m"], entry["id"])):
        if any(row["name"] == previous["name"] and not row["name"].startswith("Unnamed")
               and np.hypot(row["xy"][0] - previous["xy"][0], row["xy"][1] - previous["xy"][1]) <= 100
               for previous in kept):
            continue
        kept.append(row)
    return [{key: value for key, value in row.items() if key != "xy"}
            for row in sorted(kept, key=lambda entry: (entry["distance_from_scene_m"], entry["id"]))[:8]]
