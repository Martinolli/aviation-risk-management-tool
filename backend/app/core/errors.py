from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


_STATUS_CODE_ERROR_CODES = {
    400: ErrorCode.BUSINESS_RULE_VIOLATION,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    500: ErrorCode.INTERNAL_SERVER_ERROR,
}


def error_code_for_status(status_code: int) -> ErrorCode:
    return _STATUS_CODE_ERROR_CODES.get(status_code, ErrorCode.BAD_REQUEST)


def error_response(
    code: ErrorCode | str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build the standard API error response payload."""
    return {
        "error": {
            "code": code.value if isinstance(code, ErrorCode) else code,
            "message": message,
            "details": details or {},
        }
    }


def error_from_http_exception(
    status_code: int,
    detail: Any,
) -> tuple[ErrorCode | str, str, dict[str, Any]]:
    """Normalize legacy and structured HTTPException details."""
    code: ErrorCode | str = error_code_for_status(status_code)
    message = "Request failed."
    details: dict[str, Any] = {}

    if isinstance(detail, str):
        message = detail
    elif isinstance(detail, dict):
        detail_code = detail.get("code")
        if isinstance(detail_code, str) and detail_code:
            code = detail_code

        detail_message = detail.get("message")
        if isinstance(detail_message, str) and detail_message:
            message = detail_message

        detail_details = detail.get("details")
        if isinstance(detail_details, dict):
            details = detail_details
        elif detail_details is not None:
            details = {"detail": detail_details}

    return code, message, details


def validation_error_details(errors: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Expose useful validation metadata without echoing submitted values."""
    return {
        "errors": [
            {
                "type": str(error.get("type", "validation_error")),
                "loc": list(error.get("loc", [])),
                "msg": str(error.get("msg", "Invalid value.")),
            }
            for error in errors
        ]
    }
