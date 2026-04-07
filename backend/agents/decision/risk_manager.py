from __future__ import annotations

from dataclasses import dataclass

from backend.models.signal import AgentSignal
from backend.settings.user_settings import AgentSettings, GuardrailConfig


@dataclass
class RiskCheckResult:
    allowed: bool
    proposed_position_pct: float
    position_cap_pct: float
    risk_multiplier: float
    notes: str


def evaluate_risk(
    signals: list[AgentSignal],
    guardrails: GuardrailConfig,
    agent_settings: AgentSettings,
) -> RiskCheckResult:
    if not signals:
        return RiskCheckResult(False, 0.0, guardrails.max_position_pct, 0.0, "No agent signals available.")

    directional_signals = [signal for signal in signals if signal.action in {"BUY", "SELL"}]
    if not directional_signals:
        return RiskCheckResult(
            False,
            0.0,
            guardrails.max_position_pct,
            0.0,
            "No actionable agent signals available.",
        )

    avg_confidence = sum(signal.final_confidence for signal in directional_signals) / len(directional_signals)
    if avg_confidence < agent_settings.min_confidence_threshold:
        return RiskCheckResult(
            False,
            0.0,
            guardrails.max_position_pct,
            avg_confidence,
            "Aggregate confidence below the configured minimum threshold.",
        )

    bullish_strength = sum(signal.final_confidence for signal in directional_signals if signal.action == "BUY")
    bearish_strength = sum(signal.final_confidence for signal in directional_signals if signal.action == "SELL")
    total_directional_strength = bullish_strength + bearish_strength
    if total_directional_strength <= 0:
        return RiskCheckResult(
            False,
            0.0,
            guardrails.max_position_pct,
            0.0,
            "Directional conviction was too weak to size a position.",
        )

    strength = max(0.0, bullish_strength - bearish_strength) / total_directional_strength
    proposed_pct = round(min(guardrails.max_position_pct, max(0.0, strength * guardrails.max_position_pct)), 2)
    return RiskCheckResult(True, proposed_pct, guardrails.max_position_pct, strength, "Risk checks passed.")
