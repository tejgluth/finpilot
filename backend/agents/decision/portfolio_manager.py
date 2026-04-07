from __future__ import annotations

from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision


def aggregate_signal_conviction(
    signals: list[AgentSignal],
    agent_weights: dict[str, int],
    bull_case: DebateOutput | None = None,
    bear_case: DebateOutput | None = None,
    *,
    max_data_age_minutes: float = 60.0,
) -> dict[str, float]:
    def resolve_weight(signal: AgentSignal) -> float:
        return float(
            weights.get(
                signal.agent_name,
                weights.get(signal.agent_name.lower(), weights.get(signal.source_agent_name or "", 50)),
            )
        )

    weights = agent_weights or {}
    total_weight = 0.0
    signed_strength = 0.0
    absolute_strength = 0.0
    coverage_total = 0.0
    freshness_total = 0.0

    for signal in signals:
        weight = resolve_weight(signal)
        direction = 1.0 if signal.action == "BUY" else -1.0 if signal.action == "SELL" else 0.0
        strength = signal.final_confidence * weight
        total_weight += weight
        signed_strength += direction * strength
        absolute_strength += abs(direction) * strength
        coverage_total += signal.data_coverage_pct * weight
        if signal.oldest_data_age_minutes <= 0:
            freshness_total += weight
        else:
            freshness_total += (
                min(1.0, max_data_age_minutes / max(signal.oldest_data_age_minutes, 1.0)) * weight
            )

    if total_weight <= 0:
        return {
            "direction_score": 0.0,
            "conviction_score": 0.0,
            "priority_score": 0.0,
            "agreement_score": 0.0,
            "coverage_score": 0.0,
        }

    direction_score = signed_strength / total_weight
    agreement_score = abs(signed_strength) / absolute_strength if absolute_strength > 0 else 0.0
    coverage_score = coverage_total / total_weight
    freshness_score = freshness_total / total_weight

    aligned_debate_bias = 0.0
    if bull_case and bear_case:
        if direction_score >= 0:
            aligned_debate_bias = bull_case.confidence - bear_case.confidence
        else:
            aligned_debate_bias = bear_case.confidence - bull_case.confidence
    debate_multiplier = _clamp(1.0 + (aligned_debate_bias * 0.1), 0.85, 1.1)

    conviction_score = _clamp(
        abs(direction_score) * (0.55 + (0.45 * agreement_score)),
        0.0,
        1.0,
    )
    priority_score = _clamp(
        conviction_score * ((coverage_score + freshness_score) / 2.0) * debate_multiplier,
        0.0,
        1.0,
    )
    return {
        "direction_score": round(direction_score, 4),
        "conviction_score": round(conviction_score, 4),
        "priority_score": round(priority_score, 4),
        "agreement_score": round(agreement_score, 4),
        "coverage_score": round(coverage_score, 4),
    }


def decide_portfolio_action(
    ticker: str,
    signals: list[AgentSignal],
    bull_case: DebateOutput | None,
    bear_case: DebateOutput | None,
    proposed_position_pct: float,
    agent_weights: dict[str, int],
    risk_notes: str,
    *,
    max_data_age_minutes: float = 60.0,
) -> PortfolioDecision:
    scorecard = aggregate_signal_conviction(
        signals,
        agent_weights,
        bull_case,
        bear_case,
        max_data_age_minutes=max_data_age_minutes,
    )
    direction_score = scorecard["direction_score"]
    priority_score = scorecard["priority_score"]
    conviction_score = scorecard["conviction_score"]
    if direction_score > 0.08 and priority_score > 0.10 and proposed_position_pct > 0:
        action = "BUY"
    elif direction_score < -0.08 and priority_score > 0.10:
        action = "SELL"
    else:
        action = "HOLD"
    bull_points = bull_case.key_points if bull_case else []
    bear_points = bear_case.key_points if bear_case else []
    cited_agents = [signal.agent_name for signal in signals]
    return PortfolioDecision(
        ticker=ticker.upper(),
        action=action,
        confidence=round(_clamp((priority_score * 0.7) + (conviction_score * 0.3), 0.0, 1.0), 4),
        direction_score=direction_score,
        conviction_score=conviction_score,
        priority_score=priority_score,
        agreement_score=scorecard["agreement_score"],
        coverage_score=scorecard["coverage_score"],
        reasoning=(
            "The portfolio manager aggregated grounded agent signals into a direction and "
            "priority score, then left cross-ticker sizing to the deterministic portfolio constructor."
        ),
        cited_agents=cited_agents,
        bull_points_used=bull_points[:3],
        bear_points_addressed=bear_points[:3],
        risk_notes=risk_notes,
        proposed_position_pct=proposed_position_pct if action == "BUY" else 0.0,
    )


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
