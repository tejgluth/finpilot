from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.backtester.cache import build_pipeline_cache_key
from backend.backtester.capabilities import build_equivalence_warnings, build_historical_gap_report
from backend.backtester.engine import (
    BacktestEngine,
    BacktestRequest,
    CandidateEvaluation,
    _build_price_download_warnings,
    _target_weights_from_decisions,
)
from backend.backtester.universe import (
    HistoricalUniverseResolver,
    UniverseDateResolution,
    UniverseTimelineResolution,
    _normalize_ticker,
)
from backend.config import settings
from backend.database import init_db
from backend.llm.strategy_builder import build_execution_snapshot, default_compiled_team
from backend.models.agent_team import DataBoundary
from backend.models.backtest_result import DecisionEvent
from backend.models.signal import AgentSignal, PortfolioDecision
from backend.settings import build_default_user_settings


def _supported_team(team_id: str = "team-supported", version_number: int = 1):
    team = default_compiled_team().model_copy(deep=True)
    team.team_id = team_id
    team.version_number = version_number
    team.name = f"Supported {version_number}"
    team.enabled_agents = ["technicals", "momentum", "macro", "risk_manager", "portfolio_manager"]
    team.agent_weights = {"technicals": 60, "momentum": 40, "macro": 25}
    team.compiled_agent_specs = {
        key: value
        for key, value in team.compiled_agent_specs.items()
        if key in {"technicals", "momentum", "macro"}
    }
    return team


def _sentiment_team():
    team = _supported_team("team-sentiment", 1)
    team.name = "Sentiment Enabled"
    team.enabled_agents = [
        "technicals",
        "momentum",
        "macro",
        "sentiment",
        "risk_manager",
        "portfolio_manager",
    ]
    team.agent_weights["sentiment"] = 30
    team.compiled_agent_specs["sentiment"] = default_compiled_team().compiled_agent_specs["sentiment"]
    return team


def _snapshot(team, user_settings, *, mode: str = "backtest_experimental"):
    return build_execution_snapshot(
        mode=mode,
        ticker_or_universe="AAPL",
        user_settings=user_settings,
        compiled_team=team,
        data_boundary=DataBoundary(
            mode=mode,  # type: ignore[arg-type]
            as_of_datetime="2024-03-29T16:00:00+00:00",
            allow_latest_semantics=mode == "backtest_experimental",
        ),
        cost_model={"slippage_pct": 0.1, "commission_pct": 0.0},
        notes=["test snapshot"],
    )


def _synthetic_market_frame(start_price: float) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", "2024-03-31", freq="B")
    closes = [start_price + (idx * 0.35) for idx in range(len(index))]
    opens = [value - 0.1 for value in closes]
    return pd.DataFrame(
        {
            "Open": opens,
            "High": [value + 0.2 for value in closes],
            "Low": [value - 0.2 for value in closes],
            "Close": closes,
            "Volume": [1_000_000 + (idx * 1000) for idx in range(len(index))],
        },
        index=index,
    )


@pytest.mark.asyncio
async def test_run_backtest_returns_team_runs_and_decision_events(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    monkeypatch.setattr(settings, "db_path", tmp_path / "finpilot.db")
    await init_db()

    async def fake_store_backtest(*_args, **_kwargs):
        return None

    async def fake_download(symbols, *, start_date, end_date):  # noqa: ARG001
        return {symbol: _synthetic_market_frame(100.0 + (idx * 10.0)) for idx, symbol in enumerate(symbols)}

    async def fake_resolve(self, *, universe_id, custom_universe_csv, strict_mode, rebalance_dates, single_ticker=None):  # noqa: ARG001
        dates = [
            UniverseDateResolution(
                as_of_date=item.isoformat(),
                tickers=["AAPL"],
                source="test_universe",
                snapshot_hash="hash-aapl",
            )
            for item in rebalance_dates
        ]
        return UniverseTimelineResolution(
            requested_universe_id="single_ticker",
            universe_id="single_ticker",
            source="test_universe",
            dates=dates,
        )

    async def fake_pipeline(ticker, runtime_settings, execution_snapshot, budget=None):  # noqa: ARG001
        signal = AgentSignal(
            ticker=ticker,
            agent_name="technicals",
            action="BUY",
            raw_confidence=0.82,
            final_confidence=0.82,
            reasoning="Trend and momentum both stayed positive inside the replay window.",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        )
        decision = PortfolioDecision(
            ticker=ticker,
            action="BUY",
            confidence=0.78,
            reasoning="Backtest replay accepted the grounded buy signal.",
            cited_agents=["technicals"],
            bull_points_used=["Technicals remained constructive."],
            bear_points_addressed=["No major bearish counterweight."],
            risk_notes="Risk checks passed.",
            proposed_position_pct=5.0,
        )
        return [signal], None, None, decision

    async def fake_sector_lookup(_snapshots):
        return {"AAPL": "information_technology"}

    monkeypatch.setattr("backend.backtester.engine.store_backtest", fake_store_backtest)
    monkeypatch.setattr("backend.backtester.engine._download_market_data", fake_download)
    monkeypatch.setattr("backend.backtester.engine.HistoricalUniverseResolver.resolve_for_dates", fake_resolve)
    monkeypatch.setattr("backend.backtester.engine.run_agent_pipeline", fake_pipeline)
    monkeypatch.setattr("backend.backtester.engine._load_sector_lookup", fake_sector_lookup)

    user_settings = build_default_user_settings()
    user_settings.llm.provider = "ollama"
    user_settings.backtest.max_parallel_historical_evaluations = 1

    team = _supported_team()
    snapshot = _snapshot(team, user_settings)
    result = await BacktestEngine().run(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            fidelity_mode="full_loop",
            cache_policy="fresh",
            backtest_mode="backtest_experimental",
        ),
        user_settings,
        execution_snapshots=[snapshot],
    )

    assert result.team_runs
    assert result.decision_events
    assert result.team_runs[0].effective_signature is not None
    assert result.team_runs[0].cache_usage.writes >= 1
    assert result.universe_resolution_report.source == "test_universe"
    assert result.decision_events[0].decision.action == "BUY"
    assert Path(result.artifact.artifact_path).exists()


@pytest.mark.asyncio
async def test_experimental_replay_executes_degraded_agents_with_penalties(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    monkeypatch.setattr(settings, "db_path", tmp_path / "finpilot-honored-only.db")
    await init_db()

    async def fake_store_backtest(*_args, **_kwargs):
        return None

    async def fake_download(symbols, *, start_date, end_date):  # noqa: ARG001
        return {symbol: _synthetic_market_frame(95.0 + (idx * 5.0)) for idx, symbol in enumerate(symbols)}

    async def fake_resolve(self, *, universe_id, custom_universe_csv, strict_mode, rebalance_dates, single_ticker=None):  # noqa: ARG001
        dates = [
            UniverseDateResolution(
                as_of_date=item.isoformat(),
                tickers=["AAPL"],
                source="honored_only_universe",
                snapshot_hash="hash-aapl",
            )
            for item in rebalance_dates
        ]
        return UniverseTimelineResolution(
            requested_universe_id="single_ticker",
            universe_id="single_ticker",
            source="honored_only_universe",
            dates=dates,
        )

    async def fake_pipeline(ticker, runtime_settings, execution_snapshot, budget=None):  # noqa: ARG001
        assert execution_snapshot.effective_team.enabled_agents == [
            "technicals",
            "momentum",
            "macro",
            "sentiment",
            "risk_manager",
            "portfolio_manager",
        ]
        assert "sentiment" in execution_snapshot.effective_team.compiled_agent_specs
        signal = AgentSignal(
            ticker=ticker,
            agent_name="technicals",
            action="BUY",
            raw_confidence=0.82,
            final_confidence=0.82,
            reasoning="Historically supported replay stayed constructive.",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        )
        decision = PortfolioDecision(
            ticker=ticker,
            action="BUY",
            confidence=0.78,
            reasoning="Only honored agents participated in the replay.",
            cited_agents=["technicals"],
            bull_points_used=[],
            bear_points_addressed=[],
            risk_notes="Risk checks passed.",
            proposed_position_pct=5.0,
        )
        return [signal], None, None, decision

    async def fake_sector_lookup(_snapshots):
        return {"AAPL": "information_technology"}

    monkeypatch.setattr("backend.backtester.engine.store_backtest", fake_store_backtest)
    monkeypatch.setattr("backend.backtester.engine._download_market_data", fake_download)
    monkeypatch.setattr("backend.backtester.engine.HistoricalUniverseResolver.resolve_for_dates", fake_resolve)
    monkeypatch.setattr("backend.backtester.engine.run_agent_pipeline", fake_pipeline)
    monkeypatch.setattr("backend.backtester.engine._load_sector_lookup", fake_sector_lookup)

    user_settings = build_default_user_settings()
    user_settings.llm.provider = "ollama"
    user_settings.backtest.max_parallel_historical_evaluations = 1

    team = _sentiment_team()
    snapshot = _snapshot(team, user_settings, mode="backtest_experimental")
    result = await BacktestEngine().run(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            fidelity_mode="full_loop",
            cache_policy="fresh",
            backtest_mode="backtest_experimental",
        ),
        user_settings,
        execution_snapshots=[snapshot],
    )

    assert result.team_runs[0].supported_agents == ["technicals", "momentum", "macro", "sentiment"]
    assert {item.agent_name for item in result.team_runs[0].degraded_agents} == {"sentiment"}
    assert result.team_runs[0].effective_signature is not None
    assert result.team_runs[0].effective_signature.effective_weights["sentiment"] == 17.5


@pytest.mark.asyncio
async def test_strict_mode_rejects_unsupported_agents():
    user_settings = build_default_user_settings()
    team = _sentiment_team()
    snapshot = _snapshot(team, user_settings, mode="backtest_strict")

    with pytest.raises(ValueError, match="sentiment"):
        await BacktestEngine().run(
            BacktestRequest(
                ticker="AAPL",
                start_date="2024-01-01",
                end_date="2024-03-31",
                backtest_mode="backtest_strict",
            ),
            user_settings,
            execution_snapshots=[snapshot],
        )


def test_historical_equivalence_warning_flags_degraded_only_difference():
    team_a = _supported_team("team-a", 1)
    team_b = _supported_team("team-b", 1)
    team_b.enabled_agents = [
        "technicals",
        "momentum",
        "macro",
        "sentiment",
        "risk_manager",
        "portfolio_manager",
    ]
    team_b.agent_weights["sentiment"] = 35
    team_b.compiled_agent_specs["sentiment"] = default_compiled_team().compiled_agent_specs["sentiment"]

    report, profiles = build_historical_gap_report(
        [team_a, team_b],
        strict_temporal_mode=False,
    )
    warnings = build_equivalence_warnings(list(profiles.values()))

    assert report.warnings
    assert not warnings


@pytest.mark.asyncio
async def test_reuse_cache_avoids_recomputing_candidate_pipeline(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    monkeypatch.setattr(settings, "db_path", tmp_path / "finpilot-cache.db")
    await init_db()

    call_count = {"count": 0}

    async def fake_store_backtest(*_args, **_kwargs):
        return None

    async def fake_download(symbols, *, start_date, end_date):  # noqa: ARG001
        return {symbol: _synthetic_market_frame(90.0 + (idx * 7.0)) for idx, symbol in enumerate(symbols)}

    async def fake_resolve(self, *, universe_id, custom_universe_csv, strict_mode, rebalance_dates, single_ticker=None):  # noqa: ARG001
        dates = [
            UniverseDateResolution(
                as_of_date=item.isoformat(),
                tickers=["AAPL"],
                source="cache_test_universe",
                snapshot_hash="hash-aapl",
            )
            for item in rebalance_dates
        ]
        return UniverseTimelineResolution(
            requested_universe_id="single_ticker",
            universe_id="single_ticker",
            source="cache_test_universe",
            dates=dates,
        )

    async def fake_pipeline(ticker, runtime_settings, execution_snapshot, budget=None):  # noqa: ARG001
        call_count["count"] += 1
        signal = AgentSignal(
            ticker=ticker,
            agent_name="technicals",
            action="BUY",
            raw_confidence=0.8,
            final_confidence=0.8,
            reasoning="Cached replay signal.",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        )
        decision = PortfolioDecision(
            ticker=ticker,
            action="BUY",
            confidence=0.75,
            reasoning="Cached replay decision.",
            cited_agents=["technicals"],
            bull_points_used=[],
            bear_points_addressed=[],
            risk_notes="Risk checks passed.",
            proposed_position_pct=5.0,
        )
        return [signal], None, None, decision

    async def fake_sector_lookup(_snapshots):
        return {"AAPL": "information_technology"}

    monkeypatch.setattr("backend.backtester.engine.store_backtest", fake_store_backtest)
    monkeypatch.setattr("backend.backtester.engine._download_market_data", fake_download)
    monkeypatch.setattr("backend.backtester.engine.HistoricalUniverseResolver.resolve_for_dates", fake_resolve)
    monkeypatch.setattr("backend.backtester.engine.run_agent_pipeline", fake_pipeline)
    monkeypatch.setattr("backend.backtester.engine._load_sector_lookup", fake_sector_lookup)

    user_settings = build_default_user_settings()
    team = _supported_team("cache-team", 1)
    snapshot = _snapshot(team, user_settings)
    request = BacktestRequest(
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-31",
        fidelity_mode="full_loop",
        cache_policy="reuse",
        backtest_mode="backtest_experimental",
    )

    await BacktestEngine().run(request, user_settings, execution_snapshots=[snapshot])
    await BacktestEngine().run(request, user_settings, execution_snapshots=[snapshot])

    assert call_count["count"] == 1

    cache_key = build_pipeline_cache_key(
        execution_snapshot=build_execution_snapshot(
            mode="backtest_experimental",
            ticker_or_universe="AAPL",
            user_settings=user_settings,
            compiled_team=team,
            data_boundary=DataBoundary(
                mode="backtest_experimental",
                as_of_datetime="2024-01-31T16:00:00+00:00",
                allow_latest_semantics=True,
            ),
            cost_model={"slippage_pct": 0.1, "commission_pct": 0.0},
            notes=[],
        ),
        ticker="AAPL",
        as_of_datetime="2024-01-31T16:00:00+00:00",
        fidelity_mode="full_loop",
        backtest_mode="backtest_experimental",
    )
    assert cache_key


@pytest.mark.asyncio
async def test_experimental_universe_falls_back_to_current_members(monkeypatch):
    async def fail_monthly(as_of_date):  # noqa: ARG001
        raise ValueError("monthly unavailable")

    async def fail_daily(as_of_date):  # noqa: ARG001
        raise ValueError("daily unavailable")

    monkeypatch.setattr("backend.backtester.universe._load_monthly_snapshot", fail_monthly)
    monkeypatch.setattr("backend.backtester.universe._load_daily_historical_snapshot", fail_daily)
    monkeypatch.setattr(
        "backend.backtester.universe._load_current_sp500",
        lambda: ["AAPL", "MSFT", "NVDA"],
    )

    timeline = await HistoricalUniverseResolver().resolve_for_dates(
        universe_id="current_sp500",
        custom_universe_csv=None,
        strict_mode=False,
        rebalance_dates=[pd.Timestamp("2022-12-30").date()],
    )

    assert timeline.dates[0].source == "fallback_current_sp500"
    assert "survivorship-biased" in " ".join(timeline.dates[0].warnings)


@pytest.mark.asyncio
async def test_backtest_degrades_failed_candidate_pipeline_to_hold(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    monkeypatch.setattr(settings, "db_path", tmp_path / "finpilot-failed-candidate.db")
    await init_db()

    async def fake_store_backtest(*_args, **_kwargs):
        return None

    async def fake_download(symbols, *, start_date, end_date):  # noqa: ARG001
        return {symbol: _synthetic_market_frame(110.0 + (idx * 3.0)) for idx, symbol in enumerate(symbols)}

    async def fake_resolve(self, *, universe_id, custom_universe_csv, strict_mode, rebalance_dates, single_ticker=None):  # noqa: ARG001
        dates = [
            UniverseDateResolution(
                as_of_date=item.isoformat(),
                tickers=["AAPL"],
                source="failure_test_universe",
                snapshot_hash="hash-aapl",
            )
            for item in rebalance_dates
        ]
        return UniverseTimelineResolution(
            requested_universe_id="single_ticker",
            universe_id="single_ticker",
            source="failure_test_universe",
            dates=dates,
        )

    async def exploding_pipeline(ticker, runtime_settings, execution_snapshot, budget=None):  # noqa: ARG001
        raise IndexError("single positional indexer is out-of-bounds")

    async def fake_sector_lookup(_snapshots):
        return {}

    monkeypatch.setattr("backend.backtester.engine.store_backtest", fake_store_backtest)
    monkeypatch.setattr("backend.backtester.engine._download_market_data", fake_download)
    monkeypatch.setattr("backend.backtester.engine.HistoricalUniverseResolver.resolve_for_dates", fake_resolve)
    monkeypatch.setattr("backend.backtester.engine.run_agent_pipeline", exploding_pipeline)
    monkeypatch.setattr("backend.backtester.engine._load_sector_lookup", fake_sector_lookup)

    user_settings = build_default_user_settings()
    team = _supported_team("failure-team", 1)
    snapshot = _snapshot(team, user_settings)
    result = await BacktestEngine().run(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            fidelity_mode="full_loop",
            cache_policy="fresh",
            backtest_mode="backtest_experimental",
        ),
        user_settings,
        execution_snapshots=[snapshot],
    )

    assert result.decision_events
    assert result.decision_events[0].decision.action == "HOLD"
    assert "out-of-bounds" in " ".join(result.decision_events[0].warnings)


def test_target_weights_redistribute_leftover_under_caps():
    def make_event(ticker: str, confidence: float, score: float, proposed_pct: float) -> CandidateEvaluation:
        return CandidateEvaluation(
            event=DecisionEvent(
                rebalance_date="2024-01-31",
                execution_date="2024-02-01",
                team_id="team",
                team_name="Team",
                version_number=1,
                ticker=ticker,
                selected_for_execution=True,
                score=score,
                decision=PortfolioDecision(
                    ticker=ticker,
                    action="BUY",
                    confidence=confidence,
                    reasoning="test",
                    cited_agents=["technicals"],
                    bull_points_used=[],
                    bear_points_addressed=[],
                    risk_notes="Risk checks passed.",
                    proposed_position_pct=proposed_pct,
                ),
            ),
            price_open=None,
            price_close=None,
        )

    weights = _target_weights_from_decisions(
        evaluations=[
            make_event("A", confidence=1.0, score=0.9, proposed_pct=20.0),
            make_event("B", confidence=1.0, score=0.02, proposed_pct=20.0),
            make_event("C", confidence=1.0, score=0.02, proposed_pct=20.0),
            make_event("D", confidence=1.0, score=0.02, proposed_pct=20.0),
            make_event("E", confidence=1.0, score=0.02, proposed_pct=10.0),
            make_event("F", confidence=1.0, score=0.02, proposed_pct=10.0),
        ],
        weighting_method="confidence_weighted",
        max_positions=6,
    )

    assert round(sum(weights.values()), 4) == 1.0
    assert weights["A"] == 0.2
    assert weights["B"] == 0.2
    assert weights["C"] == 0.2
    assert weights["D"] == 0.2
    assert weights["E"] == 0.1
    assert weights["F"] == 0.1


def test_normalize_ticker_drops_non_common_symbols_and_applies_aliases():
    assert _normalize_ticker("BRK.B") == "BRK-B"
    assert _normalize_ticker("2483490D") == ""
    assert _normalize_ticker("AMTM-W") == ""


def test_price_download_warning_surfaces_missing_universe_symbols():
    warnings = _build_price_download_warnings(
        requested_symbols=["AAPL", "ATVI", "MMC", "SPY", "TLT", "^VIX"],
        available_symbols=["AAPL", "SPY", "TLT", "^VIX"],
        benchmark_symbol="SPY",
    )

    assert warnings
    assert "ATVI" in warnings[0]
    assert "MMC" in warnings[0]
    assert "excluded from the backtest shortlist/simulation" in warnings[0]


@pytest.mark.asyncio
async def test_full_loop_rejects_impossible_token_workload(monkeypatch):
    async def fake_download(symbols, *, start_date, end_date):  # noqa: ARG001
        return {symbol: _synthetic_market_frame(100.0 + (idx * 2.0)) for idx, symbol in enumerate(symbols)}

    async def fake_resolve(self, *, universe_id, custom_universe_csv, strict_mode, rebalance_dates, single_ticker=None):  # noqa: ARG001
        tickers = [f"TICK{index}" for index in range(10)]
        dates = [
            UniverseDateResolution(
                as_of_date=item.isoformat(),
                tickers=tickers,
                source="workload_universe",
                snapshot_hash=f"hash-{item.isoformat()}",
            )
            for item in rebalance_dates
        ]
        return UniverseTimelineResolution(
            requested_universe_id="current_sp500",
            universe_id="current_sp500",
            source="workload_universe",
            dates=dates,
        )

    monkeypatch.setattr("backend.backtester.engine._download_market_data", fake_download)
    monkeypatch.setattr("backend.backtester.engine.HistoricalUniverseResolver.resolve_for_dates", fake_resolve)

    user_settings = build_default_user_settings()
    user_settings.backtest.max_tokens_per_backtest = 2_000

    team = _supported_team("workload-team", 1)
    snapshot = _snapshot(team, user_settings)

    with pytest.raises(ValueError, match="Use hybrid_shortlist"):
        await BacktestEngine().run(
            BacktestRequest(
                universe_id="current_sp500",
                start_date="2024-01-01",
                end_date="2024-03-31",
                fidelity_mode="full_loop",
                cache_policy="fresh",
                backtest_mode="backtest_experimental",
            ),
            user_settings,
            execution_snapshots=[snapshot],
        )
