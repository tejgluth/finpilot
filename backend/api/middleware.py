from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
try:
    import structlog
except ImportError:  # pragma: no cover
    import logging

    class _FallbackStructlog:
        @staticmethod
        def get_logger(name: str):
            return logging.getLogger(name)

    structlog = _FallbackStructlog()  # type: ignore[assignment]


logger = structlog.get_logger("finpilot.api")


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.complete",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
