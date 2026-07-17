import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.request_context import get_request_id

PLAIN_LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
)
_HANDLER_MARKER = "_aviation_risk_logging_handler"
_FACTORY_CONFIGURED = False
_ORIGINAL_LOG_RECORD_FACTORY = logging.getLogRecordFactory()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": record.request_id,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _install_log_record_factory() -> None:
    global _FACTORY_CONFIGURED
    if _FACTORY_CONFIGURED:
        return

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = _ORIGINAL_LOG_RECORD_FACTORY(*args, **kwargs)
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return record

    logging.setLogRecordFactory(record_factory)
    _FACTORY_CONFIGURED = True


def _formatter_for(settings: Settings) -> logging.Formatter:
    is_json_logging = getattr(
        settings,
        "is_json_logging",
        getattr(settings, "log_format", "plain") == "json",
    )
    if is_json_logging:
        return JsonLogFormatter()
    return logging.Formatter(PLAIN_LOG_FORMAT)


def configure_logging(settings: Settings) -> None:
    _install_log_record_factory()
    normalized_log_level = getattr(
        settings,
        "normalized_log_level",
        getattr(settings, "log_level", "INFO"),
    )
    level = getattr(logging, normalized_log_level)
    formatter = _formatter_for(settings)
    request_id_filter = RequestIdFilter()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    app_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if getattr(handler, _HANDLER_MARKER, False)
        ),
        None,
    )
    if app_handler is None:
        app_handler = logging.StreamHandler(sys.stdout)
        setattr(app_handler, _HANDLER_MARKER, True)
        root_logger.addHandler(app_handler)

    app_handler.setLevel(level)
    app_handler.setFormatter(formatter)
    if not any(isinstance(item, RequestIdFilter) for item in app_handler.filters):
        app_handler.addFilter(request_id_filter)

    for logger_name in [
        "app",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if not any(isinstance(item, RequestIdFilter) for item in logger.filters):
            logger.addFilter(request_id_filter)
