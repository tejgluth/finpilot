from __future__ import annotations

from backend.backtester.engine import BacktestRequest
from backend.backtester.portfolio_construction import (
    build_portfolio_construction_config,
    construct_target_weights,
)
from backend.llm.strategy_builder import default_compiled_team
from backend.models.backtest_result import DecisionEvent
from backend.models.signal import PortfolioDecision
from backend.settings import build_default_user_settings


def _event(
    ticker: str,
    *,
    priority: float,
    direction: float = 0.4,
    confidence: float = 0.7,
) -> DecisionEvent:
    return DecisionEvent(
        rebalance_date="2024-03-29",
        execution_date="2024-04-01",
        team_id="team-test",
        team_name="Test Team",
        version_number=1,
        ticker=ticker,
        shortlist_rank=1,
        shortlisted=True,
        selected_for_execution=False,
        cache_status="miss",
        score=priority,
        decision=PortfolioDecision(
            ticker=ticker,
            action="BUY",
            confidence=confidence,
            direction_score=direction,
            conviction_score=priority,
            priority_score=priority,
            agreement_score=0.8,
            coverage_score=1.0,
            reasoning="Grounded decision.",
            cited_agents=["technicals"],
            bull_points_used=[],
            bear_points_addressed=[],
            risk_notes="Risk checks passed.",
            proposed_position_pct=10.0,
        ),
    )


def test_build_portfolio_config_uses_team_profile_defaults():
    user_settings = build_default_user_settings()
    team = default_compiled_team().model_copy(deep=True)
    team.portfolio_construction.max_position_pct = 16.0
    team.portfolio_construction.top_n_target = 7
    team.portfolio_construction.weighting_mode = "risk_budgeted"

    config = build_portfolio_construction_config(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
        ),
        user_settings,
        team,
    )

    assert config.max_position_pct == 16.0
    assert config.top_n_holdings == 7
    assert config.weighting_mode == "risk_budgeted"


def test_construct_target_weights_is_top_heavy_not_equal_weighted():
    user_settings = build_default_user_settings()
    team = default_compiled_team().model_copy(deep=True)
    team.portfolio_construction.max_position_pct = 60.0
    team.portfolio_construction.min_position_pct = 0.0
    team.portfolio_construction.top_n_target = 2
    team.portfolio_construction.weighting_mode = "capped_conviction"
    team.portfolio_construction.score_exponent = 2.0
    config = build_portfolio_construction_config(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            max_position_pct=60.0,
            min_position_pct=0.0,
            top_n_holdings=2,
            weighting_mode="capped_conviction",
            score_exponent=2.0,
            cash_floor_pct=0.0,
            max_turnover_pct=100.0,
            sector_cap_pct=100.0,
        ),
        user_settings,
        team,
    )

    plan = construct_target_weights(
        events=[
            _event("AAA", priority=0.78, confidence=0.86),
            _event("BBB", priority=0.48, confidence=0.73),
            _event("CCC", priority=0.22, confidence=0.61),
        ],
        current_weights_pct={},
        volatility_by_ticker={"AAA": 0.18, "BBB": 0.24, "CCC": 0.31},
        sectors={"AAA": "tech", "BBB": "health", "CCC": "energy"},
        config=config,
    )

    assert plan.selected_tickers == ["AAA", "BBB"]
    assert plan.weights["AAA"] > plan.weights["BBB"]
    assert round(plan.weights["AAA"], 4) != round(plan.weights["BBB"], 4)


def test_construct_target_weights_uses_cash_when_opportunities_are_weak():
    user_settings = build_default_user_settings()
    team = default_compiled_team().model_copy(deep=True)
    config = build_portfolio_construction_config(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            top_n_holdings=2,
            min_conviction_score=0.18,
            cash_floor_pct=5.0,
        ),
        user_settings,
        team,
    )

    plan = construct_target_weights(
        events=[
            _event("AAA", priority=0.20, confidence=0.58),
            _event("BBB", priority=0.19, confidence=0.57),
        ],
        current_weights_pct={},
        volatility_by_ticker={"AAA": 0.25, "BBB": 0.27},
        sectors={"AAA": "tech", "BBB": "health"},
        config=config,
    )

    assert plan.target_cash_pct > 25.0
    assert plan.target_gross_pct < 75.0


def test_construct_target_weights_applies_replacement_buffer_to_incumbents():
    user_settings = build_default_user_settings()
    team = default_compiled_team().model_copy(deep=True)
    config = build_portfolio_construction_config(
        BacktestRequest(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-03-31",
            top_n_holdings=1,
            replacement_threshold=0.05,
            selection_buffer_pct=0.5,
        ),
        user_settings,
        team,
    )

    old_name = _event("OLD", priority=0.30, confidence=0.70)
    new_name = _event("NEW", priority=0.33, confidence=0.72)
    plan = construct_target_weights(
        events=[old_name, new_name],
        current_weights_pct={"OLD": 10.0},
        volatility_by_ticker={"OLD": 0.25, "NEW": 0.25},
        sectors={"OLD": "tech", "NEW": "health"},
        config=config,
    )

    assert "OLD" in plan.selected_tickers
    assert "NEW" not in plan.selected_tickers
    assert "replacement threshold" in new_name.exclusion_reason.lower()
