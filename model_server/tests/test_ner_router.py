from fastapi.testclient import TestClient

from model_server.main import app


def test_ner_endpoint_returns_grouped_entities():
    client = TestClient(app)
    response = client.post(
        "/ner",
        json={
            "title": "BUG: read_csv crashes on pandas 2.2",
            "body": "ValueError from pandas/io/parsers.py on Windows for CSV.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert "read_csv" in data["grouped"]["function"]
