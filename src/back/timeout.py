import asyncio
import logging
from typing import Optional

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Abort requests that exceed the configured timeout."""

    def __init__(self, app, timeout: float = 10.0, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(app)
        self.timeout = timeout
        self.logger = logger or logging.getLogger("api.timeout")

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            self.logger.warning(
                "Request timed out",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "timeout": self.timeout,
                    "client_host": request.client.host if request.client else None,
                },
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request processing exceeded timeout"},
            )
