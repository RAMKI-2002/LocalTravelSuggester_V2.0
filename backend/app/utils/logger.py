"""Structured JSON logging + per-request ID middleware."""

from __future__ import annotations

import json
import logging
import secrets
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_obj["request_id"] = request_id
        return json.dumps(log_obj)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attaches a short random request-id to each request for log correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = secrets.token_hex(6)
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = request_id
        logging.getLogger(__name__).info(
            "%s %s -> %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            extra={"request_id": request_id},
        )
        return response
