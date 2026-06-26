"""Standardized error response schemas for all API endpoints.

All error responses follow a consistent format:
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": [{"field": "...", "message": "...", "code": "..."}]
  },
  "request_id": "uuid-for-tracing"
}

This ensures:
1. Consistent error format across all endpoints
2. Machine-readable error codes for clients
3. Field-level validation errors
4. Request tracing via request_id
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    """Standardized error codes — single source of truth for all errors.

    Each code is returned in error.code field for client-side handling.
    Clients can switch on these codes rather than parsing error messages.
    """

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_EMAIL = "INVALID_EMAIL"
    PASSWORD_TOO_WEAK = "PASSWORD_TOO_WEAK"
    INVALID_PHONE = "INVALID_PHONE"

    # Authentication errors (401)
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    MFA_REQUIRED = "MFA_REQUIRED"
    INVALID_2FA = "INVALID_2FA"

    # Authorization errors (403)
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"

    # Resource errors (404, 409, 422)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CANNOT_DELETE = "CANNOT_DELETE"
    UNPROCESSABLE = "UNPROCESSABLE"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # Payment errors (402, 402-specific)
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_PAYMENT_METHOD = "INVALID_PAYMENT_METHOD"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"

    # Server errors (500, 503)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class ErrorDetail(BaseModel):
    """Single field-level error detail (used for validation errors)."""

    field: str | None = Field(
        None,
        description="Field name if this is a validation error (e.g., 'email', 'password')",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Human-readable error message for this field",
    )
    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'INVALID_EMAIL')",
    )


class ErrorInfo(BaseModel):
    """Container for error information."""

    code: str = Field(
        ...,
        description="Machine-readable error code from ErrorCode enum",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Human-readable error message (user-safe, no internal details)",
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Field-level error details (for validation errors)",
    )


class ErrorResponse(BaseModel):
    """Standard error response format for all API endpoints.

    Every error response must use this format to ensure:
    - Consistent structure across all endpoints
    - Request tracing via request_id
    - Field-level validation error details
    - Machine-readable error codes

    Example:
        {
            "success": false,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed. Please check your input.",
                "details": [
                    {
                        "field": "email",
                        "code": "INVALID_EMAIL",
                        "message": "Email address is not valid"
                    }
                ]
            },
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """

    success: bool = Field(
        False,
        description="Always false for error responses",
    )
    error: ErrorInfo = Field(
        ...,
        description="Error details",
    )
    request_id: str = Field(
        ...,
        description="Unique request ID for tracing (UUID v4)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when error was generated",
    )

    @classmethod
    def create(
        cls,
        code: ErrorCode | str,
        message: str,
        details: list[ErrorDetail] | None = None,
        request_id: str | None = None,
    ) -> ErrorResponse:
        """Factory method to create a standardized error response.

        Args:
            code: ErrorCode enum or string code
            message: Human-readable error message
            details: Optional list of field-level error details
            request_id: Optional UUID; generated if not provided

        Returns:
            ErrorResponse: Complete error response ready to return to client

        Example:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Please check your input",
                    details=[
                        ErrorDetail(
                            field="email",
                            code="INVALID_EMAIL",
                            message="Email format invalid"
                        )
                    ]
                ).dict()
            )
        """
        code_value = code.value if isinstance(code, ErrorCode) else code
        if len(message) > 512:
            message = message[:509] + "..."

        return cls(
            success=False,
            error=ErrorInfo(
                code=code_value,
                message=message,
                details=details or [],
            ),
            request_id=request_id or str(uuid4()),
            timestamp=datetime.now(UTC),
        )

    def dict(self, **kwargs):
        """Override dict() to match FastAPI HTTPException requirements."""
        return self.model_dump(mode="json", **kwargs)


class SuccessResponse(BaseModel):
    """Standard success response envelope (optional; for consistency)."""

    success: bool = Field(True, description="Always true for success responses")
    data: dict | list | None = Field(
        None,
        description="Response data (varies by endpoint)",
    )
    request_id: str = Field(
        ...,
        description="Unique request ID for tracing",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when response was generated",
    )
