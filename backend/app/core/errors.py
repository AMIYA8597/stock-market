from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse


def _error_code_for_status(status_code: int) -> ErrorCode:
    mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        409: ErrorCode.ALREADY_EXISTS,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        location = error.get("loc") or []
        field = (
            ".".join(str(part) for part in location if part not in {"body", "query", "path", "header"})
            or None
        )
        details.append(
            ErrorDetail(
                field=field,
                message=error.get("msg", "Invalid value"),
                code=str(error.get("type", "invalid_request")).upper(),
            )
        )

    payload = ErrorResponse.create(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation failed. Please check your input.",
        details=details,
    ).model_dump(mode="json")
    return JSONResponse(status_code=400, content=payload)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"success", "error", "request_id"}.issubset(exc.detail.keys()):
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)

    code = _error_code_for_status(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    payload = ErrorResponse.create(code=code, message=message).model_dump(mode="json")
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
