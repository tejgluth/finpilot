from __future__ import annotations

from dataclasses import dataclass

from backend.agents.registry import AGENT_DATA_DEPS
from backend.models.agent_team import CompiledTeam
from backend.models.backtest_result import (
    HistoricalAgentSupport,
    HistoricalEffectiveSignature,
    HistoricalGap,
    HistoricalGapReport,
)


SUPPORTED_ANALYSIS_AGENTS = {
    "fundamentals",
    "technicals",
    "sentiment",
    "macro",
    "value",
    "momentum",
    "growth",
}

DEGRADATION_FACTORS = {
    "full": 1.0,
    "partial": 0.7,
    "experimental": 0.45,
}

HISTORICAL_SUPPORT = {
    "technicals": {
        "support_level": "full",
        "honored_in_strict": True,
        "degraded_in_experimental": False,
        "reason": "Uses historical OHLCV and deterministic TA computations only.",
    },
    "momentum": {
        "support_level": "full",
        "honored_in_strict": True,
        "degraded_in_experimental": False,
        "reason": "Uses historical price relative-strength calculations only.",
    },
    "macro": {
        "support_level": "full",
        "honored_in_strict": True,
        "degraded_in_experimental": False,
        "reason": "Uses point-in-time FRED series and price-based proxy data.",
    },
    "fundamentals": {
        "support_level": "partial",
        "honored_in_strict": False,
        "degraded_in_experimental": True,
        "reason": "Historical replay can rebuild much of the signal from SEC CompanyFacts and EDGAR, but vendor consensus and snapshot-style fields remain partial.",
    },
    "value": {
        "support_level": "partial",
        "honored_in_strict": False,
        "degraded_in_experimental": True,
        "reason": "Historical replay can rebuild valuation inputs from SEC CompanyFacts and filing text, but forward/vendor-style valuation fields remain partial.",
    },
    "growth": {
        "support_level": "partial",
        "honored_in_strict": False,
        "degraded_in_experimental": True,
        "reason": "Historical replay can reconstruct reported growth from SEC CompanyFacts, but surprise and consensus style fields remain partial.",
    },
    "sentiment": {
        "support_level": "partial",
        "honored_in_strict": False,
        "degraded_in_experimental": True,
        "reason": "Archived headline windows from Finnhub, Marketaux, and GDELT replay well, but social and options-context remain incomplete historically.",
    },
}


@dataclass
class TeamHistoricalProfile:
    signature: HistoricalEffectiveSignature
    support_by_agent: dict[str, HistoricalAgentSupport]
    gaps: list[HistoricalGap]


def build_historical_gap_report(
    compiled_teams: list[CompiledTeam],
    *,
    strict_temporal_mode: bool,
) -> tuple[HistoricalGapReport, dict[str, TeamHistoricalProfile]]:
    gaps: list[HistoricalGap] = []
    warnings: list[str] = []
    blocking_errors: list[str] = []
    profiles: dict[str, TeamHistoricalProfile] = {}

    for team in compiled_teams:
        # Block experimental_custom teams in strict mode
        team_classification = getattr(team, "team_classification", "premade")
        if team_classification == "experimental_custom" and strict_temporal_mode:
            blocking_errors.append(
                f"{team.name}: experimental_custom teams cannot run in backtest_strict mode. "
                "Remove prompt overrides or switch to backtest_experimental."
            )
            continue

        honored_agents: list[str] = []
        degraded_agents: list[HistoricalAgentSupport] = []
        ignored_agents: list[str] = []
        effective_weights: dict[str, float] = {}
        support_by_agent: dict[str, HistoricalAgentSupport] = {}
        team_gaps: list[HistoricalGap] = []

        for agent_name in team.enabled_agents:
            if agent_name not in SUPPORTED_ANALYSIS_AGENTS:
                continue
            raw_weight = float(team.agent_weights.get(agent_name, 0))
            if raw_weight <= 0:
                continue
            profile = HISTORICAL_SUPPORT[agent_name]
            support = HistoricalAgentSupport(
                agent_name=agent_name,
                support_level=profile["support_level"],
                honored_in_strict=profile["honored_in_strict"],
                degraded_in_experimental=profile["degraded_in_experimental"],
                effective_weight=round(raw_weight * DEGRADATION_FACTORS[profile["support_level"]], 2),
                reason=profile["reason"],
                owned_sources=AGENT_DATA_DEPS.get(agent_name, []),
            )
            support_by_agent[agent_name] = support

            if support.support_level == "full":
                honored_agents.append(agent_name)
                effective_weights[agent_name] = raw_weight
                continue

            status = "blocked" if strict_temporal_mode else "degraded"
            gap = HistoricalGap(
                team_id=team.team_id,
                team_name=team.name,
                version_number=team.version_number,
                agent_name=agent_name,
                support_level=support.support_level,
                status=status,
                reason=support.reason,
            )
            gaps.append(gap)
            team_gaps.append(gap)

            if strict_temporal_mode:
                ignored_agents.append(agent_name)
                blocking_errors.append(
                    f"{team.name} v{team.version_number} enables {agent_name}, which is only "
                    f"{support.support_level} for historical replay. Switch to experimental mode or remove that agent."
                )
            else:
                degraded_agents.append(support)
                if support.degraded_in_experimental:
                    effective_weights[agent_name] = support.effective_weight
                warnings.append(
                    f"{team.name} v{team.version_number}: {agent_name} is not point-in-time faithful for historical replay "
                    f"and will run with degraded historical weighting/confidence penalties in experimental mode. {support.reason}"
                )

        if not honored_agents and strict_temporal_mode:
            blocking_errors.append(
                f"{team.name} v{team.version_number} has no fully supported historical analysis agents enabled."
            )

        summary_parts = []
        if honored_agents:
            summary_parts.append(f"Full fidelity: {', '.join(sorted(honored_agents))}.")
        if degraded_agents:
            summary_parts.append(
                ("Executed with historical degradation: " if not strict_temporal_mode else "Historical limitations: ")
                + ", ".join(
                    f"{item.agent_name} ({item.support_level})" for item in degraded_agents
                )
                + "."
            )
        honored_weight_total = sum(float(team.agent_weights.get(agent_name, 0)) for agent_name in honored_agents)
        degraded_weight_total = sum(float(team.agent_weights.get(item.agent_name, 0)) for item in degraded_agents)
        if degraded_agents and degraded_weight_total >= max(honored_weight_total, 1.0):
            warnings.append(
                f"{team.name} v{team.version_number}: most configured weight sits in agent families that are not "
                "fully point-in-time faithful historically, so this replay may differ materially from the live/paper team."
            )
        if ignored_agents:
            summary_parts.append("Ignored in strict mode: " + ", ".join(sorted(ignored_agents)) + ".")
        signature = HistoricalEffectiveSignature(
            team_id=team.team_id,
            team_name=team.name,
            version_number=team.version_number,
            honored_agents=sorted(honored_agents),
            degraded_agents=degraded_agents,
            effective_weights=effective_weights,
            ignored_agents=sorted(ignored_agents),
            summary=" ".join(summary_parts).strip(),
        )
        profiles[_profile_key(team.team_id, team.version_number)] = TeamHistoricalProfile(
            signature=signature,
            support_by_agent=support_by_agent,
            gaps=team_gaps,
        )

    return (
        HistoricalGapReport(
            strict_temporal_mode=strict_temporal_mode,
            gaps=gaps,
            warnings=_dedupe(warnings),
            blocking_errors=_dedupe(blocking_errors),
        ),
        profiles,
    )


def build_equivalence_warnings(profiles: list[TeamHistoricalProfile]) -> list[str]:
    seen: dict[tuple[tuple[str, float], ...], str] = {}
    warnings: list[str] = []
    for profile in profiles:
        signature_key = tuple(sorted(profile.signature.effective_weights.items()))
        label = f"{profile.signature.team_name} v{profile.signature.version_number}"
        if signature_key in seen:
            warnings.append(
                f"{label} and {seen[signature_key]} collapse to the same effective historical "
                "signature. Any remaining differences are in non-executable or identically degraded agent families."
            )
        else:
            seen[signature_key] = label
    return warnings


def _profile_key(team_id: str, version_number: int) -> str:
    return f"{team_id}:{version_number}"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
