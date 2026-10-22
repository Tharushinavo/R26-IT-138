"""Fail-closed Supabase access-token verification using asymmetric JWKS."""

import asyncio
from functools import lru_cache
from threading import Lock
from time import monotonic
from typing import Any, Protocol

import jwt
from fastapi import Depends, Request
from jwt import PyJWKClient, PyJWKSet
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationRequiredError
from app.domain.principal import AuthenticatedPrincipal


ALLOWED_ALGORITHMS = frozenset({"RS256", "ES256"})


class ControlledJwksClient(PyJWKClient):
    """TTL cache plus rate-limited forced refresh for safe key rotation."""

    def __init__(self, uri: str, *, lifespan: int, timeout: float = 5) -> None:
        super().__init__(
            uri,
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=lifespan,
            timeout=timeout,
        )
        self._refresh_lock = Lock()
        self._last_forced_refresh = 0.0
        self._refresh_cooldown = min(30.0, max(5.0, lifespan / 10))

    @staticmethod
    def _find_key(jwk_set: PyJWKSet, kid: str) -> Any | None:
        return next((key for key in jwk_set.keys if key.key_id == kid), None)

    def get_signing_key(self, kid: str) -> Any:
        key = self._find_key(self.get_jwk_set(), kid)
        if key is not None:
            return key
        with self._refresh_lock:
            key = self._find_key(self.get_jwk_set(), kid)
            now = monotonic()
            if key is None and now - self._last_forced_refresh >= self._refresh_cooldown:
                key = self._find_key(self.get_jwk_set(refresh=True), kid)
                self._last_forced_refresh = now
        if key is None:
            raise PyJWKClientError("Unable to find a signing key that matches the token")
        return key


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class SupabaseJwtVerifier:
    def __init__(self, settings: Settings, jwks_client: SigningKeyClient | None = None) -> None:
        self._issuer = settings.supabase_jwt_issuer
        self._audience = settings.supabase_jwt_audience
        self._configured = bool(self._issuer and settings.supabase_jwks_url)
        self._jwks_client = jwks_client or ControlledJwksClient(
            settings.supabase_jwks_url or "https://invalid.local/jwks",
            lifespan=settings.supabase_jwks_cache_ttl_seconds,
            timeout=5,
        )

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if not self._configured:
            raise AuthenticationRequiredError()
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm not in ALLOWED_ALGORITHMS or not isinstance(key_id, str) or not key_id:
                raise InvalidTokenError("unsupported token header")
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            options = {
                "require": ["exp", "iss", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": self._audience is not None,
                "verify_sub": True,
            }
            claims = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=[algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options=options,
                # Small clock-skew tolerance against `exp`/`iat`/`nbf`. Supabase issues tokens from
                # its own clock; this server's clock is never guaranteed to be perfectly
                # synchronized with it (ordinary NTP jitter in production, or a VM clock that lags
                # briefly after a host resumes from sleep in local development) -- without leeway a
                # token minted and used within the same second can be rejected as "not yet valid"
                # purely from a few hundred milliseconds of drift, which is not a security property
                # worth enforcing that tightly. 30s is well inside what every major JWT library
                # documents as a normal leeway default range and far smaller than the token's own
                # 1-hour lifetime.
                leeway=30,
            )
        except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
            raise AuthenticationRequiredError() from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationRequiredError()
        email_claim = claims.get("email")
        email_verified = claims.get("email_verified") is True or bool(
            claims.get("email_confirmed_at")
        )
        email = email_claim if isinstance(email_claim, str) and email_verified else None
        return AuthenticatedPrincipal(user_id=subject, email=email)


@lru_cache
def get_jwt_verifier() -> SupabaseJwtVerifier:
    return SupabaseJwtVerifier(get_settings())


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise AuthenticationRequiredError()
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise AuthenticationRequiredError()
    return parts[1]


async def get_authenticated_principal(
    token: str = Depends(bearer_token),
    verifier: SupabaseJwtVerifier = Depends(get_jwt_verifier),
) -> AuthenticatedPrincipal:
    return await asyncio.to_thread(verifier.verify, token)
