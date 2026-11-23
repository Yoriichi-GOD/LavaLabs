"""Public evidence is reachable while restricted row artifacts remain absent."""
from fastapi.testclient import TestClient
from lavalabs.server import create_app


def test_aggregate_view_and_report_are_served_without_competition_rows():
    with TestClient(create_app()) as client:
        home=client.get('/').text
        assert 'id="atmospheric-evidence"' in home
        value=client.get('/ui/atmospheric/results.json')
        assert value.status_code==200 and value.json()['receipt_kind']=='curated_aggregate'
        report=client.get('/ui/atmospheric/LavaLabs-Obscura-Research.pdf')
        assert report.status_code==200 and report.content.startswith(b'%PDF-')
        for name in ['train.csv','test.csv','submission_selected.csv','lavalabs_features_v1.npz']:
            assert client.get('/ui/atmospheric/'+name).status_code==404
