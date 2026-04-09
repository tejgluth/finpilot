from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from backend.database import load_backtest_cache, store_backtest_cache
from backend.models.agent_team import ExecutionSnapshot

PIPELINE_CACHE_SCHEMA_VERSION = "v2"


def build_pipeline_cache_key(
    *,
    execution_snapshot: ExecutionSnapshot,
    ticker: str,
    as_of_datetime: str,
    fidelity_mode: str,
    backtest_mode: str,
) -> str:
    payload = {
        "schema_version": PIPELINE_CACHE_SCHEMA_VERSION,
        "team_hash": execution_snapshot.team_hash,
        "team_id": execution_snapshot.effective_team.team_id,
        "version_number": execution_snapshot.effective_team.version_number,
        "ticker": ticker.upper(),
        "as_of_datetime": as_of_datetime,
        "fidelity_mode": fidelity_mode,
        "backtest_mode": backtest_mode,
        "provider": execution_snapshot.provider,
        "model": execution_snapshot.model,
        "prompt_pack_versions": execution_snapshot.prompt_pack_versions,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


async def load_cached_pipeline_result(cache_key: str) -> dict[str, Any] | None:
    return await load_backtest_cache(cache_key)


async def store_cached_pipeline_result(cache_key: str, payload: dict[str, Any]) -> None:
    await store_backtest_cache(cache_key, payload)
