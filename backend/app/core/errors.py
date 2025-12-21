"""
API error types and exception handlers.

- Defines a small hierarchy of ApiError exceptions.
- Maps errors to a consistent JSON shape for clients.
- Registers FastAPI exception handlers with graceful fallbacks.

Compatible with Pydantic v1 and v2 (model_dump/dict handling).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Pydantic compatibility (v2 preferred, v1 fallback)
try:
    from pydantic import BaseModel, Field, ValidationError  # type: ignore
except Exception:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore

    try:
        from pydantic import ValidationError as _ValidationError  # type: ignore
        ValidationError = _ValidationError  # type: ignore
    except Exception:  # pragma: no cover
        class ValidationError(Exception):  # type: ignore
            pass


__all__ = [
    "ApiError",
    "NotFoundError",
    "ConflictError",
    "ErrorBody",
    "ErrorResponse",
    "register_exception_handlers",
]


# -------------------------------
# Error response models
# -------------------------------

class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict = Field(default_factory=dict, description="Optional structured details")


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: Optional[str] = Field(default=None, description="Client-supplied correlation/request id")


# -------------------------------
# Exception types
# -------------------------------

class ApiError(Exception):
    """
    Base API error with HTTP status and machine code.
    """
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ConflictError(ApiError):
    status_code = 409
    code = "conflict"


# -------------------------------
# Handlers
# -------------------------------

def _make_json_response(request: Request, exc: ApiError) -> JSONResponse:
    # Accept common correlation headers
    req_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")

    body = ErrorResponse(
        error=ErrorBody(code=exc.code, message=exc.message, details=exc.details or {}),
        request_id=req_id,
    )
    # Pydantic v2 uses model_dump; v1 uses dict
    content = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    return JSONResponse(status_code=exc.status_code, content=content)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI expects handlers typed as (Request, Exception) -> Response.

    - ApiError: mapped directly.
    - Pydantic ValidationError: mapped to 422 validation_error with details.
    - Other exceptions: mapped to 500 server_error.
    """
    if isinstance(exc, ApiError):
        return _make_json_response(request, exc)

    if isinstance(exc, ValidationError):
        details: dict[str, Any] = {}
        if hasattr(exc, "errors"):
            try:
                details = {"errors": exc.errors()}  # type: ignore[attr-defined]
            except Exception:
                details = {"error": str(exc)}
        else:
            details = {"error": str(exc)}
        err = ApiError("Validation error", details=details)
        err.status_code = 422
        err.code = "validation_error"
        return _make_json_response(request, err)

    generic = ApiError("Internal server error")
    generic.status_code = 500
    generic.code = "server_error"
    return _make_json_response(request, generic)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    generic = ApiError("Internal server error")
    generic.status_code = 500
    generic.code = "server_error"
    return _make_json_response(request, generic)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers on the FastAPI app.

    AuthError is registered if available without creating a hard dependency.
    """
    # Core mappings
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(ValidationError, api_error_handler)
    app.add_exception_handler(NotFoundError, api_error_handler)
    app.add_exception_handler(ConflictError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    # Optional: map service-layer auth error if present
    try:
        # Lazy import to avoid strict dependency from core -> services
        from app.services.auth_service import AuthError as _AuthError  # noqa: WPS433
        app.add_exception_handler(_AuthError, api_error_handler)
    except Exception:
        # If auth service is absent or import fails, skip gracefully
        pass