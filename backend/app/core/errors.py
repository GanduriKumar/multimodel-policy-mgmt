"""
Standardized API errors and exception handling for FastAPI.

Provides:
- Error response models (ErrorBody, ErrorResponse)
- Custom exceptions (AuthError, ValidationError, NotFoundError, ConflictError)
- FastAPI exception handlers and a registration helper
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

__all__ = [
    "ErrorBody",
    "ErrorResponse",
    "ApiError",
    "AuthError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "register_exception_handlers",
]


# -------------------------------
# Error models
# -------------------------------


class ErrorBody(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g., 'not_found'")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured details")


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: Optional[str] = Field(default=None, description="Correlation id if available")


# -------------------------------
# Exceptions
# -------------------------------


class ApiError(Exception):
    """Base API error with HTTP status and code."""

    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthError(ApiError):
    status_code = 401
    code = "auth_error"


class ValidationError(ApiError):  # Note: not pydantic.ValidationError
    status_code = 400
    code = "validation_error"


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
    req_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    body = ErrorResponse(
        error=ErrorBody(code=exc.code, message=exc.message, details=exc.details or {}),
        request_id=req_id,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _make_json_response(request, exc)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    generic = ApiError("Internal server error")
    generic.status_code = 500
    generic.code = "server_error"
    return _make_json_response(request, generic)


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers on the FastAPI app."""
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(AuthError, api_error_handler)
    app.add_exception_handler(ValidationError, api_error_handler)
    app.add_exception_handler(NotFoundError, api_error_handler)
    app.add_exception_handler(ConflictError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
