from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:  # pragma: no cover
    from fastapi.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content):
            super().__init__(content, media_type="text/event-stream")

from backend.backtester.engine import BacktestEngine, BacktestRequest, stream_backtest_progress
from backend.database import load_state
from backend.llm.strategy_builder import (
    apply_team_overrides,
    build_execution_snapshot,
    resolve_effective_team,
)
from backend.models.agent_team import DataBoundary, ExecutionSnapshot
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


async def _runtime_settings() -> UserSettings:
    raw = await load_state("user_settings", None)
    return UserSettings.from_dict(raw) if raw else default_user_settings()


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    runtime_settings = await _runtime_settings()
    try:
        execution_snapshots = await _resolve_execution_snapshots(request, runtime_settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    for snapshot in execution_snapshots:
        AuditLogger.log(
            "strategy",
            "execution_snapshot_created",
            {
                "snapshot_id": snapshot.snapshot_id,
                "team_id": snapshot.effective_team.team_id,
                "mode": request.backtest_mode,
                "ticker_or_universe": request.universe_descriptor,
            },
        )
    try:
        result = await BacktestEngine().run(
            request,
            runtime_settings,
            execution_snapshots=execution_snapshots,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditLogger.log(
        "system",
        "backtest_completed",
        {
            "ticker_or_universe": request.universe_descriptor,
            "artifact_id": result.artifact.artifact_id,
            "snapshot_id": execution_snapshots[0].snapshot_id,
            "team_id": execution_snapshots[0].effective_team.team_id,
            "backtest_mode": request.backtest_mode,
        },
    )
    return result.model_dump(mode="json")


@router.post("/stream")
async def run_backtest_stream(request: BacktestRequest):
    runtime_settings = await _runtime_settings()
    try:
        execution_snapshots = await _resolve_execution_snapshots(request, runtime_settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_generator():
        async for event in stream_backtest_progress(
            request,
            runtime_settings,
            execution_snapshots=execution_snapshots,
        ):
            yield {"event": event["event"], "data": json.dumps(event["data"])}

    return EventSourceResponse(event_generator())


async def _resolve_execution_snapshots(
    request: BacktestRequest,
    runtime_settings: UserSettings,
) -> list[ExecutionSnapshot]:
    compiled_teams = []
    primary = await resolve_effective_team(
        user_settings=runtime_settings,
        team_config=request.team_config,
        team_id=request.team_id,
        version_number=request.version_number,
    )
    compiled_teams.append(primary)
    for comparison_target in request.resolved_comparison_targets:
        candidate = await resolve_effective_team(
            user_settings=runtime_settings,
            team_id=comparison_target.team_id,
            version_number=comparison_target.version_number,
        )
        candidate_key = (candidate.team_id, candidate.version_number)
        existing_keys = {(team.team_id, team.version_number) for team in compiled_teams}
        if candidate_key not in existing_keys:
            compiled_teams.append(candidate)

    snapshots: list[ExecutionSnapshot] = []
    for index, compiled_team in enumerate(compiled_teams):
        effective_settings = apply_team_overrides(runtime_settings, compiled_team)
        snapshots.append(
            build_execution_snapshot(
                mode=request.backtest_mode,
                ticker_or_universe=request.universe_descriptor,
                user_settings=effective_settings,
                compiled_team=compiled_team,
                data_boundary=DataBoundary(
                    mode=request.backtest_mode,  # type: ignore[arg-type]
                    as_of_datetime=request.resolved_as_of_datetime,
                    allow_latest_semantics=not request.resolved_strict_mode,
                ),
                cost_model={
                    "slippage_pct": request.slippage_pct,
                    "commission_pct": request.commission_pct,
                    "rebalance_frequency": request.rebalance_frequency,
                },
                notes=[
                    "Backtest path resolved the selected compiled team."
                    if index == 0
                    else "Backtest path resolved an additional comparison team."
                ],
            )
        )
    return snapshots
