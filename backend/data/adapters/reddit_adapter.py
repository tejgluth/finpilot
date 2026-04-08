from __future__ import annotations

import asyncio

import praw

from backend.config import settings
from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp


SUBREDDITS = ("wallstreetbets", "investing", "stocks")


class RedditAdapter(DataAdapter):
    source_name = "reddit"
    default_ttl_minutes = 60
    supports_point_in_time = False

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_social_snapshot(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=False,
        )

    async def get_social_snapshot(self, ticker: str, as_of_datetime: str | None = None) -> dict:
        if as_of_datetime is not None:
            return {}
        if not (settings.reddit_client_id and settings.reddit_client_secret and settings.reddit_user_agent):
            return {}

        cache_key = self._cache_key("social", ticker.upper())
        cached = await self.cache.get(cache_key)
        if isinstance(cached, dict):
            return cached

        def _load() -> dict:
            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            mention_count = 0
            ratios: list[float] = []
            summaries: list[str] = []
            query = f'"{ticker.upper()}" OR "${ticker.upper()}"'
            for subreddit_name in SUBREDDITS:
                subreddit = reddit.subreddit(subreddit_name)
                for post in subreddit.search(query, sort="new", limit=20):
                    mention_count += 1
                    if getattr(post, "upvote_ratio", None) is not None:
                        ratios.append(float(post.upvote_ratio))
                    title = str(getattr(post, "title", "")).strip()
                    if title:
                        summaries.append(title)
            return {
                "mention_count": mention_count,
                "upvote_ratio": round(sum(ratios) / len(ratios), 6) if ratios else None,
                "summary": " | ".join(summaries[:5]) if summaries else None,
            }

        payload = await asyncio.to_thread(_load)
        await self.cache.set(cache_key, payload, ttl_minutes=self.default_ttl_minutes, source=self.source_name)
        return payload
