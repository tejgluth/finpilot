from backend.agents.decision.risk_manager import evaluate_risk
from backend.models.signal import AgentSignal
from backend.guardrails.position_limits import check_position_limits
from backend.settings.user_settings import AgentSettings, GuardrailConfig


def test_position_limits_block_when_daily_loss_breaches_limit():
    result = check_position_limits(
        proposed_position_pct=12,
        open_positions=1,
        sector_exposure_pct=10,
        daily_loss_pct=5,
        total_drawdown_pct=2,
        guardrails=GuardrailConfig(max_position_pct=10, max_daily_loss_pct=3),
    )
    assert result.allowed is False
    assert any("Daily loss" in reason for reason in result.reasons)


def test_risk_manager_ignores_neutral_signals_when_sizing():
    signals = [
        AgentSignal(
            ticker="AAPL",
            agent_name="technicals",
            action="BUY",
            raw_confidence=0.74,
            final_confidence=0.74,
            reasoning="test",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        ),
        AgentSignal(
            ticker="AAPL",
            agent_name="momentum",
            action="BUY",
            raw_confidence=0.71,
            final_confidence=0.71,
            reasoning="test",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        ),
        AgentSignal(
            ticker="AAPL",
            agent_name="macro",
            action="HOLD",
            raw_confidence=0.20,
            final_confidence=0.20,
            reasoning="test",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=0.0,
            warning="",
        ),
    ]

    result = evaluate_risk(
        signals=signals,
        guardrails=GuardrailConfig(max_position_pct=5.0),
        agent_settings=AgentSettings(min_confidence_threshold=0.5),
    )

    assert result.allowed is True
    assert result.proposed_position_pct == 5.0
