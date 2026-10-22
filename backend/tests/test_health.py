"""BE1 infrastructure health endpoint tests."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_liveness_reports_process_only() -> None:
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.headers["X-Request-ID"] == response.json()["request_id"]


def test_readiness_identifies_infrastructure_stage() -> None:
    with patch("app.api.routes.health.probe_database", AsyncMock()):
        response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "infrastructure"
    assert body["checks"]["database_connection"] == "ok"
    assert body["checks"]["migrations"] == "not_checked"
    assert body["checks"]["generator"] == "not_checked"
    assert body["checks"]["authentication"] == "not_checked"


def test_readiness_returns_stable_safe_error_when_database_is_unavailable() -> None:
    with patch("app.api.routes.health.probe_database", AsyncMock(side_effect=OSError("secret raw error"))):
        response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "secret raw error" not in response.text
