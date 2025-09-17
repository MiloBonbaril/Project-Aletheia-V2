import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects the current request id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = request_id_ctx_var.get("-")
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with a stable schema."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        for attr in ("method", "path", "status_code", "duration_ms", "client_host"):
            if hasattr(record, attr):
                log_payload[attr] = getattr(record, attr)

        if record.exc_info:
            log_payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=True)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:  # type: ignore[override]
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()


_configured = False


def configure_logging(level: Optional[str] = None) -> logging.Logger:
    """Configure the application logger with JSON output and request context."""

    global _configured
    if _configured:
        return logging.getLogger("api")

    resolved_level = (level or os.getenv("BACK_LOG_LEVEL", "INFO")).upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(resolved_level)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn").setLevel(resolved_level)

    _configured = True
    return logging.getLogger("api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to the request scope and emit detailed request logs."""

    def __init__(self, app, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger("api.requests")

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_ctx_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.exception(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "client_host": request.client.host if request.client else None,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id
            self.logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "client_host": request.client.host if request.client else None,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return response
        finally:
            request_id_ctx_var.reset(token)
