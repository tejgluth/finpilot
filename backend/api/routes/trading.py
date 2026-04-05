from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.brokers.alpaca_broker import AlpacaBroker
from backend.config import settings
from backend.database import list_trades, load_state, save_state, store_trade
from backend.guardrails.live_trading import evaluate_live_trading_gates
from backend.guardrails.kill_switch import activate, deactivate, is_active
from backend.guardrails.position_limits import check_position_limits
from backend.portfolio_state import compute_drawdown_metrics, compute_sector_exposure, derive_local_portfolio
from backend.data.adapters import YFinanceAdapter
from backend.models.trade import Order
from backend.permissions.model import UserPermissions
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str
    action: str
    notional_usd: float = Field(gt=0)
    confirm: bool = False
    reasoning: str = ""
    team_id: str | None = None
    execution_snapshot_id: str | None = None


class KillSwitchPayload(BaseModel):
    active: bool
    reason: str = ""


class LiveEnablePayload(BaseModel):
    enabled: bool


async def _runtime_settings() -> UserSettings:
    raw = await load_state("user_settings", None)
    return UserSettings.from_dict(raw) if raw else default_user_settings()


async def _permissions() -> UserPermissions:
    raw = await load_state("user_permissions", None)
    return UserPermissions.from_dict(raw)


@router.get("/status")
async def trading_status():
    permissions = await _permissions()
    runtime_settings = await _runtime_settings()
    active = await is_active()
    is_live_mode = settings.alpaca_mode == "live"
    live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
    return {
        "alpaca_mode": settings.alpaca_mode,
        "permission_level": permissions.level.value,
        "live_risk_acknowledged": permissions.live_trading_acknowledged_risks,
        "live_trading_enabled": permissions.live_trading_enabled,
        "paper_trading_days_completed": live_unlock["paper_trading_days_completed"],
        "live_unlock": live_unlock,
        "mode_notice": (
            "Live mode sends orders to your real Alpaca account only after all four unlock gates pass."
            if is_live_mode
            else "Paper mode is active. Orders stay in paper until you deliberately unlock live trading."
        ),
        "kill_switch": {
            "active": active,
            "reason": "manual stop" if active else "",
        },
    }


@router.post("/order")
async def submit_order(payload: TradeRequest):
    if await is_active():
        raise HTTPException(status_code=409, detail="Kill switch is active.")
    runtime_settings = await _runtime_settings()
    permissions = await _permissions()
    live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
    if settings.alpaca_mode == "live" and not bool(live_unlock["ready"]):
        raise HTTPException(status_code=403, detail="Live trading is locked until all four unlock gates pass.")

    portfolio = await _runtime_portfolio(runtime_settings)
    equity = float(portfolio.get("equity") or runtime_settings.backtest.default_initial_cash)
    positions = portfolio.get("positions", [])
    history = portfolio.get("history", [])
    ticker_profile = await YFinanceAdapter().get_security_profile(payload.ticker)
    proposed_position_pct = (payload.notional_usd / equity) * 100.0 if equity > 0 else 100.0
    daily_loss_pct, total_drawdown_pct = compute_drawdown_metrics(history)
    sector_exposure_pct = compute_sector_exposure(positions, ticker_profile.get("sector"))
    trades_today = _count_trades_today(await list_trades(500))

    runtime_settings.guardrails.kill_switch_active = await is_active()
    limit_check = check_position_limits(
        proposed_position_pct=proposed_position_pct,
        open_positions=len(positions),
        sector_exposure_pct=sector_exposure_pct,
        daily_loss_pct=daily_loss_pct,
        total_drawdown_pct=total_drawdown_pct,
        guardrails=runtime_settings.guardrails,
        trades_today=trades_today,
    )
    if not limit_check.allowed:
        AuditLogger.log("system", "trade_blocked", {"ticker": payload.ticker, "reasons": limit_check.reasons})
        raise HTTPException(status_code=400, detail=" ".join(limit_check.reasons))

    if payload.action.upper() == "SELL":
        position = next((item for item in positions if str(item.get("ticker", "")).upper() == payload.ticker.upper()), None)
        if position is None or float(position.get("market_value", 0.0) or 0.0) <= 0:
            raise HTTPException(status_code=400, detail=f"No existing position in {payload.ticker.upper()} to sell.")
        if payload.notional_usd > float(position.get("market_value", 0.0) or 0.0) * 1.02:
            raise HTTPException(status_code=400, detail="Sell notional exceeds the current position value.")

    preview_price = await YFinanceAdapter().get_latest_price(payload.ticker)
    estimated_quantity = (
        round(payload.notional_usd / preview_price, 6)
        if preview_price and preview_price > 0
        else 1.0
    )
    confirmation_required = _requires_confirmation(permissions, runtime_settings, payload)
    preview = {
        "ticker": payload.ticker.upper(),
        "action": payload.action.upper(),
        "notional_usd": round(payload.notional_usd, 2),
        "estimated_quantity": estimated_quantity,
        "estimated_price": preview_price,
        "mode": settings.alpaca_mode,
        "reasons": limit_check.reasons,
        "permission_level": permissions.level.value,
    }
    if confirmation_required and not payload.confirm:
        AuditLogger.log("system", "trade_confirmation_required", preview)
        return {
            "accepted": False,
            "requires_confirmation": True,
            "preview": preview,
        }

    order = Order(
        id=str(uuid.uuid4()),
        ticker=payload.ticker.upper(),
        action=payload.action.upper(),
        quantity=estimated_quantity,
        notional_usd=payload.notional_usd,
        mode=settings.alpaca_mode,
        status="submitted",
        reasoning=payload.reasoning or "Submitted through the trading API with guardrails enforced.",
        team_id=payload.team_id,
        execution_snapshot_id=payload.execution_snapshot_id,
    )
    broker_result = await AlpacaBroker().submit_order(order)
    if not broker_result.get("submitted"):
        AuditLogger.log("system", "trade_submission_failed", {"ticker": order.ticker, "reason": broker_result.get("reason", "Unknown broker failure")})
        raise HTTPException(status_code=502, detail=str(broker_result.get("reason", "Broker submission failed.")))

    order.submitted_at = broker_result.get("submitted_at")
    order.filled_at = broker_result.get("filled_at")
    order.fill_price = broker_result.get("fill_price")
    order.filled_quantity = broker_result.get("filled_quantity")
    order.fees = float(broker_result.get("fees", 0.0) or 0.0)
    order.broker_order_id = str(broker_result.get("broker_order_id") or "")
    order.broker_status = str(broker_result.get("broker_status") or "")
    order.status = "paper_filled" if order.filled_at and settings.alpaca_mode == "paper" else (order.broker_status or "submitted")
    await store_trade(order.id, order.model_dump() | {"created_at": datetime.now(UTC).isoformat(), "broker_result": broker_result})
    AuditLogger.log("user", "trade_submitted", order.model_dump())
    return {
        "accepted": True,
        "requires_confirmation": False,
        "order": order.model_dump(),
        "preview": preview,
    }


@router.post("/kill-switch")
async def set_kill_switch(payload: KillSwitchPayload):
    if payload.active:
        result = await activate(payload.reason or "manual stop")
        AuditLogger.log("user", "kill_switch_activated", result)
        return {"active": True, "reason": result["reason"], "cancel_result": result.get("cancel_result")}
    result = await deactivate()
    AuditLogger.log("user", "kill_switch_deactivated", result)
    return {"active": False, "reason": ""}


@router.post("/live-enable")
async def set_live_enable(payload: LiveEnablePayload):
    permissions = await _permissions()
    runtime_settings = await _runtime_settings()
    if payload.enabled:
        live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
        gating_failures = [gate["label"] for gate in live_unlock["gates"] if gate["id"] != "explicit_live_enable" and not gate["passed"]]
        if gating_failures:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot enable live trading yet: {', '.join(str(item) for item in gating_failures)}.",
            )
    permissions.live_trading_enabled = payload.enabled
    await save_state("user_permissions", permissions.to_dict())
    AuditLogger.log("user", "live_trading_toggle", {"enabled": payload.enabled})
    live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
    return {"enabled": permissions.live_trading_enabled, "live_unlock": live_unlock}


@router.get("/orders")
async def order_history():
    return await list_trades()


def _requires_confirmation(
    permissions: UserPermissions,
    runtime_settings: UserSettings,
    payload: TradeRequest,
) -> bool:
    if permissions.level.value == "full_manual":
        return True
    if permissions.level.value == "semi_auto":
        return payload.notional_usd > runtime_settings.guardrails.auto_confirm_max_usd
    return False


def _count_trades_today(trades: list[dict[str, object]]) -> int:
    today = datetime.now(UTC).date()
    count = 0
    for trade in trades:
        raw_timestamp = trade.get("filled_at") or trade.get("submitted_at") or trade.get("created_at")
        if not isinstance(raw_timestamp, str):
            continue
        try:
            parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.date() == today:
            count += 1
    return count


async def _runtime_portfolio(runtime_settings: UserSettings) -> dict[str, object]:
    broker_snapshot = await AlpacaBroker().get_portfolio_snapshot()
    if broker_snapshot.get("available"):
        local = await derive_local_portfolio(runtime_settings.backtest.default_initial_cash)
        broker_snapshot["history"] = local.get("history", [])
        return broker_snapshot
    return await derive_local_portfolio(runtime_settings.backtest.default_initial_cash)
