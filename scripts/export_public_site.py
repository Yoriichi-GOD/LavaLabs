"""Publish read-only LavaLabs views from the repository's two frozen demo runs.

Run from a clean checkout. This exporter has no external service credentials or
network acquisition. OpenAI Codex assisted the integration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from lavalabs.nepal_exports import load_case
from lavalabs.public_runs import DEMO_RUNS, DemoBridge
from lavalabs.server import CASES, REPORTS, ROOT, WORDMARK, create_app, logo_path
from lavalabs.trend_exports import read
from scripts.bootstrap_demo import bootstrap


ROUTES = re.compile(
    r"""(["'`(])(/(?:api/|apps/|assets/|art/|ui/|jai/|runs/|processor-assets/|processor-art/|trends-data/"""
    r"""|(?:nepal|trends)(?=[/?#"'\x60])|(?=[?#])))"""
)
TEXT_ASSETS = {".html", ".css", ".js"}
LIMIT = 95 * 1024 * 1024
LOGO = "/logo" + logo_path().suffix
ICON = "/favicon" + (".svg" if logo_path().name == WORDMARK else logo_path().suffix)


def prefix_links(text, base):
    text = re.sub(r"""(["'`])/logo(?=["'`])""", lambda match: match[1] + base + LOGO, text)
    text = re.sub(r"""(["'`])/favicon\.ico(?=["'`])""", lambda match: match[1] + base + ICON, text)
    return ROUTES.sub(lambda match: match[1] + base + match[2], text)


class Export:
    def __init__(self, output, base):
        self.output, self.base = output, base

    def write(self, name, content):
        destination = (self.output / name.lstrip("/")).resolve()
        if not destination.is_relative_to(self.output) or destination.exists():
            raise ValueError(f"Invalid or duplicate static path: {name}")
        if len(content) > LIMIT:
            raise ValueError(f"Public asset exceeds the deployment limit: {name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def asset(self, source, name):
        if source.suffix in TEXT_ASSETS and "vendor" not in source.parts:
            self.write(name, prefix_links(source.read_text(encoding="utf-8"), self.base).encode())
        else:
            self.write(name, source.read_bytes())

    def snapshot(self, client, url, *, path=None, rewrite=False, optional=False):
        reply = client.get(url, follow_redirects=False)
        if optional and reply.status_code == 404:
            return
        if reply.status_code != 200:
            raise ValueError(f"Snapshot request returned {reply.status_code}: {url}")
        path = path or urlsplit(url).path
        if "/" == path or not Path(path).suffix:
            path = path.rstrip("/") + "/index.html"
        content = reply.content
        if rewrite:
            text = reply.text
            if url in {"/", "/nepal", "/trends"}:
                text = text.replace("<html ", "<html data-hosted ", 1)
            if url == "/":
                text = text.replace(">Analyze area</button>", ">Saved runs</button>", 1)
                text = text.replace("Analyze saved observation →", "Open saved response →", 1)
            content = prefix_links(text, self.base).encode()
        self.write(path, content)

    def assets(self):
        files = {
            "ui": ["UI/" + name for name in ("app.js", "lava.css", "processor.css", "processor-lava.js",
                                             "flood-desk.css", "wordmark.css")],
            "assets": ["UI/satquery/" + name for name in ("style.css", "noir.css", "workspace-shell.css",
                                                          "visual-context.js", "noir/scientific-noir-background.png")],
            "jai/assets": ["jai_extension/web/" + name for name in ("earth.js", "earth.css",
                                                                    "vendor/plotly-4.1.1.min.js")],
            "processor-assets": ["components/floodlab/web/" + name for name in
                                 ("style.css", "flood-workspace.css", "flood-workspace.js", "benchmarks.js",
                                  "benchmark-data.json", "dataset-readiness.json", "debris-reference-agreement.json")],
            "processor-art": ["components/floodlab/web/art/" + name for name in
                              ("flood-workflow-satellite-planet.png", "evaluation-space.png")],
            "trends-data": ["trend_lab/web/style.css", "trend_lab/web/land.geojson"],
        }
        prefixes = {"ui": "UI", "assets": "UI/satquery", "jai/assets": "jai_extension/web",
                    "processor-assets": "components/floodlab/web", "processor-art": "components/floodlab/web/art",
                    "trends-data": "trend_lab/web"}
        for mount, names in files.items():
            for name in names:
                self.asset(ROOT/name, mount + "/" + Path(name).relative_to(prefixes[mount]).as_posix())
        for source, mount in (
            ("UI/art", "art"), ("UI/satquery/fonts", "assets/fonts"), ("UI/nepal", "ui/nepal"),
            ("UI/trends", "ui/trends"), ("UI/response", "ui/response"), ("trend_lab/web/data", "trends-data/data"),
        ):
            for file in sorted((ROOT/source).rglob("*")):
                if file.is_file() and file.name != "index.html":
                    self.asset(file, f"{mount}/{file.relative_to(ROOT/source).as_posix()}")

    def export_runs(self, client, scene):
        bridge = DemoBridge()
        for run in sorted(DEMO_RUNS):
            prefix = f"/api/flood/runs/{run}"
            if not client.get(prefix + "/visual-context").json().get("optical_available"):
                raise ValueError(f"Public demo is missing matching RGB for {run}")
            for url in ("", "/exposure", "/debris", "/grid", "/candidate.png", "/debris-candidate.png",
                        "/visual-context", "/visual/before.png", "/visual/after.png", "/visual/water.png",
                        "/visual/debris.png", "/visual/buildings.png", "/response"):
                self.snapshot(client, prefix + url, rewrite=url in {"", "/visual-context"}, optional=url.endswith(".png"))
            self.snapshot(client, prefix + "/response?brief=true", path=prefix + "/response/brief.json")
            self.snapshot(client, f"/api/context/coverage?run_id={run}&scene_id={scene}",
                          path=f"/api/context/coverage/{run}/{scene}.json")
            files, freeze = bridge.freeze(run)
            self.write(f"/runs/{run}/freeze.json", freeze)
            self.write(f"{prefix}/artifact/freeze.json", freeze)
            for name, digest in files.items():
                raw = bridge.artifact_path(run, name).read_bytes()
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError(f"Saved artifact failed its freeze check: {run}/{name}")
                self.write(f"/runs/{run}/{name}", raw)
                self.write(f"{prefix}/artifact/{name}", raw)

    def build(self):
        bootstrap(verify=True)
        with TestClient(create_app()) as client:
            self.assets()
            for page in ("/", "/nepal", "/trends"):
                self.snapshot(client, page, rewrite=True)
            self.snapshot(client, "/logo", path=LOGO)
            self.snapshot(client, "/favicon.ico", path=ICON)
            for route in ("/api/runs", "/api/flood/runs", "/api/lava/status", "/api/lava/research",
                          "/api/experimental-evidence", "/api/terrain/status"):
                self.snapshot(client, route, rewrite=route == "/api/lava/research")
            listing = client.get("/api/runs").json()
            if {row["run_id"] for row in listing} != DEMO_RUNS:
                raise ValueError("Public site must include only the repository's two demo runs. Use a clean checkout.")
            scenes = client.get("/api/terrain/status").json()["scenes"]
            if len(scenes) != 1:
                raise ValueError("Exactly one public demo terrain scene is required")
            scene = scenes[0]["id"]
            self.snapshot(client, f"/api/terrain/scenes/{scene}", rewrite=True)
            self.snapshot(client, f"/api/terrain/scenes/{scene}/raster", path=f"/api/terrain/scenes/{scene}/raster.tif")
            self.export_runs(client, scene)
            for case in CASES:
                self.snapshot(client, f"/api/lava/cases/{case}/view")
                self.snapshot(client, f"/api/research/cases/{case}")
                self.snapshot(client, f"/api/research/cases/{case}/panels.png")
            for report in REPORTS:
                self.snapshot(client, "/api/lava/reports/" + report, path="/api/lava/reports/" + report + ".md")
            for cell in load_case()["climate"]["cells"]:
                for variable in cell["trends"]:
                    for kind in ("json", "csv"):
                        stem = f"/api/lava/nepal/{cell['id']}/{variable}"
                        self.snapshot(client, f"{stem}/{kind}", path=f"{stem}/annual.{kind}")
            for index, window in enumerate(read("analysis.json")["windows"]):
                for row in window["results"]:
                    for kind in ("json", "csv"):
                        stem = f"/api/lava/trends/{row['region']['id']}/{row['variable']}/{index}"
                        self.snapshot(client, f"{stem}/{kind}", path=f"{stem}/annual.{kind}")
        self.write(".nojekyll", b"")
        files = [path for path in self.output.rglob("*") if path.is_file()]
        size = sum(path.stat().st_size for path in files)
        if size >= 900 * 1024 * 1024:
            raise ValueError("Generated site exceeds its GitHub Pages size budget")
        print(f"LavaLabs static demo: {len(files)} files, {size / 1024**2:.1f} MiB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=lambda value: Path(value).resolve())
    parser.add_argument("--base", default="/LavaLabs")
    args = parser.parse_args()
    if not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)*", args.base):
        parser.error("--base requires a root-relative site directory without a trailing slash")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("--output must be empty")
    os.environ.pop("LAVALABS_LOCAL_ARCHIVE", None)
    Export(args.output, args.base).build()
