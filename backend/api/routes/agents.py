from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.orchestrator import run_agent_pipeline
from backend.agents.registry import AGENT_DATA_DEPS, AGENT_DESCRIPTIONS
from backend.database import load_state
from backend.llm.strategy_builder import (
    apply_team_overrides,
    build_execution_snapshot,
    resolve_effective_team,
)
from backend.models.agent_team import CompiledTeam, DataBoundary
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


class AnalyzeRequest(BaseModel):
    ticker: str
    team_config: CompiledTeam | None = None
    team_id: str | None = None
    version_number: int | None = None
    as_of_datetime: str | None = None
    mode: str = "analyze"


async def _runtime_settings() -> UserSettings:
    raw = await load_state("user_settings", None)
    return UserSettings.from_dict(raw) if raw else default_user_settings()


@router.get("/")
async def list_agents():
    return {
        "descriptions": AGENT_DESCRIPTIONS,
        "data_dependencies": AGENT_DATA_DEPS,
    }


@router.post("/analyze")
async def analyze_ticker(payload: AnalyzeRequest):
    runtime_settings = await _runtime_settings()
    try:
        compiled_team = await resolve_effective_team(
            user_settings=runtime_settings,
            team_config=payload.team_config,
            team_id=payload.team_id,
            version_number=payload.version_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    effective_settings = apply_team_overrides(runtime_settings, compiled_team)
    data_boundary = DataBoundary(
        mode="paper" if payload.mode == "paper" else "live" if payload.mode == "live" else "live",
        as_of_datetime=payload.as_of_datetime,
        allow_latest_semantics=payload.as_of_datetime is None,
    )
    execution_snapshot = build_execution_snapshot(
        mode=payload.mode,
        ticker_or_universe=payload.ticker,
        user_settings=effective_settings,
        compiled_team=compiled_team,
        data_boundary=data_boundary,
        cost_model={},
        notes=["Analyze path resolved the selected compiled team."],
    )
    AuditLogger.log(
        "strategy",
        "execution_snapshot_created",
        {
            "snapshot_id": execution_snapshot.snapshot_id,
            "team_id": compiled_team.team_id,
            "ticker": payload.ticker,
            "mode": payload.mode,
        },
    )
    signals, bull_case, bear_case, decision = await run_agent_pipeline(
        payload.ticker,
        effective_settings,
        execution_snapshot,
    )
    for signal in signals:
        AuditLogger.log(f"agent:{signal.agent_name}", "agent_signal", signal.model_dump())
    AuditLogger.log(
        "portfolio_manager",
        "portfolio_decision",
        {
            "ticker": payload.ticker,
            "team_id": compiled_team.team_id,
            "snapshot_id": execution_snapshot.snapshot_id,
            "decision": decision.model_dump(),
        },
    )
    return {
        "signals": [signal.model_dump() for signal in signals],
        "bull_case": bull_case.model_dump() if bull_case else None,
        "bear_case": bear_case.model_dump() if bear_case else None,
        "decision": decision.model_dump(),
        "execution_snapshot": execution_snapshot.model_dump(mode="json"),
    }
