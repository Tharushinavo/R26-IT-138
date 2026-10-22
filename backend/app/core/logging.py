"""Minimal JSON structured logging without sensitive request content."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.request_context import current_request_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": getattr(record, "request_id", None) or current_request_id(),
        }
        for field in (
            "http_method", "route", "response_status", "duration_ms",
            "application_version", "environment", "exception_type",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def request_log_fields(settings: Settings, *, method: str, route: str) -> dict[str, Any]:
    return {
        "http_method": method,
        "route": route,
        "application_version": settings.backend_code_version,
        "environment": settings.app_env,
    }
