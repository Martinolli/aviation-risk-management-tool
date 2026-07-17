import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.request_context import reset_request_id, set_request_id

logger = logging.getLogger("app.request")

SAFE_REQUEST_HEADERS = {"user-agent", "content-type", "accept", "origin"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(settings.request_id_header) or str(
            uuid.uuid4()
        )
        token = set_request_id(request_id)
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.headers[settings.request_id_header] = request_id
            if settings.enable_request_logging:
                _log_request_completion(request, response.status_code, duration_ms)
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            if settings.enable_request_logging:
                logger.exception(
                    "Unhandled request exception method=%s path=%s duration_ms=%.2f",
                    request.method,
                    request.url.path,
                    duration_ms,
                )
            raise
        finally:
            reset_request_id(token)


def _log_request_completion(
    request: Request,
    status_code: int,
    duration_ms: float,
) -> None:
    parts: list[str] = [
        "request_completed",
        f"method={request.method}",
        f"path={request.url.path}",
    ]
    if settings.log_response_status:
        parts.append(f"status_code={status_code}")
    if settings.log_request_duration:
        parts.append(f"duration_ms={duration_ms:.2f}")
    if settings.log_request_headers:
        safe_headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() in SAFE_REQUEST_HEADERS
        }
        parts.append(f"headers={safe_headers}")
    logger.info(" ".join(parts))
