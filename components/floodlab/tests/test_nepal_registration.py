import json,hashlib,sqlite3
import pytest
from pathlib import Path
from shapely.geometry import shape
B=Path(__file__).resolve().parents[1]
def test_registered_references_and_candidate_coverage():
    d=json.loads((B/'docs/dataset-readiness.json').read_text())
    assert not d['errors'] and len(d['references'])==2 and len(d['catalogue_counts'])==8
    for r in d['references']:
        assert r['role']=='evaluation_only' and r['damage_features_inspected'] is True  # Consumed development evidence; never relabel as untouched.
        p=B/'evaluation_only/emsr'/r['filename']
        if not p.is_file():pytest.skip('Public checkout intentionally excludes local EMSR reference acquisitions')
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    for a in d['areas']:
        candidate=a['recommended_metadata_pair']
        assert candidate and candidate['full_aoi_footprint_coverage'] and candidate['imagery_downloaded']  # Source acquisition is now recorded as complete.
        assert 11.9<candidate['gap_days']<12.1
