from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import json
from typing import Any

import httpx

from backend.data.cache import SQLiteCache
from backend.data.rate_limiter import DEFAULT_LIMITS, limiter


@dataclass
class AdapterFetchResult:
    source: str
    fetched_at: str
    payload: dict[str, Any]
    point_in_time_supported: bool = False
    warnings: list[str] = field(default_factory=list)


class DataAdapter:
    source_name: str = "base"
    default_ttl_minutes: int = 60
    supports_point_in_time: bool = False

    def __init__(self) -> None:
        self.cache = SQLiteCache()

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        raise NotImplementedError

    async def _wait_for_rate_limit(self, name: str) -> None:
        limit = DEFAULT_LIMITS.get(name)
        if limit is None:
            return
        while not limiter.allow(limit):
            await asyncio.sleep(0.25)

    async def _get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str,
        ttl_minutes: int | None = None,
        rate_limit_name: str | None = None,
        timeout: float = 20.0,
    ) -> Any:
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        if rate_limit_name:
            await self._wait_for_rate_limit(rate_limit_name)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        await self.cache.set(
            cache_key,
            payload,
            ttl_minutes=ttl_minutes or self.default_ttl_minutes,
            source=self.source_name,
        )
        return payload

    async def _get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str,
        ttl_minutes: int | None = None,
        rate_limit_name: str | None = None,
        timeout: float = 20.0,
    ) -> str:
        cached = await self.cache.get(cache_key)
        if isinstance(cached, str):
            return cached

        if rate_limit_name:
            await self._wait_for_rate_limit(rate_limit_name)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.text

        await self.cache.set(
            cache_key,
            payload,
            ttl_minutes=ttl_minutes or self.default_ttl_minutes,
            source=self.source_name,
        )
        return payload

    def _cache_key(self, *parts: object) -> str:
        serialized = json.dumps(parts, sort_keys=True, default=str)
        return f"{self.source_name}:{serialized}"


def parse_as_of_datetime(as_of_datetime: str | None) -> datetime:
    if as_of_datetime:
        return datetime.fromisoformat(as_of_datetime.replace("Z", "+00:00"))
    return datetime.now(UTC)


def parse_as_of_date(as_of_datetime: str | None) -> date:
    return parse_as_of_datetime(as_of_datetime).date()


def iso_timestamp(as_of_datetime: str | None = None) -> str:
    return parse_as_of_datetime(as_of_datetime).astimezone(UTC).isoformat()
