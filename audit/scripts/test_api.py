"""Integration tests for the local inference API using FastAPI TestClient."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["features"] == 61
    assert body["threshold"] == 0.50


def test_screen_by_claim_id():
    r = client.post("/screen", json={"claim_id": 719069})
    assert r.status_code == 200
    body = r.json()
    assert body["claim_id"] == 719069
    assert body["prediction"]["warning"] is True
    assert abs(body["prediction"]["pending_risk"] - 0.782) < 1e-3
    assert body["validation"]["total_findings"] >= 1


def test_screen_low_risk_claim():
    r = client.post("/screen", json={"claim_id": 719071})
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"]["warning"] is False
    assert body["prediction"]["recommendation"] == "OK"


def test_screen_claim_not_found():
    r = client.post("/screen", json={"claim_id": 999999999})
    assert r.status_code == 404


def test_screen_missing_input():
    r = client.post("/screen", json={})
    assert r.status_code == 400


def test_screen_schema_version_and_no_target():
    r = client.post("/screen", json={"claim_id": 719069})
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert "target" not in body
    assert "label" not in body


def test_screen_batch():
    r = client.post("/screen/batch", json={"claim_ids": [719069, 719215]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["results"]) == 2


def test_screen_batch_with_missing():
    r = client.post("/screen/batch", json={"claim_ids": [719069, 999999999]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["not_found"] == [999999999]


def test_reproducibility():
    r1 = client.post("/screen", json={"claim_id": 719069}).json()
    r2 = client.post("/screen", json={"claim_id": 719069}).json()
    assert r1["prediction"]["pending_risk"] == r2["prediction"]["pending_risk"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
    print(f"\n{passed}/{len(tests)} API tests passed")
