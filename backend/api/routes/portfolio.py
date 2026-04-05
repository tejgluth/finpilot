from __future__ import annotations

from fastapi import APIRouter

from backend.brokers.alpaca_broker import AlpacaBroker
from backend.database import list_backtests, list_trades
from backend.portfolio_state import derive_local_portfolio
from backend.settings.user_settings import default_user_settings


router = APIRouter()


@router.get("/")
async def portfolio_summary():
    trades = await list_trades()
    backtests = await list_backtests(10)
    runtime_settings = default_user_settings()
    broker_snapshot = await AlpacaBroker().get_portfolio_snapshot()
    if broker_snapshot.get("available"):
        local_portfolio = await derive_local_portfolio(runtime_settings.backtest.default_initial_cash)
        summary = {
            **broker_snapshot,
            "history": local_portfolio.get("history", []),
        }
    else:
        summary = await derive_local_portfolio(runtime_settings.backtest.default_initial_cash)
    return {
        "cash": summary["cash"],
        "equity": summary["equity"],
        "daily_pnl": summary["daily_pnl"],
        "positions": summary["positions"],
        "history": summary.get("history", []),
        "trade_count": len(trades),
        "backtest_count": len(backtests),
        "agent_performance": [],
    }


@router.get("/history")
async def performance_history():
    runtime_settings = default_user_settings()
    summary = await derive_local_portfolio(runtime_settings.backtest.default_initial_cash)
    return summary.get("history", [])
