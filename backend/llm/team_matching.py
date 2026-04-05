from __future__ import annotations

from backend.llm.premade_catalog import get_catalog, get_premade_team
from backend.models.agent_team import (
    PremadeTeamTemplate,
    StrategyPreferences,
    TeamMatchExplanation,
    TeamRecommendation,
)

# Maps factor names → team IDs most relevant to that factor (ordered by relevance)
_FACTOR_TEAM_HINTS: dict[str, list[str]] = {
    "value": ["deep-value", "quality-compounder", "garp"],
    "growth": ["high-growth", "garp", "quality-compounder"],
    "momentum": ["momentum-leader", "trend-template", "benchmark-experimental"],
    "quality": ["quality-compounder", "defensive-low-vol", "capital-preservation"],
    "sentiment": ["event-driven-sentiment", "contrarian"],
    "macro": ["macro-aware", "recession-defense", "inflation-aware"],
    "income": ["dividend-income", "inflation-aware"],
    "defensive": ["defensive-low-vol", "recession-defense", "capital-preservation"],
}

# Maps style tags → single most-relevant team ID
_STYLE_TEAM_MAP: dict[str, str] = {
    "buffett": "quality-compounder",
    "graham": "deep-value",
    "lynch": "garp",
    "oneil": "momentum-leader",
    "minervini": "trend-template",
    "dalio": "macro-aware",
    "marks": "recession-defense",
    "druckenmiller": "benchmark-experimental",
    "contrarian": "contrarian",
    "dividend": "dividend-income",
}

# Contradiction pairs: (condition_a, condition_b, warning_message)
_CONTRADICTIONS: list[tuple[str, str, str]] = [
    ("aggressive", "income", "Aggressive risk + income mandate — income teams assume conservative positioning."),
    ("short", "value", "Short horizon + value mandate — value strategies typically require longer holding periods."),
    ("contrarian", "momentum", "Contrarian + momentum signals contradict each other."),
]


def _score_team(
    team: PremadeTeamTemplate,
    preferences: StrategyPreferences,
) -> tuple[float, list[str], list[str]]:
    """Return (raw_score 0-100, matched_dimensions, unmatched_dimensions)."""
    score = 0.0
    matched: list[str] = []
    unmatched: list[str] = []

    # D1 — risk level (25 pts)
    if preferences.risk_level:
        if team.risk_level == preferences.risk_level:
            score += 25
            matched.append(f"risk_level:{preferences.risk_level}")
        else:
            unmatched.append(f"risk_level:{preferences.risk_level}→{team.risk_level}")

    # D2 — time horizon (20 pts)
    if preferences.time_horizon:
        if team.time_horizon == preferences.time_horizon:
            score += 20
            matched.append(f"time_horizon:{preferences.time_horizon}")
        else:
            unmatched.append(f"time_horizon:{preferences.time_horizon}→{team.time_horizon}")

    # D5 — style tag (30 pts, strongest signal — applied before factor to allow override)
    style_match = False
    for tag in preferences.style_tags:
        mapped_id = _STYLE_TEAM_MAP.get(tag)
        if mapped_id and team.team_id == mapped_id:
            score += 30
            matched.append(f"style_tag:{tag}")
            style_match = True
            break

    # D3 — primary factors (up to 20 pts, 5 per matching factor hint, max 4 factors)
    if not style_match:
        factor_pts = 0.0
        for factor in preferences.preferred_factors:
            hints = _FACTOR_TEAM_HINTS.get(factor, [])
            if team.team_id in hints:
                factor_pts = min(factor_pts + 5, 20)
                matched.append(f"factor:{factor}")
        score += factor_pts
        if preferences.preferred_factors and factor_pts == 0:
            unmatched.append(f"factors:{','.join(preferences.preferred_factors)}")

    # D6 — complexity / beginner signal (5 pts)
    if "beginner" in " ".join(preferences.goal_summary.lower().split()):
        if team.complexity == "beginner":
            score += 5
            matched.append("complexity:beginner")

    # Disabled agents — penalise if team weights a disabled agent highly
    for agent in preferences.disabled_agents:
        team_weight = team.weights.get(agent, 0)
        if team_weight > 50:
            score -= 10

    # Benchmark intent
    goal = preferences.goal_summary.lower()
    if any(kw in goal for kw in ("beat", "alpha", "benchmark", "spy")):
        if team.team_id == "benchmark-experimental":
            score += 8
            matched.append("benchmark_intent")

    return max(0.0, min(100.0, score)), matched, unmatched


def _check_contradictions(preferences: StrategyPreferences) -> list[str]:
    warnings: list[str] = []
    risk = preferences.risk_level
    horizon = preferences.time_horizon
    factors = set(preferences.preferred_factors)
    tags = set(preferences.style_tags)

    if risk == "aggressive" and ("income" in factors or "dividend" in tags):
        warnings.append(_CONTRADICTIONS[0][2])
    if horizon == "short" and "value" in factors:
        warnings.append(_CONTRADICTIONS[1][2])
    if "contrarian" in tags and "momentum" in factors:
        warnings.append(_CONTRADICTIONS[2][2])
    return warnings


def match_team(preferences: StrategyPreferences) -> TeamRecommendation:
    # Crypto is not supported
    if preferences.asset_universe == "crypto":
        explanation = TeamMatchExplanation(
            team_id="",
            match_score=0.0,
            contradictions_detected=["crypto_not_supported_v1"],
            explanation="Crypto is not supported in the v1 execution path. US equities only.",
        )
        return TeamRecommendation(
            recommended_team_id=None,
            confidence=0.0,
            explanation=explanation,
            is_premade=False,
            is_fallback_to_default=False,
            error_code="crypto_not_supported_v1",
            extracted_preferences_summary="asset_universe=crypto",
        )

    catalog = get_catalog()
    contradictions = _check_contradictions(preferences)

    # Score every team
    scored: list[tuple[float, PremadeTeamTemplate, list[str], list[str]]] = []
    for team in catalog.teams:
        raw, matched, unmatched = _score_team(team, preferences)
        scored.append((raw, team, matched, unmatched))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_team, best_matched, best_unmatched = scored[0]

    # Beginner override: if no strong signal, prefer beginner team
    has_strong_signal = bool(
        preferences.risk_level
        or preferences.time_horizon
        or preferences.preferred_factors
        or preferences.style_tags
    )
    goal_lower = preferences.goal_summary.lower()
    is_beginner_signal = any(
        kw in goal_lower for kw in ("beginner", "start", "simple", "new to", "first time", "help me begin")
    )
    if is_beginner_signal and not has_strong_signal:
        template = get_premade_team("beginner-baseline")
        if template:
            best_team = template
            best_score = 60.0
            best_matched = ["complexity:beginner"]
            best_unmatched = []

    # Style-tag override: if there's exactly one style tag mapped to a specific team, use it
    if len(preferences.style_tags) == 1:
        tag = preferences.style_tags[0]
        mapped_id = _STYLE_TEAM_MAP.get(tag)
        if mapped_id:
            template = get_premade_team(mapped_id)
            if template:
                best_team = template
                best_score = max(best_score, 75.0)
                if f"style_tag:{tag}" not in best_matched:
                    best_matched = [f"style_tag:{tag}"] + best_matched

    confidence = round(min(best_score / 100.0, 1.0), 3)

    # Fallback to default if confidence is too low
    is_fallback = confidence < 0.25 or not has_strong_signal
    if is_fallback:
        default_id = catalog.default_team_id
        template = get_premade_team(default_id)
        if template:
            best_team = template
            confidence = max(confidence, 0.10)

    # Follow-up question when confidence is low or key dimensions are missing
    follow_up: str | None = None
    unresolved = preferences.unresolved_items
    if "risk_level" in unresolved and "time_horizon" in unresolved:
        follow_up = "What risk level and time horizon should this team target?"
    elif "risk_level" in unresolved:
        follow_up = "What risk level should this team target — conservative, moderate, or aggressive?"
    elif "time_horizon" in unresolved:
        follow_up = "What time horizon — short, medium, or long?"
    elif contradictions:
        follow_up = f"I noticed a potential conflict: {contradictions[0]} Which should take priority?"

    # Alternatives (next 3 scored teams, excluding best)
    alternatives: list[TeamMatchExplanation] = []
    for raw, team, matched, unmatched in scored[1:4]:
        if team.team_id == best_team.team_id:
            continue
        alternatives.append(
            TeamMatchExplanation(
                team_id=team.team_id,
                match_score=round(min(raw / 100.0, 1.0), 3),
                matched_dimensions=matched,
                unmatched_dimensions=unmatched,
                contradictions_detected=[],
                explanation=team.description,
            )
        )

    summary_parts: list[str] = []
    if preferences.risk_level:
        summary_parts.append(f"risk={preferences.risk_level}")
    if preferences.time_horizon:
        summary_parts.append(f"horizon={preferences.time_horizon}")
    if preferences.preferred_factors:
        summary_parts.append(f"factors={','.join(preferences.preferred_factors[:3])}")
    if preferences.style_tags:
        summary_parts.append(f"style={','.join(preferences.style_tags[:2])}")
    prefs_summary = "; ".join(summary_parts) or "no explicit preferences"

    return TeamRecommendation(
        recommended_team_id=best_team.team_id,
        confidence=confidence,
        explanation=TeamMatchExplanation(
            team_id=best_team.team_id,
            match_score=confidence,
            matched_dimensions=best_matched,
            unmatched_dimensions=best_unmatched,
            contradictions_detected=contradictions,
            explanation=best_team.description,
        ),
        alternatives=alternatives[:3],
        follow_up_question=follow_up,
        is_premade=True,
        is_fallback_to_default=is_fallback,
        extracted_preferences_summary=prefs_summary,
    )
