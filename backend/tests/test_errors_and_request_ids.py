"""Stable errors and request correlation tests."""

import json
import logging
from io import StringIO

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.errors import AuthenticationRequiredError, ConflictError
from app.main import app


router = APIRouter(prefix="/_test", include_in_schema=False)


@router.get("/conflict")
async def conflict() -> None:
    raise ConflictError()


@router.get("/auth-shaped")
async def auth_shaped() -> None:
    raise AuthenticationRequiredError()


@router.get("/unexpected")
async def unexpected() -> None:
    raise RuntimeError("database-password-and-internal-path")


if not any(getattr(route, "path", "").startswith("/_test") for route in app.routes):
    app.include_router(router)


def test_valid_request_id_is_preserved() -> None:
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": "client-123"})
    assert response.headers["X-Request-ID"] == "client-123"


def test_unsafe_request_id_is_replaced() -> None:
    unsafe = "bad request id\n" + "x" * 100
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": unsafe})
    assert response.headers["X-Request-ID"] != unsafe
    assert len(response.headers["X-Request-ID"]) <= 64


def test_not_found_uses_versioned_contract() -> None:
    response = TestClient(app).get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_conflict_and_authentication_shaped_errors() -> None:
    client = TestClient(app)
    assert client.get("/_test/conflict").json()["error"]["code"] == "CONFLICT"
    auth = client.get("/_test/auth-shaped")
    assert auth.status_code == 401
    assert auth.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_unexpected_error_is_safe() -> None:
    response = TestClient(app, raise_server_exceptions=False).get("/_test/unexpected")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "database-password" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_structured_completion_log_contains_request_id() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    from app.core.logging import JsonFormatter

    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("studentapp.http")
    logger.addHandler(handler)
    try:
        TestClient(app).get("/health/live", headers={"X-Request-ID": "log-123"})
    finally:
        logger.removeHandler(handler)
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    completed = next(item for item in events if item["event"] == "http.request.completed")
    assert completed["request_id"] == "log-123"
    assert completed["response_status"] == 200
    assert completed["application_version"]
    assert completed["environment"]
