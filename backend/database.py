from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
except ImportError:  # pragma: no cover - optional in bare test environments
    AsyncSession = object  # type: ignore[assignment]

    def async_sessionmaker(*args, **kwargs):  # type: ignore[no-redef]
        return None

    def create_async_engine(*args, **kwargs):  # type: ignore[no-redef]
        return None

from backend.config import settings


DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"
engine = create_async_engine(DATABASE_URL, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_journal (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_cache (
                cache_key TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def get_session() -> AsyncIterator[AsyncSession]:
    if AsyncSessionLocal is None:  # pragma: no cover
        raise RuntimeError("SQLAlchemy is not installed in this environment.")
    async with AsyncSessionLocal() as session:
        yield session


async def load_state(key: str, default: Any = None) -> Any:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute("SELECT value FROM app_state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        return default
    return json.loads(row[0])


async def save_state(key: str, value: Any) -> None:
    payload = json.dumps(value)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            INSERT INTO app_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, payload),
        )
        await db.commit()


async def store_backtest(run_id: str, payload: dict[str, Any]) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO backtest_runs (id, created_at, payload) VALUES (?, CURRENT_TIMESTAMP, ?)",
            (run_id, json.dumps(payload)),
        )
        await db.commit()


async def list_backtests(limit: int = 25) -> list[dict[str, Any]]:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT payload FROM backtest_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [json.loads(row[0]) for row in rows]


async def store_trade(order_id: str, payload: dict[str, Any]) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO trade_journal (id, created_at, payload) VALUES (?, CURRENT_TIMESTAMP, ?)",
            (order_id, json.dumps(payload)),
        )
        await db.commit()


async def list_trades(limit: int = 100) -> list[dict[str, Any]]:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT payload FROM trade_journal ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [json.loads(row[0]) for row in rows]


async def load_backtest_cache(cache_key: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT payload FROM backtest_cache WHERE cache_key = ?",
            (cache_key,),
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    return json.loads(row[0])


async def store_backtest_cache(cache_key: str, payload: dict[str, Any]) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO backtest_cache (cache_key, created_at, payload)
            VALUES (?, CURRENT_TIMESTAMP, ?)
            """,
            (cache_key, json.dumps(payload)),
        )
        await db.commit()
