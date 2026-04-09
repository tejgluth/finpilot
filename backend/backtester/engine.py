from __future__ import annotations

import asyncio
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from typing import Any, Awaitable, Callable

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field, model_validator

from backend.agents.debate.bear_researcher import build_bear_case
from backend.agents.debate.bull_researcher import build_bull_case
from backend.agents.decision.portfolio_manager import decide_portfolio_action
from backend.agents.decision.risk_manager import evaluate_risk
from backend.agents.orchestrator import run_agent_pipeline
from backend.backtester.artifacts import write_artifact
from backend.backtester.benchmark import build_benchmark_curve
from backend.backtester.cache import (
    build_pipeline_cache_key,
    load_cached_pipeline_result,
    store_cached_pipeline_result,
)
from backend.backtester.capabilities import (
    DEGRADATION_FACTORS,
    TeamHistoricalProfile,
    build_equivalence_warnings,
    build_historical_gap_report,
)
from backend.backtester.costs import compute_transaction_cost
from backend.backtester.metrics import compute_metrics
from backend.backtester.portfolio_construction import (
    build_portfolio_construction_config,
    construct_target_weights,
)
from backend.backtester.universe import HistoricalUniverseResolver, UniverseTimelineResolution
from backend.data.adapters import YFinanceAdapter
from backend.database import store_backtest
from backend.llm.budget import BudgetTracker
from backend.llm.strategy_builder import apply_team_overrides, build_execution_snapshot, default_compiled_team
from backend.models.agent_team import (
    REQUIRED_DECISION_AGENTS,
    VALID_ANALYSIS_AGENTS,
    CompiledTeam,
    DataBoundary,
    ExecutionSnapshot,
)
from backend.models.backtest_result import (
    BacktestResult,
    CacheUsageSummary,
    DecisionEvent,
    EquityPoint,
    HoldingsSnapshot,
    TeamBacktestRun,
    UniverseDateResolutionReport,
    UniverseResolutionReport,
)
from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

SUPPORTED_RANKING_AGENTS = {"technicals", "momentum"}
ESTIMATED_TOKENS_PER_AGENT_CALL = 300
YAHOO_SYMBOL_ALIASES = {
    "BRKA": "BRK-A",
    "BRKB": "BRK-B",
    "BFA": "BF-A",
    "BFB": "BF-B",
}


class ComparisonTarget(BaseModel):
    team_id: str
    version_number: int | None = None


class BacktestRequest(BaseModel):
    input_overrides: list[str] = Field(default_factory=list, exclude=True)
    ticker: str | None = None
    universe_id: str = "current_sp500"
    custom_universe_csv: str | None = None
    start_date: date
    end_date: date
    initial_cash: float = 100_000.0
    slippage_pct: float = 0.1
    commission_pct: float = 0.0
    team_config: dict[str, Any] | None = None
    team_id: str | None = None
    version_number: int | None = None
    team_ids: list[str] = Field(default_factory=list)
    comparison_targets: list[ComparisonTarget] = Field(default_factory=list)
    as_of_datetime: str | None = None
    backtest_mode: str = Field(default="backtest_strict", pattern="^backtest_(strict|experimental)$")
    rebalance_frequency: str = Field(default="monthly", pattern="^(daily|weekly|biweekly|monthly)$")
    selection_count: int = Field(default=10, ge=1, le=100)
    max_positions: int = Field(default=10, ge=1, le=100)
    top_n_holdings: int | None = Field(default=None, ge=1, le=100)
    candidate_pool_size: int | None = Field(default=None, ge=1, le=250)
    weighting_method: str = Field(
        default="equal_weight",
        pattern="^(equal_weight|confidence_weighted|capped_conviction|risk_budgeted)$",
    )
    weighting_mode: str | None = Field(
        default=None,
        pattern="^(equal_weight|confidence_weighted|capped_conviction|risk_budgeted)$",
    )
    score_normalization_mode: str | None = Field(default=None, pattern="^(linear|power)$")
    risk_adjustment_mode: str | None = Field(default=None, pattern="^(none|mild_inverse_vol|full_inverse_vol)$")
    score_exponent: float | None = Field(default=None, ge=1.0, le=4.0)
    min_conviction_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    min_position_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    max_position_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    cash_floor_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    max_gross_exposure_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    sector_cap_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    selection_buffer_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    turnover_buffer_pct: float | None = Field(default=None, ge=0.0, le=0.95)
    max_turnover_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    hold_zone_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    replacement_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    persistence_bonus: float | None = Field(default=None, ge=0.0, le=1.0)
    min_price: float | None = Field(default=None, ge=0.0)
    min_avg_dollar_volume_millions: float | None = Field(default=None, ge=0.0)
    liquidity_lookback_days: int | None = Field(default=None, ge=5, le=252)
    min_history_days: int | None = Field(default=None, ge=30, le=756)
    fidelity_mode: str = Field(default="full_loop", pattern="^(full_loop|hybrid_shortlist)$")
    cache_policy: str = Field(default="reuse", pattern="^(reuse|fresh)$")
    shortlist_size: int = Field(default=40, ge=1, le=250)
    benchmark_symbol: str = "SPY"
    strict_mode: bool | None = None
    walk_forward_enabled: bool = False

    @model_validator(mode="before")
    @classmethod
    def capture_input_overrides(cls, data: Any) -> Any:
        if isinstance(data, dict):
            payload = dict(data)
            payload["input_overrides"] = list(data.keys())
            return payload
        return data

    @model_validator(mode="after")
    def normalize_selection(self) -> "BacktestRequest":
        if self.top_n_holdings is None:
            self.top_n_holdings = self.max_positions
        if self.candidate_pool_size is None:
            self.candidate_pool_size = self.shortlist_size
        if self.weighting_mode is None:
            self.weighting_mode = self.weighting_method
        self.max_positions = self.top_n_holdings
        self.selection_count = min(self.selection_count, self.max_positions)
        if self.fidelity_mode == "hybrid_shortlist":
            self.candidate_pool_size = max(int(self.candidate_pool_size), self.selection_count)
            self.shortlist_size = self.candidate_pool_size
        return self

    @property
    def resolved_strict_mode(self) -> bool:
        if self.strict_mode is not None:
            return self.strict_mode
        return self.backtest_mode == "backtest_strict"

    @property
    def resolved_as_of_datetime(self) -> str:
        return self.as_of_datetime or f"{self.end_date.isoformat()}T16:00:00+00:00"

    @property
    def universe_descriptor(self) -> str:
        if self.ticker:
            return self.ticker.upper()
        if self.custom_universe_csv:
            return self.custom_universe_csv
        return self.universe_id

    @property
    def resolved_comparison_targets(self) -> list[ComparisonTarget]:
        legacy_targets = [ComparisonTarget(team_id=team_id) for team_id in self.team_ids]
        combined = [*self.comparison_targets, *legacy_targets]
        deduped: dict[tuple[str, int | None], ComparisonTarget] = {}
        for target in combined:
            deduped[(target.team_id, target.version_number)] = target
        return list(deduped.values())


@dataclass
class CandidateEvaluation:
    event: DecisionEvent
    price_open: float | None
    price_close: float | None


@dataclass
class TeamSimulation:
    run: TeamBacktestRun
    decision_events: list[DecisionEvent]


class BacktestEngine:
    async def run(
        self,
        request: BacktestRequest,
        user_settings: UserSettings,
        execution_snapshot: ExecutionSnapshot | None = None,
        execution_snapshots: list[ExecutionSnapshot] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> BacktestResult:
        started_at = datetime.now(UTC).isoformat()
        execution_snapshots = await self._normalize_execution_snapshots(
            request,
            user_settings,
            execution_snapshot=execution_snapshot,
            execution_snapshots=execution_snapshots,
        )
        compiled_teams = [snapshot.effective_team for snapshot in execution_snapshots]
        historical_gap_report, historical_profiles = build_historical_gap_report(
            compiled_teams,
            strict_temporal_mode=request.resolved_strict_mode,
        )
        if historical_gap_report.blocking_errors:
            raise ValueError(" ".join(historical_gap_report.blocking_errors))

        profile_list = [
            historical_profiles[f"{snapshot.effective_team.team_id}:{snapshot.effective_team.version_number}"]
            for snapshot in execution_snapshots
        ]
        team_equivalence_warnings = build_equivalence_warnings(profile_list)

        await _notify(progress_callback, {"stage": "loading_benchmark", "progress": 8})
        benchmark_market_data = await _download_market_data(
            [request.benchmark_symbol, "TLT", "^VIX"],
            start_date=request.start_date - timedelta(days=370),
            end_date=request.end_date + timedelta(days=5),
        )
        open_prices, close_prices, _benchmark_volumes = _build_price_frames(benchmark_market_data)
        benchmark_series = close_prices.get(request.benchmark_symbol)
        if benchmark_series is None:
            raise ValueError(f"Unable to load benchmark history for {request.benchmark_symbol}.")
        calendar = benchmark_series.dropna().loc[request.start_date.isoformat() : request.end_date.isoformat()].index
        if len(calendar) < 3:
            raise ValueError("Not enough historical bars were available for the requested backtest window.")
        rebalance_dates = _rebalance_dates(calendar, request.rebalance_frequency)
        if not rebalance_dates:
            raise ValueError("No rebalance dates were produced for the requested backtest window.")

        await _notify(progress_callback, {"stage": "resolving_universe", "progress": 16})
        universe_timeline = await HistoricalUniverseResolver().resolve_for_dates(
            universe_id=request.universe_id,
            custom_universe_csv=request.custom_universe_csv,
            strict_mode=request.resolved_strict_mode,
            single_ticker=request.ticker,
            rebalance_dates=[item.date() for item in rebalance_dates],
        )
        candidate_universe = sorted(set(universe_timeline.all_tickers + [request.benchmark_symbol, "TLT", "^VIX"]))
        _validate_backtest_workload(
            request=request,
            user_settings=user_settings,
            execution_snapshots=execution_snapshots,
            historical_profiles=historical_profiles,
            universe_timeline=universe_timeline,
            rebalance_dates=rebalance_dates,
        )

        await _notify(
            progress_callback,
            {
                "stage": "loading_prices",
                "progress": 24,
                "candidate_count": len(candidate_universe),
            },
        )
        market_data = await _download_market_data(
            candidate_universe,
            start_date=request.start_date - timedelta(days=370),
            end_date=request.end_date + timedelta(days=5),
        )
        open_prices, close_prices, volume_data = _build_price_frames(market_data)
        price_download_warnings = _build_price_download_warnings(
            requested_symbols=candidate_universe,
            available_symbols=list(close_prices),
            benchmark_symbol=request.benchmark_symbol,
        )
        if request.ticker and request.ticker.upper() not in close_prices:
            raise ValueError(
                f"Unable to load price history for requested ticker {request.ticker.upper()} from Yahoo Finance. "
                "Try another ticker or use a custom universe CSV with symbols that have available historical bars."
            )

        await _notify(progress_callback, {"stage": "simulating_teams", "progress": 34})
        simulations: list[TeamSimulation] = []
        seed_token = YFinanceAdapter.seed_backtest_history(market_data)
        try:
            for index, snapshot in enumerate(execution_snapshots):
                progress_floor = 34 + int(((index + 1) / max(1, len(execution_snapshots))) * 48)
                await _notify(
                    progress_callback,
                    {
                        "stage": "simulating_team",
                        "progress": progress_floor,
                        "team_id": snapshot.effective_team.team_id,
                        "team_name": snapshot.effective_team.name,
                        "version_number": snapshot.effective_team.version_number,
                    },
                )
                profile = historical_profiles[f"{snapshot.effective_team.team_id}:{snapshot.effective_team.version_number}"]
                simulations.append(
                    await self._simulate_team(
                        request=request,
                        base_settings=user_settings,
                        base_snapshot=snapshot,
                        profile=profile,
                        universe_timeline=universe_timeline,
                        open_prices=open_prices,
                        close_prices=close_prices,
                        volume_data=volume_data,
                        calendar=calendar,
                        rebalance_dates=rebalance_dates,
                        progress_callback=progress_callback,
                        progress_start=34 + int((index / max(1, len(execution_snapshots))) * 48),
                        progress_end=34 + int(((index + 1) / max(1, len(execution_snapshots))) * 48),
                    )
                )
        finally:
            YFinanceAdapter.reset_backtest_history(seed_token)

        primary_run = simulations[0].run
        benchmark_curve = _build_next_open_benchmark_curve(
            request.initial_cash,
            request.benchmark_symbol,
            calendar=calendar,
            open_prices=open_prices,
            close_prices=close_prices,
        )
        benchmark_metrics = compute_metrics(benchmark_curve)

        universe_report = UniverseResolutionReport(
            requested_universe_id=request.universe_id,
            resolved_universe_id=universe_timeline.universe_id,
            source=universe_timeline.source,
            warnings=[*universe_timeline.warnings, *price_download_warnings],
            dates=[
                UniverseDateResolutionReport(
                    as_of_date=item.as_of_date,
                    ticker_count=len(item.tickers),
                    source=item.source,
                    snapshot_hash=item.snapshot_hash,
                    warnings=item.warnings,
                )
                for item in universe_timeline.dates
            ],
        )

        decision_events = [
            event
            for simulation in simulations
            for event in simulation.decision_events
        ]
        primary_event = next((event for event in decision_events if event.team_id == primary_run.team_id), None)

        await _notify(progress_callback, {"stage": "writing_artifact", "progress": 90})
        primary_portfolio_construction = build_portfolio_construction_config(
            request,
            user_settings,
            execution_snapshots[0].effective_team,
        )
        temporal_features = {
            "mode": request.backtest_mode,
            "fidelity_mode": request.fidelity_mode,
            "cache_policy": request.cache_policy,
            "as_of_datetime": request.resolved_as_of_datetime,
            "universe_source": universe_timeline.source,
            "universe_warnings": [*universe_timeline.warnings, *price_download_warnings],
            "team_equivalence_warnings": team_equivalence_warnings,
        }
        artifact = write_artifact(
            config_snapshot=request.model_dump(mode="json"),
            transaction_cost_model={
                "slippage_pct": request.slippage_pct,
                "commission_pct": request.commission_pct,
                "benchmark_symbol": request.benchmark_symbol,
                "rebalance_frequency": request.rebalance_frequency,
                "fidelity_mode": request.fidelity_mode,
                "cache_policy": request.cache_policy,
            },
            portfolio_construction=primary_portfolio_construction.as_dict(),
            metrics=primary_run.metrics,
            execution_snapshot=execution_snapshots[0],
            temporal_features=temporal_features,
            supplemental_payload={
                "team_runs": [simulation.run.model_dump(mode="json") for simulation in simulations],
                "decision_events": [event.model_dump(mode="json") for event in decision_events],
                "historical_gap_report": historical_gap_report.model_dump(mode="json"),
                "universe_resolution_report": universe_report.model_dump(mode="json"),
            },
        )

        warnings = _dedupe(
            [
                *historical_gap_report.warnings,
                *universe_timeline.warnings,
                *price_download_warnings,
                *team_equivalence_warnings,
                *primary_run.notes,
                *primary_run.warnings,
            ]
        )
        result = BacktestResult(
            ticker=request.ticker or request.universe_id,
            universe_id=universe_timeline.universe_id,
            candidate_count=len(universe_timeline.all_tickers),
            rebalance_frequency=request.rebalance_frequency,
            benchmark_symbol=request.benchmark_symbol,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
            fidelity_mode=request.fidelity_mode,
            cache_policy=request.cache_policy,
            shortlist_size=request.shortlist_size,
            top_n_holdings=request.top_n_holdings or request.max_positions,
            portfolio_construction=primary_portfolio_construction.as_dict(),
            metrics=primary_run.metrics,
            benchmark_metrics=benchmark_metrics,
            equity_curve=primary_run.equity_curve,
            trades=primary_run.trades,
            signal_trace=primary_event.signals if primary_event else [],
            debates=(
                [
                    {
                        "bull_case": primary_event.bull_case.model_dump(mode="json") if primary_event and primary_event.bull_case else None,
                        "bear_case": primary_event.bear_case.model_dump(mode="json") if primary_event and primary_event.bear_case else None,
                        "decision": primary_event.decision.model_dump(mode="json") if primary_event else {},
                    }
                ]
                if primary_event
                else []
            ),
            artifact=artifact,
            execution_snapshot=execution_snapshots[0],
            execution_snapshots=execution_snapshots,
            comparison_runs=[simulation.run for simulation in simulations],
            team_runs=[simulation.run for simulation in simulations],
            decision_events=decision_events,
            historical_gap_report=historical_gap_report,
            universe_resolution_report=universe_report,
            team_equivalence_warnings=team_equivalence_warnings,
            warnings=warnings,
        )
        await store_backtest(artifact.artifact_id, result.model_dump(mode="json"))
        await _notify(progress_callback, {"stage": "complete", "progress": 100})
        return result

    async def _normalize_execution_snapshots(
        self,
        request: BacktestRequest,
        user_settings: UserSettings,
        *,
        execution_snapshot: ExecutionSnapshot | None,
        execution_snapshots: list[ExecutionSnapshot] | None,
    ) -> list[ExecutionSnapshot]:
        if execution_snapshots is not None:
            return execution_snapshots
        if execution_snapshot is not None:
            return [execution_snapshot]
        fallback = build_execution_snapshot(
            mode=request.backtest_mode,
            ticker_or_universe=request.universe_descriptor,
            user_settings=user_settings,
            compiled_team=default_compiled_team(),
            data_boundary=DataBoundary(
                mode=request.backtest_mode,  # type: ignore[arg-type]
                as_of_datetime=request.resolved_as_of_datetime,
                allow_latest_semantics=not request.resolved_strict_mode,
            ),
            cost_model={
                "slippage_pct": request.slippage_pct,
                "commission_pct": request.commission_pct,
            },
            notes=["Backtest engine created a fallback execution snapshot."],
        )
        return [fallback]

    async def _simulate_team(
        self,
        *,
        request: BacktestRequest,
        base_settings: UserSettings,
        base_snapshot: ExecutionSnapshot,
        profile: TeamHistoricalProfile,
        universe_timeline: UniverseTimelineResolution,
        open_prices: dict[str, pd.Series],
        close_prices: dict[str, pd.Series],
        volume_data: dict[str, pd.Series],
        calendar: pd.Index,
        rebalance_dates: list[pd.Timestamp],
        progress_callback: ProgressCallback | None,
        progress_start: int,
        progress_end: int,
    ) -> TeamSimulation:
        executable_team = _historical_execution_team(
            base_snapshot.effective_team,
            profile,
            strict_temporal_mode=request.resolved_strict_mode,
        )
        runtime_settings = _build_backtest_settings(base_settings, executable_team)
        portfolio_config = build_portfolio_construction_config(request, runtime_settings, executable_team)
        max_gross_exposure_pct = portfolio_config.max_gross_exposure_pct
        simulation_snapshot = build_execution_snapshot(
            mode=request.backtest_mode,
            ticker_or_universe=base_snapshot.ticker_or_universe,
            user_settings=runtime_settings,
            compiled_team=executable_team,
            data_boundary=base_snapshot.data_boundary,
            cost_model=base_snapshot.cost_model,
            notes=[
                *base_snapshot.notes,
                (
                    "Historical replay executed all enabled agent families; degraded families used replay-safe data and confidence penalties."
                    if not request.resolved_strict_mode and profile.signature.degraded_agents
                    else "Historical replay executed only the agent families that are point-in-time faithful for this mode."
                ),
            ],
        )
        shared_budget = BudgetTracker(
            max_cost_usd=runtime_settings.backtest.max_cost_per_backtest_usd,
            max_tokens=runtime_settings.backtest.max_tokens_per_backtest,
        )
        evaluation_semaphore = asyncio.Semaphore(runtime_settings.backtest.max_parallel_historical_evaluations)
        benchmark_close = close_prices[request.benchmark_symbol].loc[calendar]
        holdings: dict[str, float] = {}
        cash = request.initial_cash
        last_close: dict[str, float] = {}
        pending_targets: dict[pd.Timestamp, dict[str, Any]] = {}
        turnover_value = 0.0
        equity_curve: list[EquityPoint] = []
        trades: list[dict[str, Any]] = []
        holdings_snapshots: list[HoldingsSnapshot] = []
        decision_events: list[DecisionEvent] = []
        cache_hits = 0
        cache_misses = 0
        cache_writes = 0
        sector_cache: dict[str, str] = {}
        cash_history: list[float] = []
        gross_exposure_history: list[float] = []
        position_count_history: list[int] = []
        holding_start_dates: dict[str, pd.Timestamp] = {}
        completed_holding_periods: list[int] = []

        for index, day in enumerate(calendar):
            if day in pending_targets:
                trade_batch = pending_targets.pop(day)
                previous_tickers = set(holdings)
                previous_weights = trade_batch.get("current_weights_pct", {})
                trade_result = _apply_target_weights(
                    day=day,
                    weights=trade_batch["weights"],
                    scores=trade_batch["scores"],
                    team=base_snapshot.effective_team,
                    holdings=holdings,
                    cash=cash,
                    open_prices=open_prices,
                    close_prices=close_prices,
                    slippage_pct=request.slippage_pct,
                    commission_pct=request.commission_pct,
                    reasons=trade_batch.get("reasons", {}),
                    previous_weights=previous_weights,
                )
                cash = trade_result["cash"]
                turnover_value += trade_result["turnover_value"]
                trades.extend(trade_result["trades"])
                holdings_snapshots.append(
                    HoldingsSnapshot(
                        timestamp=day.date().isoformat(),
                        team_id=simulation_snapshot.effective_team.team_id,
                        team_name=simulation_snapshot.effective_team.name,
                        holdings=trade_result["holdings_snapshot"],
                    )
                )
                current_tickers = set(holdings)
                for ticker in current_tickers - previous_tickers:
                    holding_start_dates[ticker] = day
                for ticker in previous_tickers - current_tickers:
                    if ticker in holding_start_dates:
                        completed_holding_periods.append(max(1, (day - holding_start_dates.pop(ticker)).days))

            equity = cash
            invested_value = 0.0
            for ticker, shares in list(holdings.items()):
                close_price = _close_price(close_prices, ticker, day)
                if close_price is not None:
                    last_close[ticker] = close_price
                market_price = last_close.get(ticker)
                if market_price is None:
                    continue
                market_value = shares * market_price
                invested_value += market_value
                equity += market_value
            benchmark_equity = benchmark_close.loc[:day].dropna()
            benchmark_curve = _build_next_open_benchmark_curve(
                request.initial_cash,
                request.benchmark_symbol,
                calendar=benchmark_equity.index,
                open_prices=open_prices,
                close_prices=close_prices,
            )
            equity_curve.append(
                EquityPoint(
                    timestamp=day.date().isoformat(),
                    strategy_equity=round(equity, 2),
                    benchmark_equity=round(benchmark_curve[-1] if benchmark_curve else request.initial_cash, 2),
                )
            )
            if equity > 0:
                cash_history.append((cash / equity) * 100.0)
                gross_exposure_history.append((invested_value / equity) * 100.0)
            else:
                cash_history.append(100.0)
                gross_exposure_history.append(0.0)
            position_count_history.append(len(holdings))
            live_progress = progress_start + int(((index + 1) / max(1, len(calendar))) * max(1, progress_end - progress_start))
            await _notify(
                progress_callback,
                {
                    "stage": "team_live",
                    "progress": min(progress_end, live_progress),
                    "team_live": _build_live_team_update(
                        team=simulation_snapshot.effective_team,
                        day=day,
                        equity=equity,
                        benchmark_equity=benchmark_curve[-1] if benchmark_curve else request.initial_cash,
                        cash=cash,
                        holdings=holdings,
                        last_close=last_close,
                        close_prices=close_prices,
                        gross_exposure_pct=gross_exposure_history[-1],
                        trades=trades,
                        processed_days=index + 1,
                        total_days=len(calendar),
                        processed_rebalances=sum(1 for rebalance_day in rebalance_dates if rebalance_day <= day),
                        total_rebalances=len(rebalance_dates),
                    ),
                },
            )

            if day not in rebalance_dates or index + 1 >= len(calendar):
                continue

            as_of_datetime = _rebalance_close_timestamp(day)
            current_weights_pct = _current_portfolio_weights_pct(
                holdings=holdings,
                cash=cash,
                close_prices=close_prices,
                day=day,
            )
            universe_tickers = _filter_universe_tickers(
                tickers=universe_timeline.tickers_for(day.date()),
                close_prices=close_prices,
                volume_data=volume_data,
                day=day,
                min_price=portfolio_config.min_price,
                min_avg_dollar_volume_millions=portfolio_config.min_avg_dollar_volume_millions,
                liquidity_lookback_days=portfolio_config.liquidity_lookback_days,
                min_history_days=portfolio_config.min_history_days,
            )
            rebalance_candidates = sorted(set(universe_tickers) | set(current_weights_pct))
            if request.fidelity_mode == "hybrid_shortlist" and len(rebalance_candidates) > portfolio_config.candidate_pool_size:
                ranked_shortlist = _build_shortlist(
                    universe_tickers=rebalance_candidates,
                    close_prices=close_prices,
                    volume_data=volume_data,
                    benchmark_window=benchmark_close.loc[:day].dropna(),
                    day=day,
                    shortlist_size=portfolio_config.candidate_pool_size,
                    team_weights=profile.signature.effective_weights,
                )
            else:
                ranked_shortlist = [(ticker, 0.0) for ticker in rebalance_candidates]
            existing_holdings = [ticker for ticker in current_weights_pct if ticker not in {name for name, _ in ranked_shortlist}]
            ranked_shortlist.extend((ticker, 0.0) for ticker in existing_holdings)

            shortlist_map = {ticker: (rank + 1, scout_score) for rank, (ticker, scout_score) in enumerate(ranked_shortlist)}
            candidate_payloads = await asyncio.gather(
                *[
                    self._evaluate_candidate(
                        ticker=ticker,
                        scout_rank=shortlist_map[ticker][0],
                        scout_score=shortlist_map[ticker][1],
                        request=request,
                        runtime_settings=runtime_settings,
                        base_snapshot=simulation_snapshot,
                        as_of_datetime=as_of_datetime,
                        historical_profile=profile,
                        budget=shared_budget,
                        semaphore=evaluation_semaphore,
                    )
                    for ticker, _score in ranked_shortlist
                ]
            )

            next_day = calendar[index + 1]
            sector_cache.update(
                await _load_sector_lookup_for_tickers(
                    [payload.event.ticker for payload in candidate_payloads],
                    sector_cache,
                )
            )
            target_plan = construct_target_weights(
                events=[payload.event for payload in candidate_payloads],
                current_weights_pct=current_weights_pct,
                volatility_by_ticker={
                    payload.event.ticker: _realized_volatility(close_prices.get(payload.event.ticker), day)
                    for payload in candidate_payloads
                },
                sectors=sector_cache,
                config=portfolio_config,
            )
            pending_targets[next_day] = {
                "weights": target_plan.weights,
                "scores": {payload.event.ticker: payload.event.score for payload in candidate_payloads},
                "reasons": {
                    payload.event.ticker: (
                        payload.event.selection_reason
                        if payload.event.target_weight_pct > 0
                        else payload.event.exclusion_reason
                    )
                    for payload in candidate_payloads
                },
                "current_weights_pct": current_weights_pct,
            }
            for payload in candidate_payloads:
                payload.event.execution_date = next_day.date().isoformat()
            for payload in candidate_payloads:
                if payload.event.cache_status == "hit":
                    cache_hits += 1
                else:
                    cache_misses += 1
                    if request.cache_policy == "fresh" or payload.event.cache_status == "write":
                        cache_writes += 1
            decision_events.extend(candidate.event for candidate in candidate_payloads)
            AuditLogger.log(
                "backtest",
                "portfolio_rebalance",
                {
                    "team_id": simulation_snapshot.effective_team.team_id,
                    "team_name": simulation_snapshot.effective_team.name,
                    "version_number": simulation_snapshot.effective_team.version_number,
                    "rebalance_date": day.date().isoformat(),
                    "execution_date": next_day.date().isoformat(),
                    "portfolio_construction": portfolio_config.as_dict(),
                    "selected_tickers": target_plan.selected_tickers,
                    "excluded_tickers": target_plan.excluded_tickers,
                    "replaced_tickers": target_plan.replaced_tickers,
                    "target_gross_pct": target_plan.target_gross_pct,
                    "target_cash_pct": target_plan.target_cash_pct,
                    "turnover_pct": target_plan.turnover_pct,
                },
            )

        for ticker, started_at in list(holding_start_dates.items()):
            completed_holding_periods.append(max(1, (calendar[-1] - started_at).days))
        sectors = await _load_sector_lookup(holdings_snapshots)
        max_sector_concentration = _max_sector_concentration(holdings_snapshots, sectors)
        metrics = compute_metrics([point.strategy_equity for point in equity_curve])
        metrics["turnover_pct"] = round((turnover_value / request.initial_cash) * 100.0, 2)
        metrics["max_sector_concentration_pct"] = round(max_sector_concentration, 2)
        metrics["average_cash_pct"] = round(sum(cash_history) / max(1, len(cash_history)), 2)
        metrics["average_gross_exposure_pct"] = round(
            sum(gross_exposure_history) / max(1, len(gross_exposure_history)),
            2,
        )
        metrics["average_position_count"] = round(
            sum(position_count_history) / max(1, len(position_count_history)),
            2,
        )
        metrics["average_holding_period_days"] = round(
            sum(completed_holding_periods) / max(1, len(completed_holding_periods)),
            2,
        )
        metrics["max_name_weight_pct"] = round(_max_name_weight_pct(holdings_snapshots), 2)
        metrics["average_concentration_hhi"] = round(_average_concentration_hhi(holdings_snapshots), 4)

        run = TeamBacktestRun(
            team_id=simulation_snapshot.effective_team.team_id,
            team_name=simulation_snapshot.effective_team.name,
            version_number=simulation_snapshot.effective_team.version_number,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            turnover_pct=metrics["turnover_pct"],
            max_sector_concentration_pct=metrics["max_sector_concentration_pct"],
            top_holdings_over_time=holdings_snapshots,
            supported_agents=[
                agent
                for agent in simulation_snapshot.effective_team.enabled_agents
                if agent in VALID_ANALYSIS_AGENTS
            ],
            degraded_agents=profile.signature.degraded_agents,
            excluded_agents=profile.signature.ignored_agents,
            notes=_dedupe(
                [
                    profile.signature.summary,
                    (
                        "Historical replay executed degraded agent families with confidence penalties and replay-safe source substitutions."
                        if profile.signature.degraded_agents and not request.resolved_strict_mode
                        else "Historical replay executed only point-in-time faithful agent families; degraded families remain diagnostic-only."
                    )
                    if profile.signature.degraded_agents
                    else "",
                    (
                        f"Configured target holdings ({portfolio_config.top_n_holdings}) and max position cap "
                        f"({portfolio_config.max_position_pct:.2f}%) limit gross exposure to about "
                        f"{max_gross_exposure_pct:.1f}% before any additional macro or risk gating."
                    )
                    if max_gross_exposure_pct < 100.0
                    else "",
                    (
                        f"Portfolio construction used {portfolio_config.weighting_mode} weighting with a "
                        f"{portfolio_config.replacement_threshold:.2f} replacement threshold and "
                        f"{portfolio_config.hold_zone_pct:.2f}% hold zone."
                    ),
                ]
            ),
            warnings=[gap.reason for gap in profile.gaps],
            effective_signature=profile.signature,
            cache_usage=CacheUsageSummary(hits=cache_hits, misses=cache_misses, writes=cache_writes),
        )
        return TeamSimulation(run=run, decision_events=decision_events)

    async def _evaluate_candidate(
        self,
        *,
        ticker: str,
        scout_rank: int,
        scout_score: float,
        request: BacktestRequest,
        runtime_settings: UserSettings,
        base_snapshot: ExecutionSnapshot,
        as_of_datetime: str,
        historical_profile: TeamHistoricalProfile,
        budget: BudgetTracker,
        semaphore: asyncio.Semaphore,
    ) -> CandidateEvaluation:
        data_boundary = DataBoundary(
            mode=request.backtest_mode,  # type: ignore[arg-type]
            as_of_datetime=as_of_datetime,
            allow_latest_semantics=not request.resolved_strict_mode,
        )
        evaluation_snapshot = build_execution_snapshot(
            mode=request.backtest_mode,
            ticker_or_universe=ticker,
            user_settings=runtime_settings,
            compiled_team=base_snapshot.effective_team,
            data_boundary=data_boundary,
            cost_model=base_snapshot.cost_model,
            notes=_evaluation_notes(request.fidelity_mode, ticker, as_of_datetime, historical_profile),
        )
        cache_key = build_pipeline_cache_key(
            execution_snapshot=evaluation_snapshot,
            ticker=ticker,
            as_of_datetime=as_of_datetime,
            fidelity_mode=request.fidelity_mode,
            backtest_mode=request.backtest_mode,
        )
        cache_status = "miss"

        if request.cache_policy == "reuse":
            cached = await load_cached_pipeline_result(cache_key)
            if cached:
                signals = [AgentSignal.model_validate(item) for item in cached.get("signals", [])]
                bull_case = DebateOutput.model_validate(item) if (item := cached.get("bull_case")) else None
                bear_case = DebateOutput.model_validate(item) if (item := cached.get("bear_case")) else None
                decision = PortfolioDecision.model_validate(cached["decision"])
                warnings = list(cached.get("warnings", []))
                score = float(cached.get("score", 0.0))
                event = DecisionEvent(
                    rebalance_date=as_of_datetime[:10],
                    execution_date=as_of_datetime[:10],
                    team_id=base_snapshot.effective_team.team_id,
                    team_name=base_snapshot.effective_team.name,
                    version_number=base_snapshot.effective_team.version_number,
                    ticker=ticker,
                    shortlist_rank=scout_rank,
                    shortlisted=True,
                    selected_for_execution=decision.action == "BUY" and score > 0,
                    cache_status="hit",
                    score=score,
                    target_weight_pct=0.0,
                    signals=signals,
                    bull_case=bull_case,
                    bear_case=bear_case,
                    decision=decision,
                    warnings=warnings,
                )
                return CandidateEvaluation(event=event, price_open=None, price_close=None)

        try:
            async with semaphore:
                signals, bull_case, bear_case, decision = await run_agent_pipeline(
                    ticker,
                    runtime_settings,
                    evaluation_snapshot,
                    budget=budget,
                )
        except Exception as exc:
            return CandidateEvaluation(
                event=_failed_candidate_event(
                    ticker=ticker,
                    scout_rank=scout_rank,
                    team=base_snapshot.effective_team,
                    rebalance_date=as_of_datetime[:10],
                    execution_date=as_of_datetime[:10],
                    warning=f"Replay pipeline failed for {ticker}: {exc}",
                ),
                price_open=None,
                price_close=None,
            )
        signals, bull_case, bear_case, decision, warnings = _apply_historical_penalties(
            signals=signals,
            bull_case=bull_case,
            bear_case=bear_case,
            decision=decision,
            runtime_settings=runtime_settings,
            historical_profile=historical_profile,
            team_weights=base_snapshot.effective_team.agent_weights,
            ticker=ticker,
        )
        score = max(0.0, decision.priority_score) if decision.direction_score >= 0 else -decision.priority_score
        selected_for_execution = decision.action == "BUY" and score > 0
        event = DecisionEvent(
            rebalance_date=as_of_datetime[:10],
            execution_date=as_of_datetime[:10],
            team_id=base_snapshot.effective_team.team_id,
            team_name=base_snapshot.effective_team.name,
            version_number=base_snapshot.effective_team.version_number,
            ticker=ticker,
            shortlist_rank=scout_rank,
            shortlisted=True,
            selected_for_execution=selected_for_execution,
            cache_status=cache_status,
            score=round(score + (scout_score * 0.05), 6),
            target_weight_pct=0.0,
            signals=signals,
            bull_case=bull_case,
            bear_case=bear_case,
            decision=decision,
            warnings=warnings,
        )
        if request.cache_policy in {"reuse", "fresh"}:
            await store_cached_pipeline_result(
                cache_key,
                {
                    "signals": [signal.model_dump(mode="json") for signal in signals],
                    "bull_case": bull_case.model_dump(mode="json") if bull_case else None,
                    "bear_case": bear_case.model_dump(mode="json") if bear_case else None,
                    "decision": decision.model_dump(mode="json"),
                    "warnings": warnings,
                    "score": event.score,
                },
            )
            event.cache_status = "write"
        return CandidateEvaluation(event=event, price_open=None, price_close=None)


async def stream_backtest_progress(
    request: BacktestRequest,
    user_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot | None = None,
    execution_snapshots: list[ExecutionSnapshot] | None = None,
):
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def _progress(event: dict[str, Any]) -> None:
        await queue.put({"event": "progress", "data": event})

    async def _worker() -> None:
        try:
            result = await BacktestEngine().run(
                request,
                user_settings,
                execution_snapshot=execution_snapshot,
                execution_snapshots=execution_snapshots,
                progress_callback=_progress,
            )
            await queue.put({"event": "complete", "data": result.model_dump(mode="json")})
        except Exception as exc:  # pragma: no cover - streamed error path
            await queue.put({"event": "error", "data": {"detail": str(exc)}})
        finally:
            await queue.put(None)

    task = asyncio.create_task(_worker())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        await task


async def run_backtest(
    request: BacktestRequest,
    user_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot | None = None,
    execution_snapshots: list[ExecutionSnapshot] | None = None,
    progress_callback: ProgressCallback | None = None,
):
    return await BacktestEngine().run(
        request,
        user_settings,
        execution_snapshot=execution_snapshot,
        execution_snapshots=execution_snapshots,
        progress_callback=progress_callback,
    )


async def _notify(progress_callback: ProgressCallback | None, payload: dict[str, Any]) -> None:
    if progress_callback is None:
        return
    maybe_awaitable = progress_callback(payload)
    if asyncio.iscoroutine(maybe_awaitable):
        await maybe_awaitable


def _build_backtest_settings(user_settings: UserSettings, compiled_team) -> UserSettings:
    runtime = apply_team_overrides(user_settings, compiled_team)
    payload = runtime.to_dict()
    payload["llm"]["max_cost_per_session_usd"] = runtime.backtest.max_cost_per_backtest_usd
    payload["llm"]["max_tokens_per_request"] = max(
        runtime.llm.max_tokens_per_request,
        min(runtime.backtest.max_tokens_per_backtest, 16_000),
    )
    return UserSettings.from_dict(payload)


def _historical_execution_team(
    team: CompiledTeam,
    historical_profile: TeamHistoricalProfile,
    *,
    strict_temporal_mode: bool,
) -> CompiledTeam:
    if strict_temporal_mode:
        executable_analysis = [
            agent
            for agent in team.enabled_agents
            if agent in historical_profile.signature.honored_agents
        ]
    else:
        executable_analysis = [
            agent
            for agent in team.enabled_agents
            if agent in VALID_ANALYSIS_AGENTS and float(team.agent_weights.get(agent, 0)) > 0
        ]
    enabled_agents = [
        agent
        for agent in team.enabled_agents
        if agent in executable_analysis or agent in REQUIRED_DECISION_AGENTS
    ]
    executable_specs = {
        agent_name: spec
        for agent_name, spec in team.compiled_agent_specs.items()
        if agent_name in executable_analysis
    }
    executable_weights = {
        agent_name: int(team.agent_weights.get(agent_name, spec.weight))
        for agent_name, spec in executable_specs.items()
    }
    return team.model_copy(
        update={
            "enabled_agents": enabled_agents,
            "agent_weights": executable_weights,
            "compiled_agent_specs": executable_specs,
        },
        deep=True,
    )


def _validate_backtest_workload(
    *,
    request: BacktestRequest,
    user_settings: UserSettings,
    execution_snapshots: list[ExecutionSnapshot],
    historical_profiles: dict[str, TeamHistoricalProfile],
    universe_timeline: UniverseTimelineResolution,
    rebalance_dates: list[pd.Timestamp],
) -> None:
    if request.fidelity_mode != "full_loop":
        return

    candidate_evaluations = sum(len(universe_timeline.tickers_for(day.date())) for day in rebalance_dates)
    violations: list[str] = []
    for snapshot in execution_snapshots:
        profile = historical_profiles[f"{snapshot.effective_team.team_id}:{snapshot.effective_team.version_number}"]
        executable_team = _historical_execution_team(
            snapshot.effective_team,
            profile,
            strict_temporal_mode=request.resolved_strict_mode,
        )
        analysis_agent_count = len(
            [agent for agent in executable_team.enabled_agents if agent in VALID_ANALYSIS_AGENTS]
        )
        if analysis_agent_count <= 0:
            continue
        runtime_settings = _build_backtest_settings(user_settings, executable_team)
        estimated_tokens = candidate_evaluations * analysis_agent_count * ESTIMATED_TOKENS_PER_AGENT_CALL
        if estimated_tokens > runtime_settings.backtest.max_tokens_per_backtest:
            violations.append(
                f"{snapshot.effective_team.name} v{snapshot.effective_team.version_number} needs about "
                f"{estimated_tokens:,} analysis tokens for full-loop replay, above the configured "
                f"backtest limit of {runtime_settings.backtest.max_tokens_per_backtest:,}. "
                "Use hybrid_shortlist, shorten the window, enable cache reuse, or raise the backtest token budget."
            )

    if violations:
        raise ValueError(" ".join(violations))


def _evaluation_notes(
    fidelity_mode: str,
    ticker: str,
    as_of_datetime: str,
    historical_profile: TeamHistoricalProfile,
) -> list[str]:
    notes = [f"Historical {fidelity_mode} evaluation for {ticker} on {as_of_datetime}."]
    if historical_profile.signature.summary:
        notes.append(historical_profile.signature.summary)
    return notes


def _failed_candidate_event(
    *,
    ticker: str,
    scout_rank: int,
    team,
    rebalance_date: str,
    execution_date: str,
    warning: str,
) -> DecisionEvent:
    return DecisionEvent(
        rebalance_date=rebalance_date,
        execution_date=execution_date,
        team_id=team.team_id,
        team_name=team.name,
        version_number=team.version_number,
        ticker=ticker,
        shortlist_rank=scout_rank,
        shortlisted=True,
        selected_for_execution=False,
        cache_status="error",
        score=0.0,
        target_weight_pct=0.0,
        signals=[],
        bull_case=None,
        bear_case=None,
        decision=PortfolioDecision(
            ticker=ticker,
            action="HOLD",
            confidence=0.0,
            reasoning="Historical replay downgraded this ticker because one of its agent evaluations failed.",
            cited_agents=[],
            bull_points_used=[],
            bear_points_addressed=[],
            risk_notes=warning,
            proposed_position_pct=0.0,
        ),
        warnings=[warning],
    )


def _apply_historical_penalties(
    *,
    signals: list[AgentSignal],
    bull_case: DebateOutput | None,
    bear_case: DebateOutput | None,
    decision: PortfolioDecision,
    runtime_settings: UserSettings,
    historical_profile: TeamHistoricalProfile,
    team_weights: dict[str, int],
    ticker: str,
) -> tuple[list[AgentSignal], DebateOutput | None, DebateOutput | None, PortfolioDecision, list[str]]:
    warnings: list[str] = []
    mutated = False
    for signal in signals:
        support = historical_profile.support_by_agent.get(signal.source_agent_name or signal.agent_name)
        if not support or support.support_level == "full":
            continue
        factor = DEGRADATION_FACTORS[support.support_level]
        degraded_confidence = round(signal.final_confidence * factor, 4)
        if degraded_confidence != signal.final_confidence:
            mutated = True
            signal.final_confidence = degraded_confidence
        extra_warning = f"Historical {support.support_level} mode: {support.reason}"
        signal.warning = " ".join(filter(None, [signal.warning, extra_warning])).strip()
        warnings.append(f"{signal.agent_name}: {support.reason}")

    if not mutated:
        return signals, bull_case, bear_case, decision, _dedupe(warnings)

    rebuilt_bull = build_bull_case(signals) if runtime_settings.agents.enable_bull_bear_debate else None
    rebuilt_bear = build_bear_case(signals) if runtime_settings.agents.enable_bull_bear_debate else None
    risk = evaluate_risk(signals, runtime_settings.guardrails, runtime_settings.agents)
    rebuilt_decision = decide_portfolio_action(
        ticker=ticker,
        signals=signals,
        bull_case=rebuilt_bull,
        bear_case=rebuilt_bear,
        proposed_position_pct=risk.proposed_position_pct,
        agent_weights=team_weights,
        risk_notes=risk.notes if risk.allowed else f"Trade blocked: {risk.notes}",
        max_data_age_minutes=runtime_settings.data_sources.max_data_age_minutes,
    )
    if not risk.allowed:
        rebuilt_decision.action = "HOLD"
        rebuilt_decision.proposed_position_pct = 0.0
    return signals, rebuilt_bull, rebuilt_bear, rebuilt_decision, _dedupe(warnings)


async def _download_market_data(
    symbols: list[str],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    chunks = [symbols[index : index + 64] for index in range(0, len(symbols), 64)]
    merged: dict[str, pd.DataFrame] = {}
    for chunk in chunks:
        payload = await asyncio.to_thread(_download_chunk, chunk, start_date, end_date)
        merged.update(payload)
    return merged


def _download_chunk(chunk: list[str], start_date: date, end_date: date) -> dict[str, pd.DataFrame]:
    with _suppress_yfinance_output():
        frame = yf.download(
            tickers=chunk,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=False,
        )
    if frame.empty:
        return {}

    result: dict[str, pd.DataFrame] = {}
    if isinstance(frame.columns, pd.MultiIndex):
        available_tickers = set(frame.columns.get_level_values(0))
        for ticker in chunk:
            if ticker not in available_tickers:
                continue
            item = frame[ticker].copy()
            if item.empty:
                continue
            item.index = pd.to_datetime(item.index).tz_localize(None)
            result[ticker] = item
        missing = [ticker for ticker in chunk if ticker not in result]
        for ticker in missing:
            fallback = _download_single_symbol(ticker, start_date, end_date)
            if not fallback.empty:
                result[ticker] = fallback
        return result

    item = frame.copy()
    item.index = pd.to_datetime(item.index).tz_localize(None)
    result[chunk[0]] = item
    return result


def _build_price_frames(
    payload: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.Series], dict[str, pd.Series], dict[str, pd.Series]]:
    opens: dict[str, pd.Series] = {}
    closes: dict[str, pd.Series] = {}
    volumes: dict[str, pd.Series] = {}
    for ticker, frame in payload.items():
        lower_columns = {str(column).strip().lower(): column for column in frame.columns}
        open_column = lower_columns.get("open")
        close_column = lower_columns.get("close")
        volume_column = lower_columns.get("volume")
        if open_column is None or close_column is None:
            continue
        opens[ticker] = pd.to_numeric(frame[open_column], errors="coerce")
        closes[ticker] = pd.to_numeric(frame[close_column], errors="coerce")
        if volume_column is not None:
            volumes[ticker] = pd.to_numeric(frame[volume_column], errors="coerce")
    return opens, closes, volumes


def _build_price_download_warnings(
    *,
    requested_symbols: list[str],
    available_symbols: list[str],
    benchmark_symbol: str,
) -> list[str]:
    available = set(available_symbols)
    missing = [
        symbol for symbol in requested_symbols if symbol not in available and symbol not in {benchmark_symbol, "TLT", "^VIX"}
    ]
    if not missing:
        return []
    sample = ", ".join(missing[:12])
    suffix = "" if len(missing) <= 12 else f", +{len(missing) - 12} more"
    return [
        (
            f"Yahoo Finance price history was unavailable for {len(missing)} universe symbols. "
            f"Those names were excluded from the backtest shortlist/simulation. Examples: {sample}{suffix}."
        )
    ]


def _build_live_team_update(
    *,
    team,
    day: pd.Timestamp,
    equity: float,
    benchmark_equity: float,
    cash: float,
    holdings: dict[str, float],
    last_close: dict[str, float],
    close_prices: dict[str, pd.Series],
    gross_exposure_pct: float,
    trades: list[dict[str, Any]],
    processed_days: int,
    total_days: int,
    processed_rebalances: int,
    total_rebalances: int,
) -> dict[str, Any]:
    holdings_rows: list[dict[str, Any]] = []
    for ticker, shares in holdings.items():
        close_price = _close_price(close_prices, ticker, day) or last_close.get(ticker)
        if close_price is None:
            continue
        market_value = shares * close_price
        weight_pct = 0.0 if equity <= 0 else (market_value / equity) * 100.0
        holdings_rows.append(
            {
                "ticker": ticker,
                "shares": round(float(shares), 6),
                "price": round(float(close_price), 4),
                "market_value": round(float(market_value), 2),
                "weight_pct": round(float(weight_pct), 2),
            }
        )
    holdings_rows.sort(key=lambda item: float(item["market_value"]), reverse=True)
    return {
        "team_id": team.team_id,
        "team_name": team.name,
        "version_number": team.version_number,
        "timestamp": day.date().isoformat(),
        "strategy_equity": round(float(equity), 2),
        "benchmark_equity": round(float(benchmark_equity), 2),
        "cash": round(float(cash), 2),
        "gross_exposure_pct": round(float(gross_exposure_pct), 2),
        "holdings_count": len(holdings_rows),
        "holdings": holdings_rows[:5],
        "recent_trades": trades[-5:],
        "processed_days": processed_days,
        "total_days": total_days,
        "processed_rebalances": processed_rebalances,
        "total_rebalances": total_rebalances,
    }


def _rebalance_dates(calendar: pd.Index, frequency: str) -> list[pd.Timestamp]:
    dates = list(calendar)
    if frequency == "daily":
        return dates[:-1]

    grouped: list[pd.Timestamp] = []
    if frequency in {"weekly", "biweekly"}:
        seen: dict[tuple[int, int], pd.Timestamp] = {}
        for day in dates:
            key = (day.isocalendar().year, day.isocalendar().week)
            seen[key] = day
        grouped = [seen[key] for key in sorted(seen)]
        if frequency == "biweekly":
            grouped = grouped[::2]
        return grouped[:-1] if len(grouped) > 1 else grouped

    seen_months: dict[tuple[int, int], pd.Timestamp] = {}
    for day in dates:
        key = (day.year, day.month)
        seen_months[key] = day
    grouped = [seen_months[key] for key in sorted(seen_months)]
    return grouped[:-1] if len(grouped) > 1 else grouped


def _build_shortlist(
    *,
    universe_tickers: list[str],
    close_prices: dict[str, pd.Series],
    volume_data: dict[str, pd.Series],
    benchmark_window: pd.Series,
    day: pd.Timestamp,
    shortlist_size: int,
    team_weights: dict[str, float],
) -> list[tuple[str, float]]:
    ranked: list[tuple[str, float]] = []
    for ticker in universe_tickers:
        asset_window = close_prices.get(ticker, pd.Series(dtype=float)).loc[:day].dropna()
        if len(asset_window) < 70:
            continue
        momentum_score = _momentum_score(asset_window, benchmark_window)
        technical_score = _technical_score(asset_window)
        liquidity_score = _liquidity_score(
            price_window=asset_window,
            volume_window=volume_data.get(ticker, pd.Series(dtype=float)).loc[:day].dropna(),
        )
        volatility_score = _volatility_scout_score(asset_window)
        numerator = 0.0
        denominator = 0.0
        if team_weights.get("momentum", 0) > 0:
            numerator += momentum_score * float(team_weights["momentum"])
            denominator += float(team_weights["momentum"])
        if team_weights.get("technicals", 0) > 0:
            numerator += technical_score * float(team_weights["technicals"])
            denominator += float(team_weights["technicals"])
        core_score = numerator / denominator if denominator > 0 else (momentum_score + technical_score) / 2.0
        score = (core_score * 0.75) + (liquidity_score * 0.15) + (volatility_score * 0.10)
        if score > -0.2:
            ranked.append((ticker, round(score, 6)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:shortlist_size]


def _momentum_score(asset_window: pd.Series, benchmark_window: pd.Series) -> float:
    score = 0.0
    for lookback, weight in ((21, 0.5), (63, 0.3), (126, 0.2)):
        asset_return = _period_return(asset_window, lookback)
        benchmark_return = _period_return(benchmark_window, lookback)
        if asset_return is None or benchmark_return is None:
            continue
        score += (asset_return - benchmark_return) * 4.0 * weight
    return _clamp(score)


def _technical_score(asset_window: pd.Series) -> float:
    closes = asset_window.dropna()
    if len(closes) < 50:
        return 0.0
    latest = float(closes.iloc[-1])
    sma20 = float(closes.tail(20).mean())
    sma50 = float(closes.tail(50).mean())
    sma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else sma50
    delta = closes.diff()
    avg_gain = float(delta.clip(lower=0).tail(14).mean())
    avg_loss = float((-delta.clip(upper=0)).tail(14).mean())
    rsi = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))

    score = 0.0
    score += 0.25 if latest > sma20 else -0.25
    score += 0.3 if sma20 > sma50 else -0.3
    score += 0.25 if sma50 > sma200 else -0.25
    if 50 <= rsi <= 70:
        score += 0.2
    elif rsi < 30:
        score += 0.1
    elif rsi > 75:
        score -= 0.15
    return _clamp(score)


def _liquidity_score(price_window: pd.Series, volume_window: pd.Series) -> float:
    if price_window.empty or volume_window.empty:
        return 0.0
    merged = pd.concat([price_window.rename("price"), volume_window.rename("volume")], axis=1).dropna().tail(30)
    if merged.empty:
        return 0.0
    avg_dollar_volume = float((merged["price"] * merged["volume"]).mean())
    if avg_dollar_volume >= 100_000_000:
        return 0.25
    if avg_dollar_volume >= 50_000_000:
        return 0.15
    if avg_dollar_volume >= 25_000_000:
        return 0.05
    return -0.1


def _volatility_scout_score(asset_window: pd.Series) -> float:
    closes = asset_window.dropna()
    if len(closes) < 40:
        return 0.0
    returns = closes.pct_change().dropna().tail(60)
    if returns.empty:
        return 0.0
    annualized = float(returns.std() * (252**0.5))
    if annualized <= 0.20:
        return 0.15
    if annualized <= 0.35:
        return 0.05
    if annualized <= 0.50:
        return -0.02
    return -0.12


def _period_return(series: pd.Series, lookback: int) -> float | None:
    cleaned = series.dropna()
    if len(cleaned) <= lookback:
        return None
    start = float(cleaned.iloc[-lookback - 1])
    end = float(cleaned.iloc[-1])
    if start == 0:
        return None
    return (end / start) - 1.0


def _target_weights_from_decisions(
    *,
    evaluations: list[CandidateEvaluation],
    weighting_method: str,
    max_positions: int,
) -> dict[str, float]:
    candidates = [
        item.event
        for item in evaluations
        if item.event.selected_for_execution and item.event.decision.action == "BUY" and item.event.score > 0
    ]
    candidates.sort(key=lambda event: event.score, reverse=True)
    selected = candidates[:max_positions]
    if not selected:
        return {}

    if weighting_method == "confidence_weighted":
        raw_weights = [max(event.decision.confidence * max(event.score, 0.01), 0.01) for event in selected]
    else:
        raw_weights = [1.0 for _event in selected]

    total = sum(raw_weights)
    if total <= 0:
        return {}

    caps = [max(0.0, event.decision.proposed_position_pct / 100.0) for event in selected]
    gross_target = min(1.0, sum(caps))
    if gross_target <= 0:
        return {}

    resolved_weights = _allocate_capped_weights(raw_weights, caps, gross_target)
    weights: dict[str, float] = {}
    for event, weight in zip(selected, resolved_weights, strict=True):
        weights[event.ticker] = round(weight, 6)
        event.target_weight_pct = round(weight * 100.0, 2)
    return weights


def _allocate_capped_weights(raw_weights: list[float], caps: list[float], gross_target: float) -> list[float]:
    weights = [0.0 for _ in raw_weights]
    remaining = min(gross_target, sum(caps))
    active = [index for index, cap in enumerate(caps) if cap > 0]
    if remaining <= 0 or not active:
        return weights

    while active and remaining > 1e-9:
        active_total = sum(raw_weights[index] for index in active)
        if active_total <= 0:
            equal_share = remaining / len(active)
            for index in list(active):
                room = caps[index] - weights[index]
                allocation = min(equal_share, room)
                weights[index] += allocation
            break

        saturated: list[int] = []
        distributed = 0.0
        for index in active:
            room = max(0.0, caps[index] - weights[index])
            if room <= 1e-9:
                saturated.append(index)
                continue
            desired = remaining * (raw_weights[index] / active_total)
            allocation = min(desired, room)
            weights[index] += allocation
            distributed += allocation
            if room - allocation <= 1e-9:
                saturated.append(index)

        active = [index for index in active if index not in saturated]
        new_remaining = gross_target - sum(weights)
        if abs(new_remaining - remaining) <= 1e-9 or distributed <= 1e-9:
            break
        remaining = new_remaining

    return [max(0.0, min(weight, cap)) for weight, cap in zip(weights, caps, strict=True)]


def _download_single_symbol(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    for candidate in _yahoo_symbol_candidates(symbol):
        with _suppress_yfinance_output():
            frame = yf.Ticker(candidate).history(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=False,
                actions=False,
            )
        if frame.empty:
            continue
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        return frame
    return pd.DataFrame()


def _yahoo_symbol_candidates(symbol: str) -> list[str]:
    normalized = symbol.strip().upper().replace(".", "-")
    if not normalized or normalized[0].isdigit():
        return []
    if normalized.endswith("-W") or normalized.endswith("-WI"):
        return []
    candidates = [normalized]
    alias = YAHOO_SYMBOL_ALIASES.get(normalized)
    if alias and alias not in candidates:
        candidates.insert(0, alias)
    return candidates


@contextmanager
def _suppress_yfinance_output():
    sink = StringIO()
    with redirect_stdout(sink), redirect_stderr(sink):
        yield


def _apply_target_weights(
    *,
    day: pd.Timestamp,
    weights: dict[str, float],
    scores: dict[str, float],
    team,
    holdings: dict[str, float],
    cash: float,
    open_prices: dict[str, pd.Series],
    close_prices: dict[str, pd.Series],
    slippage_pct: float,
    commission_pct: float,
    reasons: dict[str, str] | None = None,
    previous_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    reasons = reasons or {}
    previous_weights = previous_weights or {}
    execution_prices = {
        ticker: _execution_price(open_prices, close_prices, ticker, day)
        for ticker in set(holdings) | set(weights)
    }
    portfolio_value = cash + sum(
        shares * execution_prices[ticker]
        for ticker, shares in holdings.items()
        if execution_prices.get(ticker) is not None
    )
    investable_value = max(0.0, portfolio_value)
    target_values = {ticker: investable_value * float(weight) for ticker, weight in weights.items()}
    current_values = {
        ticker: holdings.get(ticker, 0.0) * (execution_prices.get(ticker) or 0.0)
        for ticker in set(holdings) | set(target_values)
    }
    trades: list[dict[str, Any]] = []
    turnover_value = 0.0
    for ticker in set(holdings) | set(target_values):
        price = execution_prices.get(ticker)
        if price is None or price <= 0:
            continue
        current_value = current_values.get(ticker, 0.0)
        target_value = target_values.get(ticker, 0.0)
        delta_value = target_value - current_value
        if abs(delta_value) < 1e-6:
            continue
        cost = compute_transaction_cost(
            entry_notional=abs(delta_value),
            slippage_pct=slippage_pct,
            commission_pct=commission_pct,
        )
        cash -= delta_value
        cash -= cost
        turnover_value += abs(delta_value)
        target_shares = target_value / price if target_value > 0 else 0.0
        if target_shares > 0:
            holdings[ticker] = target_shares
        else:
            holdings.pop(ticker, None)
        trades.append(
            {
                "timestamp": day.date().isoformat(),
                "ticker": ticker,
                "action": "BUY" if delta_value > 0 else "SELL",
                "fill_price": round(price, 4),
                "notional_usd": round(abs(delta_value), 2),
                "cost_usd": round(cost, 2),
                "previous_weight_pct": round(float(previous_weights.get(ticker, 0.0)), 2),
                "weight_pct": round((weights.get(ticker, 0.0) * 100.0), 2),
                "team_id": team.team_id,
                "team_name": team.name,
                "version_number": team.version_number,
                "score": round(float(scores.get(ticker, 0.0)), 4),
                "reason": reasons.get(ticker, ""),
            }
        )
    holdings_snapshot = [
        {
            "ticker": ticker,
            "weight_pct": round(weight * 100.0, 2),
            "score": round(float(scores.get(ticker, 0.0)), 4),
        }
        for ticker, weight in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    return {
        "cash": cash,
        "turnover_value": turnover_value,
        "trades": trades,
        "holdings_snapshot": holdings_snapshot,
    }


def _decision_score(signals: list[AgentSignal], agent_weights: dict[str, int]) -> float:
    total_weight = 0.0
    score = 0.0
    for signal in signals:
        direction = 1.0 if signal.action == "BUY" else -1.0 if signal.action == "SELL" else 0.0
        weight = float(
            agent_weights.get(
                signal.agent_name,
                agent_weights.get(
                    signal.agent_name.lower(),
                    agent_weights.get(signal.source_agent_name or "", 50),
                ),
            )
        )
        total_weight += weight
        score += direction * signal.final_confidence * weight
    if total_weight <= 0:
        return 0.0
    return round(score / total_weight, 6)


def _current_portfolio_weights_pct(
    *,
    holdings: dict[str, float],
    cash: float,
    close_prices: dict[str, pd.Series],
    day: pd.Timestamp,
) -> dict[str, float]:
    position_values: dict[str, float] = {}
    portfolio_value = cash
    for ticker, shares in holdings.items():
        close_price = _close_price(close_prices, ticker, day)
        if close_price is None:
            continue
        position_value = shares * close_price
        position_values[ticker] = position_value
        portfolio_value += position_value
    if portfolio_value <= 0:
        return {}
    return {
        ticker: round((value / portfolio_value) * 100.0, 4)
        for ticker, value in position_values.items()
    }


def _filter_universe_tickers(
    *,
    tickers: list[str],
    close_prices: dict[str, pd.Series],
    volume_data: dict[str, pd.Series],
    day: pd.Timestamp,
    min_price: float,
    min_avg_dollar_volume_millions: float,
    liquidity_lookback_days: int,
    min_history_days: int,
) -> list[str]:
    filtered: list[str] = []
    fallback: list[str] = []
    for ticker in tickers:
        prices = close_prices.get(ticker, pd.Series(dtype=float)).loc[:day].dropna()
        volumes = volume_data.get(ticker, pd.Series(dtype=float)).loc[:day].dropna()
        if len(prices) >= 40 and float(prices.iloc[-1]) >= min_price:
            fallback.append(ticker)
        if len(prices) < min_history_days:
            continue
        last_price = float(prices.iloc[-1])
        if last_price < min_price:
            continue
        merged = pd.concat([prices.rename("price"), volumes.rename("volume")], axis=1).dropna().tail(liquidity_lookback_days)
        if merged.empty:
            continue
        avg_dollar_volume = float((merged["price"] * merged["volume"]).mean()) / 1_000_000.0
        if avg_dollar_volume < min_avg_dollar_volume_millions:
            continue
        filtered.append(ticker)
    return filtered or fallback


def _realized_volatility(series: pd.Series | None, day: pd.Timestamp) -> float:
    if series is None:
        return 0.25
    returns = series.loc[:day].dropna().pct_change().dropna().tail(60)
    if returns.empty:
        return 0.25
    return float(returns.std() * (252**0.5))


def _max_name_weight_pct(holdings_over_time: list[HoldingsSnapshot]) -> float:
    max_weight = 0.0
    for snapshot in holdings_over_time:
        for holding in snapshot.holdings:
            max_weight = max(max_weight, float(holding.get("weight_pct", 0.0)))
    return max_weight


def _average_concentration_hhi(holdings_over_time: list[HoldingsSnapshot]) -> float:
    if not holdings_over_time:
        return 0.0
    values: list[float] = []
    for snapshot in holdings_over_time:
        weights = [float(holding.get("weight_pct", 0.0)) / 100.0 for holding in snapshot.holdings]
        if not weights:
            continue
        values.append(sum(weight * weight for weight in weights))
    return sum(values) / max(1, len(values))


def _build_next_open_benchmark_curve(
    starting_cash: float,
    ticker: str,
    *,
    calendar: pd.Index,
    open_prices: dict[str, pd.Series],
    close_prices: dict[str, pd.Series],
) -> list[float]:
    if len(calendar) < 2:
        return []
    entry_day = calendar[1] if len(calendar) > 1 else calendar[0]
    entry_price = _execution_price(open_prices, close_prices, ticker, entry_day)
    if entry_price is None or entry_price <= 0:
        closes = [float(value) for value in close_prices[ticker].loc[calendar].dropna().tolist()]
        return build_benchmark_curve(starting_cash, closes)
    curve: list[float] = []
    for day in calendar:
        market_price = _close_price(close_prices, ticker, day)
        if market_price is None:
            curve.append(curve[-1] if curve else round(starting_cash, 2))
            continue
        if day < entry_day:
            curve.append(round(starting_cash, 2))
        else:
            curve.append(round(starting_cash * (market_price / entry_price), 2))
    return curve


def _rebalance_close_timestamp(day: pd.Timestamp) -> str:
    return f"{day.date().isoformat()}T16:00:00+00:00"


def _execution_price(
    open_prices: dict[str, pd.Series],
    close_prices: dict[str, pd.Series],
    ticker: str,
    day: pd.Timestamp,
) -> float | None:
    open_series = open_prices.get(ticker)
    if open_series is not None and day in open_series.index and pd.notna(open_series.loc[day]):
        return float(open_series.loc[day])
    return _close_price(close_prices, ticker, day)


def _close_price(close_prices: dict[str, pd.Series], ticker: str, day: pd.Timestamp) -> float | None:
    series = close_prices.get(ticker)
    if series is None:
        return None
    if day in series.index and pd.notna(series.loc[day]):
        return float(series.loc[day])
    history = series.loc[:day].dropna()
    if history.empty:
        return None
    return float(history.iloc[-1])


async def _load_sector_lookup(holdings_over_time: list[HoldingsSnapshot]) -> dict[str, str]:
    from backend.data.adapters import YFinanceAdapter

    tickers = sorted(
        {
            holding["ticker"]
            for snapshot in holdings_over_time
            for holding in snapshot.holdings
        }
    )
    if not tickers:
        return {}
    adapter = YFinanceAdapter()
    profiles = await asyncio.gather(*[adapter.get_security_profile(ticker) for ticker in tickers])
    return {
        ticker: str(profile.get("sector") or "unknown")
        for ticker, profile in zip(tickers, profiles, strict=True)
    }


async def _load_sector_lookup_for_tickers(
    tickers: list[str],
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    from backend.data.adapters import YFinanceAdapter

    existing = existing or {}
    missing = [ticker for ticker in sorted(set(tickers)) if ticker not in existing]
    if not missing:
        return dict(existing)
    adapter = YFinanceAdapter()
    profiles = await asyncio.gather(*[adapter.get_security_profile(ticker) for ticker in missing])
    resolved = dict(existing)
    resolved.update(
        {
            ticker: str(profile.get("sector") or "unknown")
            for ticker, profile in zip(missing, profiles, strict=True)
        }
    )
    return resolved


def _max_sector_concentration(holdings_over_time: list[HoldingsSnapshot], sectors: dict[str, str]) -> float:
    max_concentration = 0.0
    for snapshot in holdings_over_time:
        totals: dict[str, float] = {}
        for holding in snapshot.holdings:
            sector = sectors.get(holding["ticker"], "unknown")
            totals[sector] = totals.get(sector, 0.0) + float(holding["weight_pct"])
        if totals:
            max_concentration = max(max_concentration, max(totals.values()))
    return max_concentration


def _clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, round(value, 6)))


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
