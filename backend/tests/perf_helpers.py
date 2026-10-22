"""PERF-01: test-only query profiler.

Counts every statement a SQLAlchemy engine sends (``before_cursor_execute``), records where in ``app/`` it came from, and can
sleep a fixed time per statement to reproduce the cost of a remote database (the dev API talks to Supabase in Singapore,
about 50 ms per round trip). Not imported by anything under ``app/``.

Only statements are counted -- BEGIN / COMMIT are not (they are the route's unit-of-work boundary and are unchanged).

ORIGIN. The ``before_cursor_execute`` hook runs inside SQLAlchemy's greenlet, whose frame chain does not reach the awaiting
application code. So the ``AsyncSession`` entry points are wrapped (while a profile is active) to read the caller's frame chain
-- running coroutines link to their awaiting caller through ``f_back`` -- and stash it in a ContextVar the hook then reads.
"""

from __future__ import annotations

import contextvars
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

_ORIGIN: contextvars.ContextVar = contextvars.ContextVar("perf_origin", default=("?", "?"))
_WRAPPED = ("execute", "scalar", "scalars", "get", "flush", "refresh", "commit", "delete", "merge", "get_one")


def _app_frames_from(frame) -> tuple[str, str]:
    """(innermost app/ frame, innermost app/application|api frame) as 'file:line' relative to app/."""
    innermost = application = ""
    while frame is not None:
        name = frame.f_code.co_filename.replace("\\", "/")
        if "/app/app/" in name and "site-packages" not in name:
            rel = name.split("/app/app/", 1)[1]
            tag = f"{rel}:{frame.f_lineno}"
            innermost = innermost or tag
            if not application and rel.startswith(("application/", "api/")):
                application = tag
        frame = frame.f_back
    return innermost or "?", application or "?"


def _wrap(orig):
    async def wrapper(self, *args, **kwargs):
        token = _ORIGIN.set(_app_frames_from(sys._getframe(1)))
        try:
            return await orig(self, *args, **kwargs)
        finally:
            _ORIGIN.reset(token)

    wrapper.__wrapped_by_perf__ = orig
    return wrapper


@dataclass
class QueryProfile:
    engine: object
    latency_ms: float = 0.0
    statements: list = field(default_factory=list)
    _listener: Optional[object] = None
    _originals: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def __enter__(self) -> "QueryProfile":
        sync_engine = getattr(self.engine, "sync_engine", self.engine)

        def before(conn, cursor, statement, parameters, context, executemany):
            origin, caller = _ORIGIN.get()
            self.statements.append((" ".join(statement.split())[:90], origin, caller))
            if self.latency_ms:
                time.sleep(self.latency_ms / 1000.0)

        self._listener = (sync_engine, before)
        event.listen(sync_engine, "before_cursor_execute", before)
        for name in _WRAPPED:
            orig = getattr(AsyncSession, name, None)
            if orig is not None and not hasattr(orig, "__wrapped_by_perf__"):
                self._originals[name] = orig
                setattr(AsyncSession, name, _wrap(orig))
        return self

    def __exit__(self, *exc) -> None:
        sync_engine, before = self._listener
        event.remove(sync_engine, "before_cursor_execute", before)
        for name, orig in self._originals.items():
            setattr(AsyncSession, name, orig)
        self._originals.clear()

    @property
    def count(self) -> int:
        return len(self.statements)

    def origins(self, n: int = 8, by: str = "origin") -> list[tuple[str, int]]:
        idx = 1 if by == "origin" else 2
        return Counter(s[idx] for s in self.statements).most_common(n)
