# tests/test_health.py
# Smoke test: confirm the /health endpoint returns 200 and correct JSON.
# Uses the shared `client` fixture from conftest.py (in-memory SQLite, no real DB needed).

def test_health_check(client):
    """GET /health should return 200 with status 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
