"""Read only the LavaLabs-owned saved runs, with the same freeze checks as before."""
import json
import re

from components.floodlab.floodlab import server as flood
from jai_extension.flood_bridge import BridgeError, FloodBridge, MAX_JSON, MIME, RUN_ID

DEMO_RUNS = frozenset({'event-fe47db331390', 'nepal-syapru-004'})
JOB_ID = re.compile(r'event-[a-f0-9]{12}\Z')


class DemoBridge(FloodBridge):
    def __init__(self, *, include_archive=False, check=None):
        self.include_archive = include_archive
        self.check = check or (lambda: None)

    def for_job(self, check):
        return DemoBridge(include_archive=self.include_archive, check=check)

    def permits(self, run_id):
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            return False
        return (self.include_archive or run_id in DEMO_RUNS or
                bool(JOB_ID.fullmatch(run_id) and (flood.ROOT / 'data/jobs' / f'{run_id}.json').is_file()))

    def require(self, run_id):
        if not self.permits(run_id):
            raise BridgeError(404, 'Run is outside this LavaLabs demonstration')

    def artifact_path(self, run_id, name):
        self.require(run_id)
        root = flood.RUNS.resolve()
        target = (root / run_id / name).resolve()
        if name not in MIME or not target.is_relative_to(root) or not target.is_file():
            raise BridgeError(404, 'Saved run or artifact not found')
        return target

    def listing(self):
        runs = flood.RUNS.resolve()
        results = []
        for folder in sorted(runs.iterdir()) if runs.is_dir() else []:
            if not self.permits(folder.name) or not folder.is_dir() or not (folder / 'freeze.json').is_file():
                continue
            try:
                results.append(json.loads(self.read(f'/runs/{folder.name}/result.json')))
            except (BridgeError, ValueError):
                continue
        return results

    def read(self, path, cap=MAX_JSON):
        self.check()
        if path == '/api/health':
            raw = json.dumps(flood.health()).encode()
        elif path == '/api/runs':
            raw = json.dumps(self.listing()).encode()
        else:
            match = re.fullmatch(r'/runs/([^/]+)/([^/]+)', path)
            if not match:
                raise BridgeError(404, 'Unknown saved evidence path')
            target = self.artifact_path(*match.groups())
            with target.open('rb') as stream:
                raw = stream.read(cap + 1)
        self.check()
        if len(raw) > cap:
            raise BridgeError(413, 'Artifact exceeds transfer limit')
        return raw
