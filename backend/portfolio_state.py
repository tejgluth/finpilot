from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.data.adapters import YFinanceAdapter
from backend.database import list_trades


EXECUTED_STATUSES = {"paper_filled", "filled", "executed"}


@dataclass
class ExecutedTrade:
    order_id: str
    ticker: str
    action: str
    quantity: float
    fill_price: float
    fees: float
    filled_at: datetime
    mode: str
    reasoning: str
    status: str


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_trade(payload: dict[str, Any]) -> ExecutedTrade | None:
    filled_at = _parse_timestamp(payload.get("filled_at") or payload.get("submitted_at") or payload.get("created_at"))
    action = str(payload.get("action", "")).upper()
    status = str(payload.get("status", "")).lower()
    quantity = payload.get("filled_quantity", payload.get("quantity"))
    fill_price = payload.get("fill_price")
    if filled_at is None or action not in {"BUY", "SELL"}:
        return None
    try:
        quantity_value = float(quantity)
        fill_price_value = float(fill_price)
        fees_value = float(payload.get("fees", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if quantity_value <= 0 or fill_price_value <= 0:
        return None
    if status not in EXECUTED_STATUSES and status != "":
        return None
    return ExecutedTrade(
        order_id=str(payload.get("id") or ""),
        ticker=str(payload.get("ticker", "")).upper(),
        action=action,
        quantity=quantity_value,
        fill_price=fill_price_value,
        fees=fees_value,
        filled_at=filled_at,
        mode=str(payload.get("mode", "paper")),
        reasoning=str(payload.get("reasoning", "")),
        status=status or "filled",
    )


async def list_executed_trades(limit: int = 1000) -> list[ExecutedTrade]:
    rows = await list_trades(limit=limit)
    trades = [trade for payload in rows if (trade := _normalize_trade(payload))]
    return sorted(trades, key=lambda trade: trade.filled_at)


async def count_paper_trading_days(limit: int = 1000) -> int:
    trades = await list_executed_trades(limit=limit)
    days = {
        trade.filled_at.date().isoformat()
        for trade in trades
        if trade.mode == "paper"
    }
    return len(days)


async def derive_local_portfolio(starting_cash: float = 100_000.0) -> dict[str, Any]:
    trades = await list_executed_trades()
    if not trades:
        return {
            "cash": round(starting_cash, 2),
            "equity": round(starting_cash, 2),
            "daily_pnl": 0.0,
            "positions": [],
            "history": [],
            "executed_trades": [],
            "paper_trading_days_completed": 0,
        }

    tickers = sorted({trade.ticker for trade in trades})
    start_date = min(trade.filled_at.date() for trade in trades) - timedelta(days=7)
    end_date = datetime.now(UTC).date() + timedelta(days=1)
    adapter = YFinanceAdapter()

    async def _history_for(ticker: str) -> tuple[str, dict[str, float], str]:
        frame = await adapter.get_price_history(ticker, start_date=start_date, end_date=end_date)
        profile = await adapter.get_security_profile(ticker)
        prices = {
            str(row["date"]): round(float(row["close"]), 4)
            for row in frame.to_dict(orient="records")
            if row.get("close") is not None
        }
        return ticker, prices, profile.get("sector") or "unknown"

    histories = await asyncio.gather(*[_history_for(ticker) for ticker in tickers])
    price_lookup = {ticker: prices for ticker, prices, _sector in histories}
    sector_lookup = {ticker: sector for ticker, _prices, sector in histories}

    timeline = sorted(
        {
            datetime.fromisoformat(price_date).date()
            for prices in price_lookup.values()
            for price_date in prices
        }
        | {trade.filled_at.date() for trade in trades}
    )
    if not timeline:
        timeline = [datetime.now(UTC).date()]

    positions: dict[str, dict[str, float]] = {}
    cash = float(starting_cash)
    history: list[dict[str, float | str]] = []
    last_prices: dict[str, float] = {}
    pending = list(trades)
    trade_index = 0

    for current_day in timeline:
        while trade_index < len(pending) and pending[trade_index].filled_at.date() <= current_day:
            trade = pending[trade_index]
            position = positions.setdefault(trade.ticker, {"quantity": 0.0, "average_cost": 0.0})
            if trade.action == "BUY":
                existing_quantity = position["quantity"]
                new_quantity = existing_quantity + trade.quantity
                gross_cost = (position["average_cost"] * existing_quantity) + (trade.fill_price * trade.quantity) + trade.fees
                position["quantity"] = new_quantity
                position["average_cost"] = gross_cost / new_quantity if new_quantity > 0 else 0.0
                cash -= (trade.fill_price * trade.quantity) + trade.fees
            else:
                sell_quantity = min(position["quantity"], trade.quantity)
                cash += (trade.fill_price * sell_quantity) - trade.fees
                position["quantity"] = max(0.0, position["quantity"] - sell_quantity)
                if position["quantity"] == 0:
                    position["average_cost"] = 0.0
            trade_index += 1

        equity = cash
        for ticker, position in list(positions.items()):
            if position["quantity"] <= 0:
                positions.pop(ticker, None)
                continue
            day_price = price_lookup.get(ticker, {}).get(current_day.isoformat())
            if day_price is not None:
                last_prices[ticker] = day_price
            market_price = last_prices.get(ticker, position["average_cost"])
            equity += position["quantity"] * market_price

        history.append(
            {
                "timestamp": current_day.isoformat(),
                "equity": round(equity, 2),
                "cash": round(cash, 2),
            }
        )

    positions_payload: list[dict[str, Any]] = []
    current_equity = cash
    for ticker, position in sorted(positions.items()):
        market_price = last_prices.get(ticker, position["average_cost"])
        market_value = position["quantity"] * market_price
        current_equity += market_value
        positions_payload.append(
            {
                "ticker": ticker,
                "quantity": round(position["quantity"], 6),
                "average_cost": round(position["average_cost"], 4),
                "market_price": round(market_price, 4),
                "market_value": round(market_value, 2),
                "unrealized_pnl": round((market_price - position["average_cost"]) * position["quantity"], 2),
                "sector": sector_lookup.get(ticker, "unknown"),
            }
        )

    previous_equity = history[-2]["equity"] if len(history) > 1 else history[-1]["equity"]
    daily_pnl = round(float(history[-1]["equity"]) - float(previous_equity), 2)

    return {
        "cash": round(cash, 2),
        "equity": round(current_equity, 2),
        "daily_pnl": daily_pnl,
        "positions": positions_payload,
        "history": history,
        "executed_trades": [
            {
                "id": trade.order_id,
                "ticker": trade.ticker,
                "action": trade.action,
                "quantity": trade.quantity,
                "fill_price": trade.fill_price,
                "fees": trade.fees,
                "filled_at": trade.filled_at.isoformat(),
                "mode": trade.mode,
                "reasoning": trade.reasoning,
                "status": trade.status,
            }
            for trade in trades
        ],
        "paper_trading_days_completed": len({trade.filled_at.date().isoformat() for trade in trades if trade.mode == "paper"}),
    }


def compute_drawdown_metrics(history: list[dict[str, float | str]]) -> tuple[float, float]:
    if len(history) < 2:
        return 0.0, 0.0

    equity_values = [float(point["equity"]) for point in history]
    running_peak = equity_values[0]
    max_drawdown_pct = 0.0
    for equity in equity_values:
        running_peak = max(running_peak, equity)
        if running_peak > 0:
            drawdown_pct = max(0.0, ((running_peak - equity) / running_peak) * 100.0)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    latest = equity_values[-1]
    previous = equity_values[-2]
    daily_loss_pct = max(0.0, ((previous - latest) / previous) * 100.0) if previous > 0 else 0.0
    return round(daily_loss_pct, 4), round(max_drawdown_pct, 4)


def compute_sector_exposure(positions: list[dict[str, Any]], ticker_sector: str | None) -> float:
    if not ticker_sector:
        return 0.0
    total_equity = sum(float(position.get("market_value", 0.0) or 0.0) for position in positions)
    if total_equity <= 0:
        return 0.0
    sector_value = sum(
        float(position.get("market_value", 0.0) or 0.0)
        for position in positions
        if str(position.get("sector", "")).strip().lower() == ticker_sector.strip().lower()
    )
    return round((sector_value / total_equity) * 100.0, 4)
