from __future__ import annotations

from datetime import timedelta

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date


class MarketauxAdapter(DataAdapter):
    source_name = "marketaux"
    default_ttl_minutes = 45
    supports_point_in_time = True

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_entity_sentiment(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=True,
        )

    async def get_entity_sentiment(self, ticker: str, as_of_datetime: str | None = None) -> dict:
        if not settings.marketaux_api_key:
            return {}

        as_of = parse_as_of_date(as_of_datetime)
        start = as_of - timedelta(days=7)
        payload = await self._get_json(
            "https://api.marketaux.com/v1/news/all",
            params={
                "symbols": ticker.upper(),
                "filter_entities": "true",
                "published_after": start.isoformat(),
                "published_before": as_of.isoformat(),
                "limit": 20,
                "api_token": settings.marketaux_api_key,
            },
            cache_key=self._cache_key("news-all", ticker.upper(), start.isoformat(), as_of.isoformat()),
            ttl_minutes=self.default_ttl_minutes,
            rate_limit_name="marketaux",
        )
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if not items:
            return {}

        sentiments: list[float] = []
        mentions = 0
        for item in items:
            entities = item.get("entities", []) if isinstance(item, dict) else []
            for entity in entities:
                symbol = str(entity.get("symbol", "")).upper()
                if symbol != ticker.upper():
                    continue
                sentiment = entity.get("sentiment_score")
                try:
                    sentiments.append(float(sentiment))
                    mentions += 1
                except (TypeError, ValueError):
                    continue

        entity_sentiment = round(sum(sentiments) / len(sentiments), 6) if sentiments else None
        highlights = [
            str(item.get("title", "")).strip()
            for item in items[:6]
            if isinstance(item, dict) and item.get("title")
        ]
        return {
            "entity_sentiment": entity_sentiment,
            "entity_mentions": mentions,
            "summary": " | ".join(highlights) if highlights else None,
            "highlights": highlights,
        }
