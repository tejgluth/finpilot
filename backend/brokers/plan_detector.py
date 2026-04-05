"""
Detects Alpaca plan tier and maps it to conservative local rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import httpx

from backend.config import settings


class AlpacaPlan(Enum):
    FREE = "free"
    ALGO_TRADER = "algo_trader"
    UNLIMITED = "unlimited"
    UNKNOWN = "unknown"


@dataclass
class AlpacaRateLimits:
    plan: AlpacaPlan
    display_name: str
    data_requests_per_minute: int
    orders_per_minute: int
    orders_per_day: int
    supports_live_trading: bool
    supports_options: bool
    description: str


PLAN_LIMITS = {
    AlpacaPlan.FREE: AlpacaRateLimits(
        AlpacaPlan.FREE,
        "Free",
        data_requests_per_minute=200,
        orders_per_minute=60,
        orders_per_day=200,
        supports_live_trading=True,
        supports_options=False,
        description="200 data req/min, 200 orders/day. Stocks, ETFs, crypto. No options.",
    ),
    AlpacaPlan.ALGO_TRADER: AlpacaRateLimits(
        AlpacaPlan.ALGO_TRADER,
        "Algo Trader Plus",
        data_requests_per_minute=500,
        orders_per_minute=150,
        orders_per_day=2000,
        supports_live_trading=True,
        supports_options=True,
        description="500 data req/min, 2000 orders/day. Options enabled.",
    ),
    AlpacaPlan.UNLIMITED: AlpacaRateLimits(
        AlpacaPlan.UNLIMITED,
        "Unlimited",
        data_requests_per_minute=10_000,
        orders_per_minute=500,
        orders_per_day=10_000,
        supports_live_trading=True,
        supports_options=True,
        description="Highest available rate limits.",
    ),
    AlpacaPlan.UNKNOWN: AlpacaRateLimits(
        AlpacaPlan.UNKNOWN,
        "Unknown (using Free limits for safety)",
        data_requests_per_minute=200,
        orders_per_minute=60,
        orders_per_day=200,
        supports_live_trading=False,
        supports_options=False,
        description=(
            "Plan detection failed. Using Free plan limits as a conservative default. "
            "You can manually select your plan in Settings -> Data Sources."
        ),
    ),
}


async def detect_alpaca_plan(override: str = "auto") -> AlpacaRateLimits:
    if override != "auto":
        plan_map = {
            "free": AlpacaPlan.FREE,
            "algo_trader": AlpacaPlan.ALGO_TRADER,
            "unlimited": AlpacaPlan.UNLIMITED,
        }
        return PLAN_LIMITS.get(plan_map.get(override, AlpacaPlan.UNKNOWN), PLAN_LIMITS[AlpacaPlan.UNKNOWN])

    if not settings.has_alpaca():
        return PLAN_LIMITS[AlpacaPlan.UNKNOWN]

    base_url = settings.alpaca_live_base_url if settings.alpaca_mode == "live" else settings.alpaca_paper_base_url
    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/v2/account", headers=headers)
            response.raise_for_status()
            account = response.json()
        if account.get("trading_blocked"):
            return PLAN_LIMITS[AlpacaPlan.UNKNOWN]
        options_level = account.get("options_approved_level", 0)
        if options_level and int(options_level) > 0:
            return PLAN_LIMITS[AlpacaPlan.ALGO_TRADER]
        return PLAN_LIMITS[AlpacaPlan.FREE]
    except Exception:
        return PLAN_LIMITS[AlpacaPlan.UNKNOWN]
