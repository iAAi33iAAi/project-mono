"""Smoke tests for the /health endpoint."""


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_method_not_allowed(client):
    resp = client.post("/health")
    assert resp.status_code == 405
