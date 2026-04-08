from __future__ import annotations

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date


class FmpAdapter(DataAdapter):
    source_name = "fmp"
    default_ttl_minutes = 180
    supports_point_in_time = False

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_earnings_snapshot(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=False,
        )

    async def get_earnings_snapshot(self, ticker: str, as_of_datetime: str | None = None) -> dict:
        if not settings.fmp_api_key:
            return {}

        payload = await self._get_json(
            f"https://financialmodelingprep.com/api/v3/earnings-surprises/{ticker.upper()}",
            params={"apikey": settings.fmp_api_key},
            cache_key=self._cache_key("earnings-surprises", ticker.upper()),
            ttl_minutes=self.default_ttl_minutes,
            rate_limit_name="fmp",
        )
        if not isinstance(payload, list):
            return {}

        as_of = parse_as_of_date(as_of_datetime)
        filtered = [
            item
            for item in payload
            if not item.get("date") or parse_as_of_date(f"{item['date']}T00:00:00+00:00") <= as_of
        ]
        if not filtered:
            return {}

        surprises = []
        analyst_consensus_eps = None
        for item in filtered[:8]:
            estimated = item.get("estimatedEarning") or item.get("estimatedEPS")
            actual = item.get("actualEarningResult") or item.get("actualEPS")
            try:
                estimated_value = float(estimated)
                actual_value = float(actual)
            except (TypeError, ValueError):
                continue
            if estimated_value != 0:
                surprises.append(round((actual_value / estimated_value) - 1.0, 6))
            analyst_consensus_eps = estimated_value

        if not surprises:
            return {}

        return {
            "earnings_surprises": surprises[:8],
            "analyst_consensus_eps": analyst_consensus_eps,
            "beat_rate": round(len([value for value in surprises if value > 0]) / len(surprises), 6),
        }


FMPAdapter = FmpAdapter
