from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class RateLimit:
    name: str
    requests: int
    period_seconds: int


class TokenBucketLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[datetime]] = defaultdict(deque)

    def allow(self, limit: RateLimit) -> bool:
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=limit.period_seconds)
        bucket = self._events[limit.name]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit.requests:
            return False
        bucket.append(now)
        return True


DEFAULT_LIMITS = {
    "edgar": RateLimit("edgar", 10, 1),
    "finnhub": RateLimit("finnhub", 60, 60),
    "marketaux": RateLimit("marketaux", 100, 86400),
    "fmp": RateLimit("fmp", 250, 86400),
}

limiter = TokenBucketLimiter()
