from __future__ import annotations

from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision


def decide_portfolio_action(
    ticker: str,
    signals: list[AgentSignal],
    bull_case: DebateOutput | None,
    bear_case: DebateOutput | None,
    proposed_position_pct: float,
    agent_weights: dict[str, int],
    risk_notes: str,
) -> PortfolioDecision:
    weights = agent_weights or {}
    score = 0.0
    cited_agents: list[str] = []
    for signal in signals:
        direction = 1 if signal.action == "BUY" else -1 if signal.action == "SELL" else 0
        score += direction * signal.final_confidence * weights.get(signal.agent_name, 50)
        cited_agents.append(signal.agent_name)
    normalized = score / max(1.0, sum(weights.get(signal.agent_name, 50) for signal in signals))
    if normalized > 0.12 and proposed_position_pct > 0:
        action = "BUY"
    elif normalized < -0.12:
        action = "SELL"
    else:
        action = "HOLD"
    confidence = min(1.0, max(0.0, abs(normalized) + 0.45))
    bull_points = bull_case.key_points if bull_case else []
    bear_points = bear_case.key_points if bear_case else []
    return PortfolioDecision(
        ticker=ticker.upper(),
        action=action,
        confidence=round(confidence, 4),
        reasoning="Compiled team weights, debate review, and deterministic risk sizing were applied to the grounded signals.",
        cited_agents=cited_agents,
        bull_points_used=bull_points[:3],
        bear_points_addressed=bear_points[:3],
        risk_notes=risk_notes,
        proposed_position_pct=proposed_position_pct if action == "BUY" else 0.0,
    )
