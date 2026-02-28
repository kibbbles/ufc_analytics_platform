"""core/middleware.py — Custom ASGI middleware for the UFC Analytics API.

Provides:
  - RequestIDMiddleware  : stamps every request with a UUID (X-Request-ID header)
  - TimingMiddleware     : logs method, path, status, and duration per request

Both middleware classes use Starlette's BaseHTTPMiddleware and integrate with
the JSON logger configured in core/logging.py.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response.

    Sets:
      - request.state.request_id  — available to route handlers and other middleware
      - X-Request-ID response header — visible to API clients for log correlation
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and wall-clock duration for every request.

    Reads request.state.request_id set by RequestIDMiddleware (must be added
    after TimingMiddleware so RequestID runs first).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
