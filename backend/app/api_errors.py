from http import HTTPStatus

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error_code_from_status(status_code: int) -> str:
    try:
        return f"http_{HTTPStatus(status_code).value}"
    except ValueError:
        return f"http_{status_code}"


def _normalise_detail(detail):
    if isinstance(detail, (dict, list)):
        return detail
    if detail is None:
        return None
    return str(detail)


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = _normalise_detail(exc.detail)
    request.state.api_error_code = _error_code_from_status(exc.status_code)
    request.state.api_error_message = detail if isinstance(detail, str) else HTTPStatus(exc.status_code).phrase
    error_payload = {
        "error": {
            "code": _error_code_from_status(exc.status_code),
            "message": detail if isinstance(detail, str) and detail else HTTPStatus(exc.status_code).phrase,
        }
    }
    if detail is not None and not isinstance(detail, str):
        error_payload["error"]["details"] = detail
    return JSONResponse(status_code=exc.status_code, content=error_payload)


def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request.state.api_error_code = "validation_error"
    request.state.api_error_message = "Validation error"
    details = []
    for error in exc.errors():
        details.append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error",
                "details": details,
            }
        },
    )


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request.state.api_error_code = "internal_server_error"
    request.state.api_error_message = "Une erreur interne est survenue"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Une erreur interne est survenue",
            }
        },
    )