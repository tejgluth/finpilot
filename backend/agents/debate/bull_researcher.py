from __future__ import annotations

from backend.models.signal import AgentSignal, DebateOutput


def build_bull_case(signals: list[AgentSignal]) -> DebateOutput:
    positives = [signal for signal in signals if signal.action == "BUY"]
    if not positives:
        return DebateOutput(
            position="BULL",
            thesis="The bullish case is limited because few agents produced strong positive signals.",
            key_points=["Positive evidence is sparse or low confidence."],
            cited_agents=[signal.agent_name for signal in signals],
            confidence=0.35,
        )
    ordered = sorted(positives, key=lambda signal: signal.final_confidence, reverse=True)
    points = [
        f"{signal.agent_name} supports BUY with final_confidence {signal.final_confidence:.2f}."
        for signal in ordered[:5]
    ]
    return DebateOutput(
        position="BULL",
        thesis="The strongest bullish case comes from the highest-confidence positive agents.",
        key_points=points,
        cited_agents=[signal.agent_name for signal in ordered[:5]],
        confidence=round(sum(signal.final_confidence for signal in ordered[:5]) / len(ordered[:5]), 4),
    )
