from __future__ import annotations

from datetime import timedelta

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date
from backend.data.adapters.headline_sentiment import normalize_headlines, score_headlines


class FinnhubAdapter(DataAdapter):
    source_name = "finnhub"
    default_ttl_minutes = 30
    supports_point_in_time = True

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_news_snapshot(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=False,
        )

    async def get_news_snapshot(self, ticker: str, as_of_datetime: str | None = None) -> dict:
        if not settings.finnhub_api_key:
            return {}

        as_of = parse_as_of_date(as_of_datetime)
        start = as_of - timedelta(days=7)
        news = await self._get_json(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": ticker.upper(),
                "from": start.isoformat(),
                "to": as_of.isoformat(),
                "token": settings.finnhub_api_key,
            },
            cache_key=self._cache_key("company-news", ticker.upper(), start.isoformat(), as_of.isoformat()),
            ttl_minutes=self.default_ttl_minutes,
            rate_limit_name="finnhub",
        )
        if not isinstance(news, list):
            return {}

        highlights = normalize_headlines(
            [
            item.get("headline", "").strip()
            for item in news[:8]
            if isinstance(item, dict) and item.get("headline")
            ]
        )

        sentiment_score = score_headlines(highlights)
        if as_of_datetime is None:
            try:
                sentiment = await self._get_json(
                    "https://finnhub.io/api/v1/news-sentiment",
                    params={"symbol": ticker.upper(), "token": settings.finnhub_api_key},
                    cache_key=self._cache_key("news-sentiment", ticker.upper()),
                    ttl_minutes=self.default_ttl_minutes,
                    rate_limit_name="finnhub",
                )
            except Exception:
                sentiment = {}
            company_news_score = sentiment.get("companyNewsScore") if isinstance(sentiment, dict) else None
            try:
                provider_score = None if company_news_score is None else round(float(company_news_score), 6)
            except (TypeError, ValueError):
                provider_score = None
            if provider_score is not None and sentiment_score is not None:
                sentiment_score = round((provider_score + sentiment_score) / 2.0, 6)
            elif provider_score is not None:
                sentiment_score = provider_score

        return {
            "headline_sentiment": sentiment_score,
            "headline_count": len(highlights),
            "highlights": highlights,
        }
