from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.models import ErrorResponse


def api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    debug_hint: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            code=code,
            message=message,
            details=details or {},
            debug_hint=debug_hint,
        ).model_dump(),
    )


def _error_response(status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message", "details", "debug_hint"}.issubset(exc.detail):
        return _error_response(exc.status_code, exc.detail)

    return _error_response(
        exc.status_code,
        ErrorResponse(
            code="http_error",
            message=str(exc.detail),
            details={"path": request.url.path},
            debug_hint="Raise errors with core.errors.api_error to attach a domain-specific code.",
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        422,
        ErrorResponse(
            code="validation_error",
            message="Request validation failed.",
            details={"errors": exc.errors(), "path": request.url.path},
            debug_hint="Check the request body, path parameters, query parameters, and multipart fields.",
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        500,
        ErrorResponse(
            code="internal_server_error",
            message="An unexpected server error occurred.",
            details={"path": request.url.path},
            debug_hint=f"Check backend logs for {exc.__class__.__name__}.",
        ).model_dump(),
    )
