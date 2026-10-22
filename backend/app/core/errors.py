"""Versioned, user-safe API error contract and centralized handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException


ERROR_SCHEMA_VERSION = "1.0"


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str
    details: dict[str, Any] | list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = ERROR_SCHEMA_VERSION
    error: ErrorBody


class ApplicationError(Exception):
    """Expected application failure safe to represent through the public contract."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "APPLICATION_ERROR"
    message = "The request could not be completed."

    def __init__(self, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(self.code)
        self.details = details


class AuthenticationRequiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTHENTICATION_REQUIRED"
    message = "Authentication is required."


class ResourceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "RESOURCE_NOT_FOUND"
    message = "The requested resource was not found."


class ForbiddenError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "You are not authorized to access this resource."


class ConflictError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "The request conflicts with the current resource state."


class ClassroomNameMismatchError(ApplicationError):
    """A classroom deletion whose typed confirmation did not match the classroom's name.

    The name is the teacher's last deliberate check before a classroom closes, so a mismatch
    is refused on the server too -- a client that skipped the check still cannot delete."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "CLASSROOM_NAME_MISMATCH"
    message = "The confirmation does not match the classroom name."


class TechnicalFailureError(ApplicationError):
    """A network/database/API failure while handling the request. Never a learner-facing
    correctness/BKT outcome — see ``app.application.attempt_submission``."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "TECHNICAL_FAILURE"
    message = "A technical failure occurred; please retry."


class MasteryPayloadRejectedError(ApplicationError):
    """Phase 4b, Q2/B2-c: translates ``app.domain.live_engine_c.errors.
    MasteryPayloadContractValidationError``. ``details`` must be built ONLY from that error's
    ``field_errors`` (``[(loc, type), ...]``, never ``str(exc)``) — the same
    ``[{"location": [...], "type": ...}]`` shape ``install_error_handlers``'s own
    ``RequestValidationError`` handler already uses (``errors.py``, this file), so a client sees
    one consistent validation-error shape across both paths. Never carries a mastery value, a B
    identity field, or any pydantic ``msg``/``input``."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "MASTERY_PAYLOAD_REJECTED"
    message = "The supplied mastery payload failed contract validation."


class ActionPayloadRejectedError(ApplicationError):
    """Phase 5, C-12: translates ``app.domain.live_engine_c.action_payload_validation.
    ActionPayloadValidationError``. ``details`` must be built ONLY from that error's
    ``field_errors`` (``[(loc, type), ...]``), same shape as ``MasteryPayloadRejectedError`` —
    never the submitted value itself, so a malformed/garbled ``action_payload`` never becomes a
    silently-recorded wrong answer (owner's own words: "a malformed payload does not error, it
    becomes a recorded wrong answer... enters the research data as a false negative") — it is
    REJECTED before ``evaluate`` is ever called, proven by the call-counter spy pattern (P4-c)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "ACTION_PAYLOAD_REJECTED"
    message = "The submitted action payload failed structural validation."


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"location": [str(item) for item in error["loc"]], "type": error["type"]}
            for error in exc.errors()
        ]
        return error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="REQUEST_VALIDATION_FAILED",
            message="The request is invalid.",
            details=details,
        )

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        known = {
            401: ("AUTHENTICATION_REQUIRED", "Authentication is required."),
            403: ("FORBIDDEN", "You are not authorized to access this resource."),
            404: ("RESOURCE_NOT_FOUND", "The requested resource was not found."),
            409: ("CONFLICT", "The request conflicts with the current resource state."),
            503: ("SERVICE_UNAVAILABLE", "A required service is unavailable."),
        }
        code, message = known.get(
            exc.status_code, ("HTTP_ERROR", "The request could not be completed.")
        )
        details = exc.detail if isinstance(exc.detail, dict) else None
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
        )
