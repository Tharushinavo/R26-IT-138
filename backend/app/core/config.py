"""Environment-backed infrastructure settings for BE1."""

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    """Operational settings only; no scientific or learner-policy defaults."""

    app_env: str
    backend_code_version: str
    database_url: str
    log_level: str
    cors_allowed_origins: tuple[str, ...]
    supabase_url: str
    supabase_jwt_issuer: str
    supabase_jwt_audience: str | None
    supabase_jwks_url: str
    supabase_jwks_cache_ttl_seconds: int
    # Connection-pool sizing. Defaults are deliberately well under Supabase's session-mode
    # ceiling: Supavisor caps a project at 15 CLIENT connections in session mode and answers the
    # 16th with `(EMAXCONNSESSION) max clients reached in session mode`. SQLAlchemy's own
    # defaults (pool_size=5, max_overflow=10) permit exactly 15 from a single process, so one
    # API process at full stretch consumes the entire project allowance and anything else that
    # connects -- a second uvicorn worker, the test suite, a dev script -- fails outright.
    db_pool_size: int = 5
    db_max_overflow: int = 2
    # Recycle before a provider-side idle timeout can hand us a dead socket. This is the cheap
    # half of the `pool_pre_ping` trade: pre-ping pays a round trip on EVERY checkout (measured
    # at ~280ms against ap-southeast-1), whereas recycling pays nothing per request and simply
    # retires connections on age.
    db_pool_recycle_seconds: int = 600
    # Left configurable rather than removed: a flaky network can still want per-checkout
    # validation, at the cost above.
    db_pool_pre_ping: bool = False

    @property
    def database_endpoint(self) -> tuple[str, int]:
        parsed = urlparse(self.database_url)
        if parsed.scheme not in {"postgres", "postgresql", "postgresql+asyncpg"} or not parsed.hostname:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL with a hostname")
        return parsed.hostname, parsed.port or 5432


@lru_cache
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    return Settings(
        app_env=getenv("APP_ENV", "development"),
        backend_code_version=getenv("BACKEND_CODE_VERSION", "0.1.0-be1.3"),
        database_url=getenv(
            "DATABASE_URL",
            "postgresql://studentapp:local-development-only@db:5432/studentapp",
        ),
        log_level=getenv("LOG_LEVEL", "INFO").upper(),
        cors_allowed_origins=origins,
        supabase_url=getenv("SUPABASE_URL", ""),
        supabase_jwt_issuer=getenv("SUPABASE_JWT_ISSUER", ""),
        supabase_jwt_audience=getenv("SUPABASE_JWT_AUDIENCE") or None,
        supabase_jwks_url=getenv("SUPABASE_JWKS_URL", ""),
        supabase_jwks_cache_ttl_seconds=max(
            30, min(int(getenv("SUPABASE_JWKS_CACHE_TTL_SECONDS", "300")), 3600)
        ),
        db_pool_size=max(1, min(int(getenv("DB_POOL_SIZE", "5")), 50)),
        db_max_overflow=max(0, min(int(getenv("DB_MAX_OVERFLOW", "2")), 50)),
        db_pool_recycle_seconds=max(60, min(int(getenv("DB_POOL_RECYCLE_SECONDS", "600")), 3600)),
        db_pool_pre_ping=getenv("DB_POOL_PRE_PING", "false").strip().lower()
        in {"1", "true", "yes", "on"},
    )
