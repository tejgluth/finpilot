from __future__ import annotations

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp


class PolygonAdapter(DataAdapter):
    source_name = "polygon"
    default_ttl_minutes = 5
    supports_point_in_time = False

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        if as_of_datetime is not None or not settings.polygon_api_key:
            return AdapterFetchResult(
                source=self.source_name,
                fetched_at=iso_timestamp(as_of_datetime),
                payload={},
                point_in_time_supported=False,
            )

        payload = await self._get_json(
            f"https://api.polygon.io/v2/last/trade/{ticker.upper()}",
            params={"apiKey": settings.polygon_api_key},
            cache_key=self._cache_key("last-trade", ticker.upper()),
            ttl_minutes=self.default_ttl_minutes,
        )
        results = payload.get("results", {}) if isinstance(payload, dict) else {}
        price = results.get("p")
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload={"last_price": float(price)} if price is not None else {},
            point_in_time_supported=False,
        )
