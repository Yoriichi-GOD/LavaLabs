"""The public demonstration never enumerates an unrelated local archive."""
import json
import re
from jai_extension.flood_bridge import FloodBridge, BridgeError

DEMO_RUNS = frozenset({'event-fe47db331390', 'nepal-syapru-004'})

class DemoBridge(FloodBridge):
    def __init__(self, upstream, session=None, include_archive=False):
        super().__init__(upstream, session=session)
        self.allowed = set(DEMO_RUNS)
        self.include_archive = include_archive

    def permits(self, run_id):
        return self.include_archive or isinstance(run_id, str) and run_id in self.allowed

    def require(self, run_id):
        if not self.permits(run_id):
            raise BridgeError(404, 'Run is outside this LavaLabs demonstration')

    def read(self, path, cap=2*1024*1024):
        match = re.match(r'/runs/([^/]+)/', path)
        if match:
            self.require(match[1])
        raw = super().read(path, cap)
        if path == '/api/runs' and not self.include_archive:
            raw = json.dumps([row for row in json.loads(raw) if self.permits(row.get('run_id'))]).encode()
        return raw
