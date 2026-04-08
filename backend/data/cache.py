from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

import aiosqlite

from backend.config import settings


class SQLiteCache:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(settings.db_path)

    async def _ensure(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS data_cache (
                    cache_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def get(self, cache_key: str) -> Any | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value, expires_at FROM data_cache WHERE cache_key = ?",
                (cache_key,),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        expires_at = datetime.fromisoformat(row[1])
        if expires_at < datetime.now(UTC):
            await self.delete(cache_key)
            return None
        return json.loads(row[0])

    async def set(self, cache_key: str, value: Any, ttl_minutes: int, source: str) -> None:
        await self._ensure()
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO data_cache (cache_key, value, expires_at, source)
                VALUES (?, ?, ?, ?)
                """,
                (cache_key, json.dumps(value), expires_at.isoformat(), source),
            )
            await db.commit()

    async def delete(self, cache_key: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM data_cache WHERE cache_key = ?", (cache_key,))
            await db.commit()

    async def purge_expired(self) -> int:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM data_cache WHERE expires_at < ?",
                (datetime.now(UTC).isoformat(),),
            )
            await db.commit()
            return cursor.rowcount or 0
