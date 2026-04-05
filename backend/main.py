from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.api.middleware import register_middleware
from backend.api.routes import agents, audit, backtest, permissions, portfolio, setup, strategy, trading
from backend.api.routes import settings as settings_routes
from backend.config import settings
from backend.database import init_db
from backend.security.audit_logger import AuditLogger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    AuditLogger.log("system", "startup", {"version": "0.1.0", "alpaca_mode": settings.alpaca_mode})
    yield
    AuditLogger.log("system", "shutdown", {})


app = FastAPI(
    title="FinPilot",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug_logging else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
register_middleware(app)

app.include_router(setup.router, prefix="/api/setup")
app.include_router(strategy.router, prefix="/api/strategy")
app.include_router(agents.router, prefix="/api/agents")
app.include_router(backtest.router, prefix="/api/backtest")
app.include_router(portfolio.router, prefix="/api/portfolio")
app.include_router(trading.router, prefix="/api/trading")
app.include_router(audit.router, prefix="/api/audit")
app.include_router(permissions.router, prefix="/api/permissions")
app.include_router(settings_routes.router, prefix="/api/settings")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "alpaca_mode": settings.alpaca_mode,
        "ai_provider": settings.ai_provider,
        "data_sources": settings.available_data_sources(),
    }


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.backend_port, reload=False)
