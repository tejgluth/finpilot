from __future__ import annotations

from datetime import UTC, datetime
import asyncio
from typing import Any

import httpx

from backend.config import settings
from backend.data.adapters import YFinanceAdapter
from backend.models.trade import Order


class AlpacaBroker:
    async def submit_order(self, order: Order) -> dict:
        if settings.alpaca_mode == "paper" and not settings.has_alpaca():
            return await self._submit_local_paper(order)
        if not settings.has_alpaca():
            return {
                "submitted": False,
                "mode": settings.alpaca_mode,
                "reason": "Alpaca credentials not configured.",
            }
        payload: dict[str, Any] = {
            "symbol": order.ticker.upper(),
            "side": order.action.lower(),
            "type": "market",
            "time_in_force": "day",
        }
        if order.notional_usd > 0:
            payload["notional"] = round(order.notional_usd, 2)
        else:
            payload["qty"] = round(order.quantity, 6)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self._trading_base_url()}/v2/orders",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()

        filled_qty = _to_float(raw.get("filled_qty")) or _to_float(raw.get("qty")) or order.quantity
        fill_price = _to_float(raw.get("filled_avg_price"))
        return {
            "submitted": True,
            "mode": settings.alpaca_mode,
            "broker_order_id": raw.get("id"),
            "broker_status": raw.get("status"),
            "submitted_at": raw.get("submitted_at") or datetime.now(UTC).isoformat(),
            "filled_at": raw.get("filled_at"),
            "fill_price": fill_price,
            "filled_quantity": filled_qty,
            "fees": 0.0,
            "raw_order": raw,
        }

    async def cancel_all_orders(self) -> dict:
        if not settings.has_alpaca():
            return {
                "cancelled": True,
                "mode": settings.alpaca_mode,
                "cancelled_count": 0,
                "detail": "Local paper mode has no remote resting orders.",
            }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.delete(
                f"{self._trading_base_url()}/v2/orders",
                headers=self._headers(),
            )
            response.raise_for_status()
            raw = response.json() if response.content else []
        return {
            "cancelled": True,
            "mode": settings.alpaca_mode,
            "cancelled_count": len(raw) if isinstance(raw, list) else 0,
        }

    async def get_portfolio_snapshot(self) -> dict[str, Any]:
        if not settings.has_alpaca():
            return {"available": False, "reason": "Alpaca credentials not configured."}
        async with httpx.AsyncClient(timeout=20.0) as client:
            account_response, positions_response = await asyncio.gather(
                client.get(f"{self._trading_base_url()}/v2/account", headers=self._headers()),
                client.get(f"{self._trading_base_url()}/v2/positions", headers=self._headers()),
            )
            account_response.raise_for_status()
            positions_response.raise_for_status()
        account = account_response.json()
        raw_positions = positions_response.json()
        positions: list[dict[str, Any]] = []
        for item in raw_positions:
            qty = _to_float(item.get("qty")) or 0.0
            avg_entry = _to_float(item.get("avg_entry_price")) or 0.0
            market_price = _to_float(item.get("current_price")) or avg_entry
            market_value = _to_float(item.get("market_value")) or (qty * market_price)
            unrealized = _to_float(item.get("unrealized_pl")) or (market_value - (qty * avg_entry))
            positions.append(
                {
                    "ticker": item.get("symbol"),
                    "quantity": round(qty, 6),
                    "average_cost": round(avg_entry, 4),
                    "market_price": round(market_price, 4),
                    "market_value": round(market_value, 2),
                    "unrealized_pnl": round(unrealized, 2),
                    "sector": "unknown",
                }
            )
        equity = _to_float(account.get("equity")) or 0.0
        last_equity = _to_float(account.get("last_equity")) or equity
        cash = _to_float(account.get("cash")) or 0.0
        return {
            "available": True,
            "cash": round(cash, 2),
            "equity": round(equity, 2),
            "daily_pnl": round(equity - last_equity, 2),
            "positions": positions,
            "history": [],
        }

    def _trading_base_url(self) -> str:
        return settings.alpaca_live_base_url if settings.alpaca_mode == "live" else settings.alpaca_paper_base_url

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _submit_local_paper(self, order: Order) -> dict[str, Any]:
        price = await YFinanceAdapter().get_latest_price(order.ticker)
        if price is None or price <= 0:
            return {
                "submitted": False,
                "mode": "paper",
                "reason": f"Unable to fetch a truthful market price for {order.ticker}.",
            }
        quantity = round(order.notional_usd / price, 6)
        return {
            "submitted": True,
            "mode": "paper",
            "broker_order_id": f"local-paper-{order.id}",
            "broker_status": "filled",
            "submitted_at": datetime.now(UTC).isoformat(),
            "filled_at": datetime.now(UTC).isoformat(),
            "fill_price": round(price, 4),
            "filled_quantity": quantity,
            "fees": 0.0,
        }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
