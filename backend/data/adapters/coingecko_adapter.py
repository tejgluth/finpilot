from __future__ import annotations

from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp


COIN_SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


class CoinGeckoAdapter(DataAdapter):
    source_name = "coingecko"
    default_ttl_minutes = 10
    supports_point_in_time = False

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        coin_id = COIN_SYMBOL_TO_ID.get(ticker.upper())
        if coin_id is None or as_of_datetime is not None:
            return AdapterFetchResult(
                source=self.source_name,
                fetched_at=iso_timestamp(as_of_datetime),
                payload={},
                point_in_time_supported=False,
            )

        payload = await self._get_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"},
            cache_key=self._cache_key("simple-price", coin_id),
            ttl_minutes=self.default_ttl_minutes,
        )
        usd_price = payload.get(coin_id, {}).get("usd") if isinstance(payload, dict) else None
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload={"usd_price": float(usd_price)} if usd_price is not None else {},
            point_in_time_supported=False,
        )
