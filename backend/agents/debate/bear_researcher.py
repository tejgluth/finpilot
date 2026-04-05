from __future__ import annotations

from backend.models.signal import AgentSignal, DebateOutput


def build_bear_case(signals: list[AgentSignal]) -> DebateOutput:
    negatives = [signal for signal in signals if signal.action == "SELL" or signal.warning]
    if not negatives:
        return DebateOutput(
            position="BEAR",
            thesis="The bearish case is limited because few agents surfaced direct downside warnings.",
            key_points=["Downside evidence is light or based on missing data warnings."],
            cited_agents=[signal.agent_name for signal in signals],
            confidence=0.35,
        )
    ordered = sorted(negatives, key=lambda signal: signal.final_confidence, reverse=True)
    points = [
        f"{signal.agent_name} flags risk with action {signal.action} and warning '{signal.warning or 'none'}'."
        for signal in ordered[:5]
    ]
    return DebateOutput(
        position="BEAR",
        thesis="The bearish case focuses on the most confident negative or low-quality signals.",
        key_points=points,
        cited_agents=[signal.agent_name for signal in ordered[:5]],
        confidence=round(sum(signal.final_confidence for signal in ordered[:5]) / len(ordered[:5]), 4),
    )
