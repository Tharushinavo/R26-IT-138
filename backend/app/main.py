"""FastAPI application entry point."""

import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.b_learner import router as b_learner_router
from app.api.routes.b_session import router as b_session_router
from app.api.routes.c_session import router as c_session_router
from app.api.routes.c_task import router as c_task_router
from app.api.routes.classroom_membership import router as classroom_membership_router
from app.api.routes.d_profile import router as d_profile_router
from app.api.routes.health import router as health_router
from app.api.routes.identity import router as identity_router
from app.api.routes.profile_classroom import router as profile_classroom_router
from app.core.config import get_settings
from app.core.errors import error_response, install_error_handlers
from app.core.logging import configure_logging, request_log_fields
from app.core.request_context import bind_request_id, reset_request_id
from app.infrastructure.database import dispose_database


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
logger = logging.getLogger("studentapp.http")


def accepted_request_id(value: str | None) -> str:
    return value if value and REQUEST_ID_PATTERN.fullmatch(value) else str(uuid4())


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unresolved")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await dispose_database()

    application = FastAPI(
        title="Adaptive Math Platform - Component B API",
        version=settings.backend_code_version,
        lifespan=lifespan,
    )
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Idempotency-Key",
            # Sent on every request by frontend/src/api/client.ts, including from the Expo web
            # target — not mobile-only despite the header name. Web is the only platform whose
            # browser enforces CORS, so this was invisible on native and blocked every
            # state-changing request (sign-up, save name, join code, ...) on web only.
            "X-Mobile-App-Version",
        ],
    )

    @application.middleware("http")
    async def request_observability(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = accepted_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        started = perf_counter()
        fields = request_log_fields(settings, method=request.method, route="unresolved")
        logger.info("request started", extra={"event": "http.request.started", **fields})
        try:
            response = await call_next(request)
        except Exception as exc:
            fields["route"] = route_template(request)
            duration_ms = round((perf_counter() - started) * 1000, 3)
            logger.error(
                "request failed",
                extra={
                    "event": "http.request.exception",
                    "exception_type": type(exc).__name__,
                    "response_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "duration_ms": duration_ms,
                    **fields,
                },
            )
            response = error_response(
                request,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
            )
        fields["route"] = route_template(request)
        duration_ms = round((perf_counter() - started) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "event": "http.request.completed",
                "response_status": response.status_code,
                "duration_ms": duration_ms,
                **fields,
            },
        )
        reset_request_id(token)
        return response

    application.include_router(health_router)
    application.include_router(identity_router)
    application.include_router(profile_classroom_router)
    application.include_router(classroom_membership_router)
    application.include_router(b_session_router)
    application.include_router(b_learner_router)
    application.include_router(c_session_router)
    application.include_router(c_task_router)
    # Component D (Component D authorization, owner decision D-011 A2/A3): the six
    # student-side cognitive-profiling routes.
    application.include_router(d_profile_router)
    return application


app = create_app()
