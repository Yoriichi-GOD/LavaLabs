import base64
import io
import json

import numpy as np
import pytest
import requests
from PIL import Image
from fastapi.testclient import TestClient
from rasterio.transform import Affine

from jai_extension.flood_bridge import BridgeError
from lavalabs.public_runs import DemoBridge
from lavalabs.response import CORRIDOR, SCENE, build, inspect_point, point_snapshot
from lavalabs.server import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as value:
        yield value


def test_observation_state_and_metric_distance_are_separate():
    mask = np.zeros((80, 80), dtype="uint8")
    mask[2, 2], mask[2, 1] = 2, 255
    affine = Affine(10, 0, 0, 0, -10, 800)
    assert inspect_point(mask, affine, affine * (2.5, 2.5)) == ("candidate", 0.0)
    assert inspect_point(mask, affine, affine * (1.5, 2.5)) == ("unobserved", None)
    assert inspect_point(mask, affine, affine * (3.5, 2.5)) == ("nearby", 5.0)
    assert inspect_point(mask, affine, affine * (50.5, 2.5)) == ("no_contact", None)
    assert inspect_point(mask, affine, affine * (80, 2.5)) == ("outside", None)


def test_narrow_run_ranks_evidence_and_preserves_gaps(client, monkeypatch):
    def unexpected_network(*args, **kwargs):
        pytest.fail("Saved response must work within the same app")

    monkeypatch.setattr(requests.sessions.Session, "request", unexpected_network)
    response = client.get(f"/api/flood/runs/{SCENE}/response")
    assert response.status_code == 200
    body = response.json()
    first, second, third = (group["sites"] for group in body["priorities"])
    assert [site["kind"] for site in first] == ["building"] * 2 + ["settlement"] * 3
    assert {site["name"]: site["distance_m"] for site in body["settlements"]} == {
        "Pajung": 176.6, "Syabru Bensi": 178.9, "Unnamed mapped settlement": 143.2,
    }
    assert [site["id"] for site in second[:2]] == ["way/84566285", "way/886704211"]
    assert all(row["status"] == "unknown_no_hubs" and row["before"] is None for row in body["access"])
    assert body["nearby_run"] == CORRIDOR

    mask, grid, _, _ = DemoBridge().mask(SCENE)
    raster = Image.open(io.BytesIO(base64.b64decode(body["map"]["png"])))
    assert raster.size == (grid["width"], grid["height"])
    inv = ~Affine(*grid["transform"][:6])
    assert len(third) == 3
    for gap in third:
        assert gap["kind"] == "gap" and gap["evidence"]["state"] == "unobserved"
        col, row = inv * gap["xy"]
        assert mask[int(row), int(col)] == 255
        assert raster.getpixel((int(col), int(row)))[:3] == (66, 69, 78)


def test_corridor_brief_does_not_treat_missing_modeled_route_as_known_closure(client):
    response = client.get(f"/api/flood/runs/{CORRIDOR}/response?brief=true")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    brief = response.json()
    assert brief["map"] is None
    site = next(row for row in brief["access"] if row["id"] == "node/267564991")
    assert site["before"] and site["optimistic"] is site["conservative"] is False
    assert site["boundary_truncated"] and site["status"] == "unknown_aoi_boundary"
    assert site["hub_name"] == "Rasuwa District Hospital"
    assert [row["state"] for row in brief["care"] if row["name"] == site["hub_name"]] == ["outside"]
    assert any(row["name"] == "Bahun Danda" and row["state"] == "unobserved" for row in brief["settlements"])


def test_render_entry_points_and_archive_boundary(client):
    home = client.get("/").text
    for element_id in ("flood-views", "flood-processor", "processor-response", "response-svg", "event-pick", "map-optical"):
        assert f'id="{element_id}"' in home
    assert home.count('shadowrootmode="open"') == 2
    assert 'id="event-bbox" required value=' not in home
    assert '/?view=flood-evidence#terrain' in home
    assert f"/?view=response&amp;run={SCENE}#terrain" in client.get("/nepal").text
    legacy = client.get(f"/processor/response?run={SCENE}", follow_redirects=False)
    assert legacy.status_code == 307 and legacy.headers["location"] == f"/?view=response&run={SCENE}#terrain"
    assert client.get("/processor", follow_redirects=False).headers["location"] == "/?view=analysis#terrain"
    assert client.get("/api/flood/runs/private-archive-run/response").status_code == 404


def test_response_overlay_uses_identical_grid_and_preserves_original_radar_classes(client):
    base = f"/api/flood/runs/{SCENE}"
    response = client.get(f"{base}/response").json()
    overlay = Image.open(io.BytesIO(base64.b64decode(response["map"]["overlay"])))
    mask, expected, _, _ = DemoBridge().mask(SCENE)
    grid = client.get(f"{base}/visual-context").json()["after"]["grid"]
    optical = client.get(f"{base}/visual/after.png")
    assert optical.status_code == 200
    assert overlay.size == Image.open(io.BytesIO(optical.content)).size
    for key in ("crs", "transform", "width", "height"):
        assert response["map"][key] == grid[key] == expected[key]
    alpha = np.asarray(overlay)[:, :, 3]
    assert np.all(alpha[(mask == 0) | (mask == 1)] == 0)
    assert np.all(alpha[mask == 2] == 210)
    assert np.all(alpha[mask == 255] == 124)


def test_new_runs_read_points_from_the_frozen_topology():
    topology = {"settlements": [{"id": "node/1", "point": [85, 28], "kind": "settlement"},
                                {"id": "node/2", "node_id": 2}],
                "care_sites": [{"id": "node/3", "point": [85.1, 28.1], "kind": "care"}]}
    rows, source = point_snapshot("event-000000000000", "2026-08-25T00:00:00Z", topology)
    assert [row["id"] for row in rows] == ["node/1", "node/3"]
    assert source["source"] == "Frozen historical topology audit"


def test_verified_sources_required(monkeypatch):
    bridge = DemoBridge()
    read_original = bridge.read

    def read(path, *args):
        raw = read_original(path, *args)
        return raw + b" " if path.endswith("/connectivity.json") else raw

    monkeypatch.setattr(bridge, "read", read)
    with pytest.raises(BridgeError) as error:
        build(bridge, SCENE)
    assert error.value.status == 409


def test_synthetic_run_rejected_before_processing(monkeypatch):
    bridge = DemoBridge()
    monkeypatch.setattr(bridge, "freeze", lambda _: ({}, b""))
    monkeypatch.setattr(bridge, "verified", lambda *args: (json.dumps({
        "run_id": SCENE, "synthetic": True,
    }).encode(), "test"))
    with pytest.raises(BridgeError) as error:
        build(bridge, SCENE)
    assert error.value.status == 422
