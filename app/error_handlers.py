"""global exception handlers for standardized error responses."""

import logging
import traceback
from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import AppError

logger = logging.getLogger(__name__)


def _build_error_response(
    message: str,
    error_code: str,
    status_code: int,
    details: dict | None = None,
) -> JSONResponse:
    """build a standardized json error response."""
    body = {
        "message": message,
        "error_code": error_code,
        "status_code": status_code,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=status_code, content=body)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """handle domain exceptions (AppError subclasses)."""
    details = None
    # include field-level details for domain validation errors
    if hasattr(exc, "fields") and exc.fields:
        details = exc.fields

    return _build_error_response(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=details,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """handle pydantic/fastapi request validation errors."""
    field_errors: dict[str, list[str]] = {}
    for error in exc.errors():
        # build a dot-separated field path from the location tuple
        loc = error.get("loc", ())
        # skip the first element if it's 'body', 'query', or 'path'
        parts = [str(part) for part in loc if part not in ("body",)]
        field_name = ".".join(parts) if parts else "unknown"
        field_errors.setdefault(field_name, []).append(error.get("msg", "invalid"))

    return _build_error_response(
        message="Error de validación en los datos enviados",
        error_code="VALIDATION_ERROR",
        status_code=422,
        details=field_errors,
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """handle unhandled exceptions. logs full traceback, returns generic message."""
    logger.error(
        "unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
    )
    logger.error(traceback.format_exc())

    return _build_error_response(
        message="Error interno del servidor",
        error_code="INTERNAL_ERROR",
        status_code=500,
    )


def register_error_handlers(app) -> None:
    """register all global exception handlers on the fastapi app instance."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
