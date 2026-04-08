from __future__ import annotations

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp


class AlpacaDataAdapter(DataAdapter):
    source_name = "alpaca_data"
    default_ttl_minutes = 1
    supports_point_in_time = False

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        if as_of_datetime is not None or not settings.has_alpaca():
            return AdapterFetchResult(
                source=self.source_name,
                fetched_at=iso_timestamp(as_of_datetime),
                payload={},
                point_in_time_supported=False,
            )

        payload = await self._get_json(
            f"{settings.alpaca_data_base_url}/v2/stocks/{ticker.upper()}/quotes/latest",
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            },
            cache_key=self._cache_key("latest-quote", ticker.upper()),
            ttl_minutes=self.default_ttl_minutes,
        )
        quote = payload.get("quote", {}) if isinstance(payload, dict) else {}
        price = quote.get("ap") or quote.get("bp")
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload={"last_price": float(price)} if price is not None else {},
            point_in_time_supported=False,
        )
