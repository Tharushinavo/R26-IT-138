"""Offline deterministic Supabase JWT and identity endpoint tests."""

import json
import logging
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import PyJWK
from jwt.exceptions import PyJWKClientError

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.infrastructure.auth import ControlledJwksClient, SupabaseJwtVerifier, get_jwt_verifier
from app.main import app


ISSUER = "https://test-project.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def settings() -> Settings:
    return Settings(
        app_env="test",
        backend_code_version="test",
        database_url="postgresql://user:pass@db/test",
        log_level="INFO",
        cors_allowed_origins=(),
        supabase_url="https://test-project.supabase.co",
        supabase_jwt_issuer=ISSUER,
        supabase_jwt_audience=AUDIENCE,
        supabase_jwks_url="https://test-project.supabase.co/auth/v1/.well-known/jwks.json",
        supabase_jwks_cache_ttl_seconds=300,
    )


def key_material(kid: str) -> tuple[Any, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    return private_key, jwk


KEY_1, JWK_1 = key_material("key-1")
KEY_2, JWK_2 = key_material("key-2")


class StaticJwksClient:
    def __init__(self, keys: list[dict[str, Any]]) -> None:
        self.keys = keys

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        kid = jwt.get_unverified_header(token).get("kid")
        for key in self.keys:
            if key["kid"] == kid:
                return PyJWK.from_dict(key)
        raise PyJWKClientError("unknown key")


class RotatingJwksClient(ControlledJwksClient):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__("https://offline.invalid/jwks", lifespan=300, timeout=1)
        self.responses = responses
        self.fetch_count = 0

    def fetch_data(self) -> dict[str, Any]:
        response = self.responses[min(self.fetch_count, len(self.responses) - 1)]
        self.fetch_count += 1
        self.jwk_set_cache.put(response)
        return response


def make_token(
    *,
    key: Any = KEY_1,
    kid: str = "key-1",
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    expires_delta: timedelta = timedelta(minutes=5),
    algorithm: str = "RS256",
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "user-123",
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "exp": now + expires_delta,
        "email": "verified@example.test",
        "email_verified": True,
        "role": "authenticated",
        "user_metadata": {"private": "not-exposed"},
    }
    claims.update(extra_claims or {})
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


def verifier(keys: list[dict[str, Any]] | None = None) -> SupabaseJwtVerifier:
    return SupabaseJwtVerifier(settings(), StaticJwksClient(keys or [JWK_1]))


def assert_rejected(token: str, custom_verifier: SupabaseJwtVerifier | None = None) -> None:
    with pytest.raises(Exception) as caught:
        (custom_verifier or verifier()).verify(token)
    assert type(caught.value).__name__ == "AuthenticationRequiredError"


def test_missing_and_malformed_authorization_headers() -> None:
    client = TestClient(app)
    missing = client.get("/api/v1/me")
    malformed = client.get("/api/v1/me", headers={"Authorization": "Basic credentials"})
    assert missing.status_code == malformed.status_code == 401
    assert missing.json()["error"]["request_id"] == missing.headers["X-Request-ID"]
    assert malformed.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        # Must fall OUTSIDE the 30-second clock-skew leeway `SupabaseJwtVerifier` allows on
        # `exp`/`iat`/`nbf` (app/infrastructure/auth.py). This was -1s, which the leeway
        # swallowed once that leeway was added (2026-09-14): the token verified, and this
        # fail-closed case silently stopped asserting anything. -2 minutes is unambiguously
        # expired at any tolerance this server would reasonably carry.
        make_token(expires_delta=timedelta(minutes=-2)),
        make_token(issuer="https://wrong.example/auth/v1"),
        make_token(audience="wrong-audience"),
        make_token(key=KEY_2),
        make_token(kid="unknown-key"),
    ],
    ids=["malformed", "expired", "wrong-issuer", "wrong-audience", "invalid-signature", "unknown-kid"],
)
def test_invalid_tokens_fail_closed(token: str) -> None:
    assert_rejected(token)


def test_not_before_is_validated() -> None:
    future = datetime.now(UTC) + timedelta(minutes=5)
    assert_rejected(make_token(extra_claims={"nbf": future}))


def test_expiry_leeway_is_bounded() -> None:
    """The clock-skew tolerance on `exp` is a narrow allowance, not an open window.

    The verifier deliberately accepts a token a few seconds past `exp` so ordinary NTP jitter (or
    a VM clock that lags after the host resumes) cannot reject a token minted seconds earlier.
    That tolerance is 30s. This pins the far side of it: 90 seconds past `exp` is expired, and
    stays expired. Without this, widening `leeway` later would quietly turn the "expired" case in
    `test_invalid_tokens_fail_closed` back into a token the verifier accepts -- which is exactly
    how that case stopped testing anything the first time.
    """
    assert_rejected(make_token(expires_delta=timedelta(seconds=-90)))


def test_subject_is_required_and_nonempty() -> None:
    assert_rejected(make_token(extra_claims={"sub": ""}))


def test_unsupported_algorithm_is_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "user-123", "iss": ISSUER, "aud": AUDIENCE, "exp": now + timedelta(minutes=5)},
        "unsafe-shared-secret-that-is-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "key-1"},
    )
    assert_rejected(token)


def test_valid_jwt_and_me_return_only_approved_fields() -> None:
    token = make_token()
    local_verifier = verifier()
    app.dependency_overrides[get_jwt_verifier] = lambda: local_verifier
    try:
        response = TestClient(app).get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}", "X-Request-ID": "auth-valid-123"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "auth-valid-123"
    assert response.json() == {"user_id": "user-123", "email": "verified@example.test"}
    assert "role" not in response.text
    assert "user_metadata" not in response.text


def test_unverified_email_is_not_exposed() -> None:
    principal = verifier().verify(make_token(extra_claims={"email_verified": False}))
    assert principal.email is None


def test_unknown_kid_forces_one_refresh_and_supports_rotation() -> None:
    rotating_client = RotatingJwksClient(
        [{"keys": [JWK_1]}, {"keys": [JWK_1, JWK_2]}]
    )
    rotating_verifier = SupabaseJwtVerifier(settings(), rotating_client)
    principal = rotating_verifier.verify(make_token(key=KEY_2, kid="key-2"))
    assert principal.user_id == "user-123"
    assert rotating_client.fetch_count == 2
    assert_rejected(
        make_token(kid="kid-spray-attempt"),
        rotating_verifier,
    )
    assert rotating_client.fetch_count == 2


def test_token_and_credentials_do_not_appear_in_logs() -> None:
    token = make_token()
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("studentapp.http")
    logger.addHandler(handler)
    app.dependency_overrides[get_jwt_verifier] = lambda: verifier()
    try:
        response = TestClient(app).get(
            "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
        )
    finally:
        app.dependency_overrides.clear()
        logger.removeHandler(handler)
    assert response.status_code == 200
    logs = stream.getvalue()
    assert token not in logs
    assert "Authorization" not in logs
    assert "unsafe-shared-secret" not in logs
    assert "postgresql://" not in logs
