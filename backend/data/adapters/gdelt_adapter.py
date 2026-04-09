from __future__ import annotations

from datetime import timedelta
from typing import Any

from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_datetime
from backend.data.adapters.headline_sentiment import normalize_headlines, score_headlines


class GdeltAdapter(DataAdapter):
    source_name = "gdelt"
    default_ttl_minutes = 60
    supports_point_in_time = True

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_news_snapshot(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=True,
        )

    async def get_news_snapshot(
        self,
        ticker: str,
        *,
        company_name: str | None = None,
        as_of_datetime: str | None = None,
    ) -> dict[str, Any]:
        as_of = parse_as_of_datetime(as_of_datetime)
        start = as_of - timedelta(days=7)
        query_terms = [term for term in [company_name, ticker.upper()] if term]
        if not query_terms:
            return {}
        payload = await self._get_json(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": " OR ".join(f'"{term}"' for term in query_terms),
                "mode": "ArtList",
                "format": "json",
                "maxrecords": 25,
                "sort": "datedesc",
                "startdatetime": start.strftime("%Y%m%d%H%M%S"),
                "enddatetime": as_of.strftime("%Y%m%d%H%M%S"),
            },
            cache_key=self._cache_key(
                "artlist",
                ticker.upper(),
                company_name or "",
                start.strftime("%Y%m%d%H%M%S"),
                as_of.strftime("%Y%m%d%H%M%S"),
            ),
            ttl_minutes=self.default_ttl_minutes,
            timeout=25.0,
        )
        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        if not isinstance(articles, list):
            return {}

        titles = normalize_headlines(
            [str(item.get("title", "")).strip() for item in articles if isinstance(item, dict)],
            limit=8,
        )
        if not titles:
            return {}
        return {
            "headline_sentiment": score_headlines(titles),
            "headline_count": len(titles),
            "highlights": titles,
        }

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
        try:
            return await super()._get_json(
                url,
                params=params,
                headers=headers,
                cache_key=cache_key,
                ttl_minutes=ttl_minutes,
                rate_limit_name=rate_limit_name,
                timeout=timeout,
            )
        except Exception:
            return {}
