from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any

from backend.agents.registry import (
    AGENT_DATA_DEPS,
    ANALYSIS_FACTOR_MAP,
    EXECUTABLE_ANALYSIS_AGENTS,
    REQUIRED_AGENTS,
    SECTOR_NAMES,
    STYLE_TAGS,
)
from backend.database import load_state, save_state
from backend.llm.budget import BudgetTracker
from backend.llm.prompt_packs import PROMPT_PACKS_BY_AGENT, validate_modifiers
from backend.llm.provider import get_llm_client
from backend.models.agent_team import (
    CompiledAgentSpec,
    CompiledTeam,
    DataBoundary,
    ExecutionSnapshot,
    PortfolioConstructionProfile,
    PremadeTeamTemplate,
    StrategyConversation,
    StrategyDraft,
    StrategyMessage,
    StrategyPreferences,
    TeamComparison,
    TeamDraft,
    TeamVersion,
    ValidationReport,
)
from backend.security.input_sanitizer import ContentSource, sanitize
from backend.security.output_validator import parse_llm_json
from backend.settings.user_settings import UserSettings

DEFAULT_TEAM_ID = "default-balanced-core"
DEFAULT_TEAM_LABEL = "Default Balanced Core"
CONVERSATIONS_KEY = "strategy_conversations_v2"
TEAMS_KEY = "strategy_team_versions_v2"
ACTIVE_TEAM_KEY = "strategy_active_team_v2"
STRATEGY_BUILDER_TIMEOUT_SECONDS = 8.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "custom-team"


async def _load_conversations() -> dict[str, dict[str, Any]]:
    return await load_state(CONVERSATIONS_KEY, {})


async def _save_conversations(conversations: dict[str, dict[str, Any]]) -> None:
    await save_state(CONVERSATIONS_KEY, conversations)


async def _load_team_versions() -> dict[str, list[dict[str, Any]]]:
    return await load_state(TEAMS_KEY, {})


async def _save_team_versions(teams: dict[str, list[dict[str, Any]]]) -> None:
    await save_state(TEAMS_KEY, teams)


async def list_strategy_conversations() -> list[StrategyConversation]:
    raw = await _load_conversations()
    conversations = [StrategyConversation.model_validate(item) for item in raw.values()]
    return sorted(conversations, key=lambda item: item.updated_at, reverse=True)


async def create_strategy_conversation(
    user_settings: UserSettings, seed_prompt: str | None = None
) -> StrategyConversation:
    conversation = StrategyConversation(created_at=_now_iso(), updated_at=_now_iso())
    if seed_prompt:
        await process_strategy_message(
            conversation_id=conversation.conversation_id,
            content=seed_prompt,
            request_compile=False,
            user_settings=user_settings,
            conversation=conversation,
        )
        stored = await get_strategy_conversation(conversation.conversation_id)
        if stored is not None:
            return stored
    else:
        raw = await _load_conversations()
        raw[conversation.conversation_id] = conversation.model_dump(mode="json")
        await _save_conversations(raw)
    return conversation


async def get_strategy_conversation(conversation_id: str) -> StrategyConversation | None:
    raw = await _load_conversations()
    payload = raw.get(conversation_id)
    return StrategyConversation.model_validate(payload) if payload else None


def _default_message(role: str, content: str, sanitized_content: str, message_type: str) -> StrategyMessage:
    return StrategyMessage(
        role=role,
        content=content,
        sanitized_content=sanitized_content,
        timestamp=_now_iso(),
        message_type=message_type,
    )


def _append_message(conversation: StrategyConversation, message: StrategyMessage) -> None:
    conversation.messages.append(message)
    conversation.updated_at = _now_iso()


def _normalize_factor_name(name: str) -> str:
    name = name.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "quality_growth": "quality",
        "garp": "growth",
        "income": "income",
        "news": "sentiment",
        "social": "sentiment",
        "rates": "macro",
        "macro_aware": "macro",
    }
    return aliases.get(name, name)


def _raw_user_messages(messages: list[StrategyMessage]) -> str:
    # Local preference extraction should read the user's actual text, not the
    # sanitizer framing that is meant only for downstream LLM safety.
    return "\n".join(message.content.lower() for message in messages if message.role == "user")


def extract_preferences(messages: list[StrategyMessage]) -> StrategyPreferences:
    prefs = StrategyPreferences()
    user_text = _raw_user_messages(messages)
    if not user_text:
        prefs.unresolved_items = ["risk_level", "time_horizon", "primary_factors"]
        return prefs
    user_text = user_text.lower()
    normalized_user_text = re.sub(r"[^a-z0-9.\s%-]+", " ", user_text)

    sentences = [chunk.strip() for chunk in re.split(r"[.!?\n]+", user_text) if chunk.strip()]
    prefs.goal_summary = sentences[-1][:160] if sentences else user_text[:160]

    risk_map = {
        "conservative": "conservative",
        "low risk": "conservative",
        "defensive": "conservative",
        "moderate": "moderate",
        "balanced": "moderate",
        "aggressive": "aggressive",
        "high risk": "aggressive",
        "speculative": "aggressive",
    }
    for token, level in risk_map.items():
        if token in user_text:
            prefs.risk_level = level
    horizon_map = {
        "short": "short",
        "short term": "short",
        "short-term": "short",
        "swing": "short",
        "day trade": "short",
        "medium": "medium",
        "medium term": "medium",
        "medium-term": "medium",
        "intermediate": "medium",
        "long": "long",
        "long term": "long",
        "long-term": "long",
        "compounder": "long",
        "retirement": "long",
    }
    for token, horizon in horizon_map.items():
        if token in user_text:
            prefs.time_horizon = horizon

    universe_map = {
        "large cap": "large_cap_equities",
        "large-cap": "large_cap_equities",
        "small cap": "small_cap_equities",
        "small-cap": "small_cap_equities",
        "crypto": "crypto",
        "etf": "etfs",
        "healthcare": "healthcare_equities",
        "semiconductor": "semiconductor_equities",
    }
    for token, asset_universe in universe_map.items():
        if token in user_text:
            prefs.asset_universe = asset_universe

    positive_factors = []
    negative_factors = []
    for factor in ANALYSIS_FACTOR_MAP:
        normalized = _normalize_factor_name(factor)
        if re.search(rf"\b{factor.replace('_', '[ _-]?')}\b", user_text):
            positive_factors.append(normalized)
    negative_map = {
        "no sentiment": "sentiment",
        "avoid sentiment": "sentiment",
        "sentiment secondary": "sentiment",
        "sentiment is secondary": "sentiment",
        "ignore macro": "macro",
        "no macro": "macro",
        "avoid technicals": "technicals",
        "no technicals": "technicals",
        "avoid growth": "growth",
        "no growth": "growth",
        "avoid value": "value",
        "no value": "value",
    }
    for token, factor in negative_map.items():
        if token in user_text:
            negative_factors.append(factor)
    if "momentum-only" in user_text or "momentum only" in user_text:
        positive_factors.extend(["momentum", "technicals"])
        negative_factors.extend(["value", "macro", "sentiment"])
    positive_factors = [factor for factor in positive_factors if factor not in negative_factors]
    prefs.preferred_factors = sorted(set(positive_factors))
    prefs.deemphasized_factors = sorted(set(negative_factors))

    disabled_agents = set()
    if "no sentiment" in user_text or "avoid sentiment" in user_text:
        disabled_agents.add("sentiment")
    if "no macro" in user_text or "avoid macro" in user_text:
        disabled_agents.add("macro")
    prefs.disabled_agents = sorted(disabled_agents)

    for sector in SECTOR_NAMES:
        human = sector.replace("_", " ")
        if f"exclude {human}" in user_text or f"avoid {human}" in user_text:
            prefs.sector_exclusions.append(sector)
    if "avoid financials" in user_text:
        prefs.sector_exclusions.append("financials")
    if "avoid healthcare" in user_text:
        prefs.sector_exclusions.append("healthcare")
    prefs.sector_exclusions = sorted(set(prefs.sector_exclusions))

    style_tags = []
    for tag in STYLE_TAGS:
        if tag in user_text:
            style_tags.append(tag)
    prefs.style_tags = style_tags

    source_preferences: dict[str, list[str]] = {}
    if "no reddit" in user_text or "avoid reddit" in user_text:
        source_preferences["sentiment"] = ["finnhub", "marketaux", "yfinance"]
    elif "news only" in user_text:
        source_preferences["sentiment"] = ["finnhub", "marketaux"]
    elif "options first" in user_text:
        source_preferences["sentiment"] = ["yfinance", "finnhub", "marketaux"]
    prefs.source_preferences = source_preferences

    modifier_preferences: dict[str, dict[str, Any]] = {}

    def set_modifier(agent_name: str, key: str, value: Any) -> None:
        modifier_preferences.setdefault(agent_name, {})[key] = value

    if "fast news" in user_text or "headline driven" in user_text:
        set_modifier("sentiment", "variant_id", "event_driven")
    if "contrarian" in user_text:
        set_modifier("sentiment", "variant_id", "contrarian_reset")
    if "dividend" in user_text or "income" in user_text:
        set_modifier("value", "variant_id", "dividend_steward")
    if "mean reversion" in user_text:
        set_modifier("technicals", "variant_id", "mean_reversion")
    if "breakout" in user_text:
        set_modifier("technicals", "variant_id", "oneil_breakout")
        set_modifier("momentum", "variant_id", "oneil_leader_tracking")
    if "trend" in user_text and "template" in user_text:
        set_modifier("technicals", "variant_id", "minervini_trend_template")
    if "trend follower" in normalized_user_text or "trend following" in normalized_user_text:
        set_modifier("technicals", "variant_id", "turtle_trend")
        set_modifier("technicals", "rsi_bias", "trend_following")
    if "skeptical sentiment" in normalized_user_text or "filter noisy sentiment" in normalized_user_text:
        set_modifier("sentiment", "variant_id", "skeptical_filter")
    if "crowd momentum" in normalized_user_text or "social momentum" in normalized_user_text:
        set_modifier("sentiment", "variant_id", "crowd_momentum")
    if "all weather" in normalized_user_text:
        set_modifier("macro", "variant_id", "dalio_all_weather")
    if "cycle aware" in normalized_user_text or "cycle watch" in normalized_user_text:
        set_modifier("macro", "variant_id", "marks_cycle_watch")
    if "risk on risk off" in normalized_user_text or "risk-on risk-off" in normalized_user_text:
        set_modifier("macro", "variant_id", "risk_on_risk_off")
    if "quality value" in normalized_user_text:
        set_modifier("value", "variant_id", "buffett_quality_value")
    if "margin of safety" in normalized_user_text or "deep value" in normalized_user_text:
        set_modifier("value", "variant_id", "graham_margin_of_safety")
    if "balance sheet discipline" in normalized_user_text:
        set_modifier("value", "variant_id", "balance_sheet_discipline")
    if "relative strength" in normalized_user_text and "purist" in normalized_user_text:
        set_modifier("momentum", "variant_id", "relative_strength_purist")
    if "conviction trend" in normalized_user_text:
        set_modifier("momentum", "variant_id", "druckenmiller_conviction_trend")
    if "quality growth" in normalized_user_text:
        set_modifier("growth", "variant_id", "fisher_quality_growth")
    if "earnings revision" in normalized_user_text or "revision momentum" in normalized_user_text:
        set_modifier("growth", "variant_id", "earnings_revision")

    technical_lookback_match = re.search(
        r"(?:technical(?:s)?|ohlcv)\s+(?:lookback|window)\s+(\d{2,3})\s*days?", normalized_user_text
    ) or re.search(r"(\d{2,3})\s*day technical(?:s)? lookback", normalized_user_text)
    if technical_lookback_match:
        set_modifier("technicals", "lookback_days", int(technical_lookback_match.group(1)))

    news_lookback_match = re.search(
        r"(?:news|headline)s?\s+(?:lookback|window)\s+(\d{1,2})\s*days?", normalized_user_text
    ) or re.search(r"last\s+(\d{1,2})\s*days?\s+of\s+news", normalized_user_text)
    if news_lookback_match:
        set_modifier("sentiment", "news_lookback_days", int(news_lookback_match.group(1)))

    reddit_lookback_match = re.search(
        r"(?:reddit|social)\s+(?:lookback|window)\s+(\d{1,3})\s*hours?", normalized_user_text
    ) or re.search(r"last\s+(\d{1,3})\s*hours?\s+of\s+(?:reddit|social)", normalized_user_text)
    if reddit_lookback_match:
        set_modifier("sentiment", "reddit_lookback_hours", int(reddit_lookback_match.group(1)))

    if "news first" in normalized_user_text:
        set_modifier("sentiment", "source_weighting", "news_first")
    elif "social first" in normalized_user_text or "reddit first" in normalized_user_text:
        set_modifier("sentiment", "source_weighting", "social_first")
    elif "options first" in normalized_user_text or "put call first" in normalized_user_text:
        set_modifier("sentiment", "source_weighting", "options_first")

    if "rates regime" in normalized_user_text or "rate environment" in normalized_user_text or "rate sensitive" in normalized_user_text:
        set_modifier("macro", "variant_id", "rates_regime")
    if "defensive tilt" in normalized_user_text:
        set_modifier("macro", "defensive_tilt", True)
    if "inflation first" in normalized_user_text or "high inflation priority" in normalized_user_text:
        set_modifier("macro", "inflation_priority", "high")
    elif "low inflation priority" in normalized_user_text:
        set_modifier("macro", "inflation_priority", "low")

    if "income first" in normalized_user_text:
        set_modifier("value", "income_bias", "income_first")
    elif "capital return first" in normalized_user_text or "buyback first" in normalized_user_text:
        set_modifier("value", "income_bias", "capital_return_first")

    if "high filing weight" in normalized_user_text or "filing heavy" in normalized_user_text:
        set_modifier("fundamentals", "filing_weight", "high")
        set_modifier("value", "filing_weight", "high")
    elif "low filing weight" in normalized_user_text or "light filing weight" in normalized_user_text:
        set_modifier("fundamentals", "filing_weight", "low")
        set_modifier("value", "filing_weight", "low")

    if "defensive emphasis" in normalized_user_text:
        set_modifier("fundamentals", "emphasis", "defensive")
    elif "aggressive emphasis" in normalized_user_text:
        set_modifier("fundamentals", "emphasis", "aggressive")

    if "high benchmark weight" in normalized_user_text or "benchmark heavy" in normalized_user_text:
        set_modifier("momentum", "benchmark_weight", "high")
    elif "low benchmark weight" in normalized_user_text:
        set_modifier("momentum", "benchmark_weight", "low")

    range_floor_match = re.search(
        r"(?:range floor|minimum range position|position in range floor)\s+(\d{1,3}(?:\.\d+)?)%?",
        normalized_user_text,
    )
    if range_floor_match:
        raw_floor = float(range_floor_match.group(1))
        floor = raw_floor / 100 if raw_floor > 1 else raw_floor
        set_modifier("momentum", "position_in_range_floor", floor)

    if "high surprise weight" in normalized_user_text or "surprise heavy" in normalized_user_text:
        set_modifier("growth", "surprise_weight", "high")
    elif "low surprise weight" in normalized_user_text:
        set_modifier("growth", "surprise_weight", "low")

    growth_floor_match = re.search(r"growth floor\s+(\d{1,2}(?:\.\d+)?)%?", normalized_user_text)
    if growth_floor_match:
        raw_floor = float(growth_floor_match.group(1))
        floor = raw_floor / 100 if raw_floor > 1 else raw_floor
        set_modifier("growth", "growth_floor", floor)

    prefs.agent_modifier_preferences = modifier_preferences

    unresolved = []
    if not prefs.risk_level:
        unresolved.append("risk_level")
    if not prefs.time_horizon:
        unresolved.append("time_horizon")
    if not prefs.preferred_factors and not prefs.style_tags:
        unresolved.append("primary_factors")
    prefs.unresolved_items = unresolved
    return prefs


def _default_agent_weights() -> dict[str, int]:
    return {
        "fundamentals": 75,
        "technicals": 55,
        "sentiment": 35,
        "macro": 65,
        "value": 70,
        "momentum": 60,
        "growth": 65,
    }


def _heuristic_team_draft(preferences: StrategyPreferences) -> TeamDraft:
    weights = _default_agent_weights()
    enabled = set(EXECUTABLE_ANALYSIS_AGENTS)
    risk_level = preferences.risk_level or "moderate"
    time_horizon = preferences.time_horizon or "medium"

    for factor in preferences.preferred_factors:
        for agent in ANALYSIS_FACTOR_MAP.get(factor, []):
            if agent in weights:
                weights[agent] = min(100, weights[agent] + 15)
    for factor in preferences.deemphasized_factors:
        for agent in ANALYSIS_FACTOR_MAP.get(factor, [factor]):
            if agent in weights:
                weights[agent] = max(0, weights[agent] - 20)
    for agent in preferences.disabled_agents:
        enabled.discard(agent)
        if agent in weights:
            weights[agent] = 0

    if risk_level == "conservative":
        for agent in ("fundamentals", "value", "macro"):
            weights[agent] = min(100, weights[agent] + 10)
        for agent in ("sentiment", "technicals", "momentum"):
            weights[agent] = max(10, weights[agent] - 10)
    elif risk_level == "aggressive":
        for agent in ("growth", "momentum", "technicals", "sentiment"):
            weights[agent] = min(100, weights[agent] + 10)
        weights["macro"] = max(20, weights["macro"] - 10)

    if time_horizon == "short":
        for agent in ("technicals", "momentum", "sentiment"):
            weights[agent] = min(100, weights[agent] + 12)
        for agent in ("value", "macro"):
            weights[agent] = max(10, weights[agent] - 10)
    elif time_horizon == "long":
        for agent in ("fundamentals", "value", "growth", "macro"):
            weights[agent] = min(100, weights[agent] + 10)
        weights["sentiment"] = max(10, weights["sentiment"] - 10)
        weights["technicals"] = max(20, weights["technicals"] - 5)

    if "sentiment" in preferences.deemphasized_factors and "sentiment" not in preferences.disabled_agents:
        weights["sentiment"] = min(weights["sentiment"], 20)
    if "sentiment" in preferences.disabled_agents:
        enabled.discard("sentiment")
    if "macro" in preferences.disabled_agents:
        enabled.discard("macro")

    enabled_agents = sorted(enabled | REQUIRED_AGENTS)
    name_parts = []
    if risk_level:
        name_parts.append(risk_level.capitalize())
    if preferences.preferred_factors:
        name_parts.extend(factor.capitalize() for factor in preferences.preferred_factors[:2])
    elif preferences.style_tags:
        name_parts.append(preferences.style_tags[0].capitalize())
    else:
        name_parts.append("Custom")
    name_parts.append("Team")
    name = " ".join(dict.fromkeys(name_parts))
    description = (
        f"{time_horizon.capitalize()}-horizon team tuned for {preferences.goal_summary or 'grounded equity research'}."
    )
    return TeamDraft(
        name=name,
        description=description,
        enabled_agents=enabled_agents,
        agent_weights={agent: weights.get(agent, 0) for agent in enabled if weights.get(agent, 0) > 0},
        agent_modifiers=deepcopy(preferences.agent_modifier_preferences),
        risk_level=risk_level,
        time_horizon=time_horizon,
        asset_universe=preferences.asset_universe,
        sector_exclusions=preferences.sector_exclusions,
        team_overrides={
            "enable_bull_bear_debate": True,
            "min_confidence_threshold": 0.5 if risk_level == "aggressive" else 0.58,
            "backtest_mode_default": preferences.backtest_mode_default,
        },
    )


async def _model_team_draft(
    preferences: StrategyPreferences, user_settings: UserSettings, fallback: TeamDraft
) -> tuple[TeamDraft, str | None]:
    client = get_llm_client(user_settings.llm)
    if not client.available:
        return fallback, None

    class StrategyBuilderResponse(TeamDraft):
        assistant_reply: str = ""

    prompt_catalog = {
        agent_name: {
            "variants": [variant.variant_id for variant in pack.allowed_variants],
            "modifiers": [modifier.key for modifier in pack.allowed_modifiers],
        }
        for agent_name, pack in PROMPT_PACKS_BY_AGENT.items()
    }
    budget = BudgetTracker(
        max_cost_usd=user_settings.llm.max_cost_per_session_usd,
        max_tokens=user_settings.llm.max_tokens_per_request,
    )
    system = (
        "Return JSON matching StrategyBuilderResponse. "
        "Include every TeamDraft field plus assistant_reply. "
        "Use only the provided agents, variant ids, and modifier keys. "
        "Do not invent agents, adapters, indicators, prompt text, or tools. "
        "assistant_reply should be concise, conversational, and mention the current team direction. "
        "Ask for at most one follow-up only when preferences remain unresolved."
    )
    user = json.dumps(
        {
            "preferences": preferences.model_dump(mode="json"),
            "catalog": prompt_catalog,
            "fallback": fallback.model_dump(mode="json"),
        },
        indent=2,
    )
    try:
        async with asyncio.timeout(STRATEGY_BUILDER_TIMEOUT_SECONDS):
            raw = await client.chat(
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=min(1400, user_settings.llm.max_tokens_per_request),
                temperature=user_settings.llm.temperature_strategy,
                budget=budget,
            )
        parsed = parse_llm_json(raw, StrategyBuilderResponse)
        assistant_reply = parsed.assistant_reply.strip() or None
        return TeamDraft.model_validate(parsed.model_dump(exclude={"assistant_reply"})), assistant_reply
    except Exception:
        return fallback, None


def _describe_team_direction(preferences: StrategyPreferences, model_draft: TeamDraft) -> str:
    parts: list[str] = []
    if preferences.risk_level:
        parts.append(f"{preferences.risk_level} risk")
    if preferences.time_horizon:
        parts.append(f"{preferences.time_horizon}-horizon")
    if preferences.asset_universe and preferences.asset_universe != "us_equities":
        parts.append(preferences.asset_universe.replace("_", " "))
    if preferences.preferred_factors:
        parts.append(f"tilted toward {', '.join(preferences.preferred_factors)}")
    if preferences.deemphasized_factors:
        parts.append(f"de-emphasizing {', '.join(preferences.deemphasized_factors)}")
    if preferences.sector_exclusions:
        sectors = ", ".join(sector.replace("_", " ") for sector in preferences.sector_exclusions)
        parts.append(f"excluding {sectors}")
    summary = ", ".join(parts) if parts else "a balanced multi-factor starting point"
    return f"I'm shaping this into {model_draft.name}: {summary}."


def _fallback_assistant_reply(
    preferences: StrategyPreferences,
    model_draft: TeamDraft,
    follow_up: str | None,
) -> str:
    base = _describe_team_direction(preferences, model_draft)
    if follow_up:
        return f"{base} {follow_up}"
    return f"{base} I have enough to produce a working team draft from here."


def _resolve_variant(agent_name: str, preferences: StrategyPreferences, draft: TeamDraft) -> str:
    variant_id = draft.agent_modifiers.get(agent_name, {}).get("variant_id")
    if variant_id:
        return variant_id
    for tag in preferences.style_tags:
        mapped = STYLE_TAGS.get(tag, {}).get(agent_name)
        if mapped:
            return mapped
    if agent_name == "value" and ("income" in preferences.preferred_factors or "dividend" in preferences.style_tags):
        return "dividend_steward"
    return "balanced"


def _compile_agent_spec(
    agent_name: str,
    weight: int,
    preferences: StrategyPreferences,
    draft: TeamDraft,
) -> CompiledAgentSpec:
    variant_id = _resolve_variant(agent_name, preferences, draft)
    requested_modifiers = deepcopy(draft.agent_modifiers.get(agent_name, {}))
    requested_modifiers.pop("variant_id", None)
    modifiers = validate_modifiers(agent_name, requested_modifiers)
    if agent_name == "sentiment":
        sources = preferences.source_preferences.get(agent_name, AGENT_DATA_DEPS[agent_name])
    else:
        sources = AGENT_DATA_DEPS[agent_name]
    freshness_limit = 45 if preferences.time_horizon == "short" else 120
    lookback_defaults = {
        "technicals": {"days": int(modifiers.get("lookback_days", 260))},
        "sentiment": {
            "news_days": int(modifiers.get("news_lookback_days", 7)),
            "reddit_hours": int(modifiers.get("reddit_lookback_hours", 48)),
        },
        "momentum": {"months": 12 if preferences.time_horizon != "short" else 6},
        "macro": {"months": 6},
        "growth": {"quarters": 4},
        "fundamentals": {"quarters": 4},
        "value": {"filings": 2},
    }
    pack = PROMPT_PACKS_BY_AGENT[agent_name]
    return CompiledAgentSpec(
        agent_name=agent_name,
        enabled=True,
        weight=weight,
        prompt_pack_id=pack.pack_id,
        prompt_pack_version=pack.version,
        variant_id=variant_id,
        modifiers=modifiers,
        owned_sources=sources,
        freshness_limit_minutes=freshness_limit,
        lookback_config=lookback_defaults.get(agent_name, {}),
    )


def _build_portfolio_profile(
    risk_level: str,
    time_horizon: str,
    overrides: dict[str, Any] | None = None,
) -> PortfolioConstructionProfile:
    profile = PortfolioConstructionProfile()
    risk_level = risk_level.strip().lower()
    time_horizon = time_horizon.strip().lower()

    if risk_level == "conservative":
        profile = profile.model_copy(
            update={
                "concentration_style": "diversified",
                "sizing_style": "defensive",
                "turnover_style": "low",
                "cash_policy": "defensive_cash",
                "candidate_pool_size": 70,
                "top_n_target": 12,
                "min_conviction_score": 0.20,
                "max_position_pct": 8.0,
                "cash_floor_pct": 10.0,
                "sector_cap_pct": 25.0,
                "score_exponent": 1.35,
                "selection_buffer_pct": 0.6,
                "turnover_buffer_pct": 0.45,
                "max_turnover_pct": 18.0,
                "hold_zone_pct": 1.5,
                "replacement_threshold": 0.08,
                "persistence_bonus": 0.05,
            }
        )
    elif risk_level == "aggressive":
        profile = profile.model_copy(
            update={
                "concentration_style": "concentrated",
                "sizing_style": "aggressive",
                "turnover_style": "high",
                "cash_policy": "fully_invested",
                "risk_adjustment_mode": "none",
                "candidate_pool_size": 50,
                "top_n_target": 8,
                "min_conviction_score": 0.15,
                "min_position_pct": 3.0,
                "max_position_pct": 18.0,
                "cash_floor_pct": 2.0,
                "sector_cap_pct": 45.0,
                "score_exponent": 2.0,
                "selection_buffer_pct": 0.35,
                "turnover_buffer_pct": 0.2,
                "max_turnover_pct": 40.0,
                "hold_zone_pct": 0.75,
                "replacement_threshold": 0.04,
                "persistence_bonus": 0.02,
            }
        )

    if time_horizon == "short":
        profile = profile.model_copy(
            update={
                "turnover_style": "high",
                "rebalance_frequency_preference": "weekly",
                "selection_buffer_pct": min(profile.selection_buffer_pct, 0.4),
                "turnover_buffer_pct": min(profile.turnover_buffer_pct, 0.2),
                "hold_zone_pct": min(profile.hold_zone_pct, 0.75),
                "replacement_threshold": min(profile.replacement_threshold, 0.04),
            }
        )
    elif time_horizon == "long":
        profile = profile.model_copy(
            update={
                "turnover_style": "low",
                "rebalance_frequency_preference": "monthly",
                "candidate_pool_size": profile.candidate_pool_size + 10,
                "selection_buffer_pct": max(profile.selection_buffer_pct, 0.6),
                "turnover_buffer_pct": max(profile.turnover_buffer_pct, 0.45),
                "hold_zone_pct": max(profile.hold_zone_pct, 1.5),
                "replacement_threshold": max(profile.replacement_threshold, 0.08),
                "persistence_bonus": max(profile.persistence_bonus, 0.05),
            }
        )
    else:
        profile = profile.model_copy(update={"rebalance_frequency_preference": "biweekly"})

    if overrides:
        portfolio_overrides = {
            key: value
            for key, value in overrides.items()
            if key in PortfolioConstructionProfile.model_fields
        }
        if portfolio_overrides:
            profile = profile.model_copy(update=portfolio_overrides)
    return profile


def compile_team(team_draft: TeamDraft, preferences: StrategyPreferences) -> CompiledTeam:
    enabled = [agent for agent in team_draft.enabled_agents if agent in EXECUTABLE_ANALYSIS_AGENTS]
    if not enabled:
        enabled = ["fundamentals", "macro", "value"]
    enabled = sorted(set(enabled))

    weights = {}
    for agent in enabled:
        candidate = team_draft.agent_weights.get(agent, _default_agent_weights().get(agent, 50))
        weights[agent] = max(0, min(100, int(candidate)))

    compiled_agent_specs = {
        agent: _compile_agent_spec(agent, weight, preferences, team_draft)
        for agent, weight in weights.items()
        if weight > 0
    }
    enabled_agents = sorted(set(compiled_agent_specs) | REQUIRED_AGENTS)
    warnings = []
    if preferences.unresolved_items:
        warnings.append(
            "Draft compiled with defaults because some preferences were unresolved: "
            + ", ".join(preferences.unresolved_items)
        )

    compiled = CompiledTeam(
        team_id=team_draft.team_id or f"team-{_slug(team_draft.name)}",
        name=team_draft.name,
        description=team_draft.description,
        enabled_agents=enabled_agents,
        agent_weights=weights,
        compiled_agent_specs=compiled_agent_specs,
        risk_level=team_draft.risk_level,
        time_horizon=team_draft.time_horizon,
        asset_universe=team_draft.asset_universe,
        sector_exclusions=team_draft.sector_exclusions,
        team_overrides=team_draft.team_overrides,
        portfolio_construction=_build_portfolio_profile(
            team_draft.risk_level,
            team_draft.time_horizon,
            overrides=team_draft.team_overrides,
        ).model_copy(update=team_draft.portfolio_construction.model_dump(mode="python", exclude_unset=True)),
        validation_report=ValidationReport(
            valid=True,
            warnings=warnings,
            normalized_fields=sorted(set(REQUIRED_AGENTS) - set(team_draft.enabled_agents)),
        ),
    )
    return compiled


def default_compiled_team() -> CompiledTeam:
    base_preferences = StrategyPreferences(
        goal_summary="Balanced benchmark-aware equity research",
        risk_level="moderate",
        time_horizon="medium",
        preferred_factors=["quality", "macro", "momentum"],
        unresolved_items=[],
    )
    draft = TeamDraft(
        team_id=DEFAULT_TEAM_ID,
        name="Balanced Core",
        description="Premade benchmark-first research team spanning quality, macro, value, growth, and trend.",
        enabled_agents=sorted(EXECUTABLE_ANALYSIS_AGENTS | REQUIRED_AGENTS),
        agent_weights={
            "fundamentals": 78,
            "technicals": 55,
            "sentiment": 25,
            "macro": 70,
            "value": 72,
            "momentum": 58,
            "growth": 66,
        },
        agent_modifiers={
            "fundamentals": {"variant_id": "balanced"},
            "technicals": {"variant_id": "balanced"},
            "sentiment": {"variant_id": "skeptical_filter"},
            "macro": {"variant_id": "balanced"},
            "value": {"variant_id": "balanced"},
            "momentum": {"variant_id": "balanced"},
            "growth": {"variant_id": "balanced"},
        },
        risk_level="moderate",
        time_horizon="medium",
        team_overrides={
            "enable_bull_bear_debate": True,
            "min_confidence_threshold": 0.55,
            "backtest_mode_default": "backtest_strict",
        },
        portfolio_construction=_build_portfolio_profile("moderate", "medium"),
    )
    compiled = compile_team(draft, base_preferences)
    compiled.team_id = DEFAULT_TEAM_ID
    compiled.version_number = 1
    return compiled


def default_team_version() -> TeamVersion:
    compiled = default_compiled_team()
    return TeamVersion.from_compiled(
        compiled,
        created_at="2026-04-03T00:00:00+00:00",
        label=DEFAULT_TEAM_LABEL,
        source_conversation_id=None,
        is_default=True,
        status="active",
    )


def compare_to_default(compiled_team: CompiledTeam) -> TeamComparison:
    default_team = default_compiled_team()
    added = sorted(set(compiled_team.enabled_agents) - set(default_team.enabled_agents))
    removed = sorted(set(default_team.enabled_agents) - set(compiled_team.enabled_agents))
    weight_diff = {}
    modifier_diff = {}
    for agent in sorted(set(compiled_team.agent_weights) | set(default_team.agent_weights)):
        default_weight = default_team.agent_weights.get(agent, 0)
        candidate_weight = compiled_team.agent_weights.get(agent, 0)
        if default_weight != candidate_weight:
            weight_diff[agent] = {"default": default_weight, "candidate": candidate_weight}
        default_modifiers = (
            default_team.compiled_agent_specs.get(agent).modifiers
            if agent in default_team.compiled_agent_specs
            else {}
        )
        candidate_modifiers = (
            compiled_team.compiled_agent_specs.get(agent).modifiers
            if agent in compiled_team.compiled_agent_specs
            else {}
        )
        if default_modifiers != candidate_modifiers:
            modifier_diff[agent] = {"default": default_modifiers, "candidate": candidate_modifiers}
    summary_parts = []
    if added:
        summary_parts.append(f"adds {', '.join(added)}")
    if removed:
        summary_parts.append(f"removes {', '.join(removed)}")
    if not summary_parts:
        summary_parts.append("keeps the same agent lineup but changes weighting and framing")
    return TeamComparison(
        default_team_id=DEFAULT_TEAM_ID,
        candidate_team_id=compiled_team.team_id,
        agent_diff={"added": added, "removed": removed},
        weight_diff=weight_diff,
        modifier_diff=modifier_diff,
        risk_diff={"default": default_team.risk_level, "candidate": compiled_team.risk_level},
        horizon_diff={"default": default_team.time_horizon, "candidate": compiled_team.time_horizon},
        exclusion_diff={
            "default": default_team.sector_exclusions,
            "candidate": compiled_team.sector_exclusions,
        },
        summary="Compared with the premade default team, this configuration " + ", ".join(summary_parts) + ".",
    )


def compile_from_template(template: PremadeTeamTemplate) -> CompiledTeam:
    """Compile a PremadeTeamTemplate into an executable CompiledTeam."""
    prefs = StrategyPreferences(
        goal_summary=template.description,
        risk_level=template.risk_level,
        time_horizon=template.time_horizon,
        sector_exclusions=template.excluded_sectors,
        unresolved_items=[],
    )
    agent_modifiers: dict[str, dict[str, Any]] = {
        agent: {"variant_id": variant_id}
        for agent, variant_id in template.agent_variants.items()
    }
    # Sanitize display_name to the characters TeamDraft allows.
    safe_name = re.sub(r"[^a-zA-Z0-9\s\-_]", " ", template.display_name).strip()[:64] or template.team_id
    draft = TeamDraft(
        team_id=template.team_id,
        name=safe_name,
        description=template.description,
        enabled_agents=sorted(set(template.enabled_analysis_agents) | REQUIRED_AGENTS),
        agent_weights={
            agent: template.weights.get(agent, 0)
            for agent in template.enabled_analysis_agents
        },
        agent_modifiers=agent_modifiers,
        risk_level=template.risk_level,
        time_horizon=template.time_horizon,
        sector_exclusions=template.excluded_sectors,
        team_overrides=dict(template.team_overrides),
        portfolio_construction=template.portfolio_construction,
    )
    compiled = compile_team(draft, prefs)
    compiled.team_id = template.team_id
    return compiled


async def process_strategy_message(
    conversation_id: str,
    content: str,
    request_compile: bool,
    user_settings: UserSettings,
    conversation: StrategyConversation | None = None,
) -> tuple[StrategyConversation, StrategyDraft, CompiledTeam | None, TeamComparison | None, bool]:
    conversation = conversation or await get_strategy_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Unknown conversation: {conversation_id}")

    sanitized = sanitize(content, ContentSource.USER_STRATEGY_INPUT)
    _append_message(
        conversation,
        _default_message("user", content, sanitized.sanitized_text, "input"),
    )

    preferences = extract_preferences(conversation.messages)
    conversation.preferences = preferences
    heuristic_draft = _heuristic_team_draft(preferences)
    model_draft, model_reply = await _model_team_draft(preferences, user_settings, heuristic_draft)
    # Preserve deterministic preference-derived modifiers if the model omits them.
    for agent_name, modifiers in preferences.agent_modifier_preferences.items():
        model_draft.agent_modifiers.setdefault(agent_name, {}).update(
            {key: value for key, value in modifiers.items() if key not in model_draft.agent_modifiers.get(agent_name, {})}
        )

    summary = (
        f"Current plan: {model_draft.name} emphasizes "
        f"{', '.join(preferences.preferred_factors or ['balanced multi-factor research'])}."
    )
    follow_up = None
    if preferences.unresolved_items:
        if "risk_level" in preferences.unresolved_items and "time_horizon" in preferences.unresolved_items:
            follow_up = "I can sharpen the team if you specify the risk level and time horizon."
        elif "risk_level" in preferences.unresolved_items:
            follow_up = "What risk level should this team target: conservative, moderate, or aggressive?"
        elif "time_horizon" in preferences.unresolved_items:
            follow_up = "What time horizon should this team target: short, medium, or long?"
        else:
            follow_up = "Which factor should lead the team most strongly: value, growth, momentum, macro, or sentiment?"

    draft = StrategyDraft(
        conversation_id=conversation.conversation_id,
        summary=summary,
        team_draft=model_draft,
        rationale=(
            "The builder translated your conversation into a bounded team draft using the trusted agent catalog, "
            "prompt variants, and safe overrides only."
        ),
        follow_up_question=follow_up,
        unresolved_items=preferences.unresolved_items,
        default_team_comparison_note="The draft is always compared against the premade default team before save.",
    )
    conversation.latest_draft = draft
    conversation.status = "draft_ready" if not preferences.unresolved_items else "collecting_requirements"

    assistant_text = model_reply or summary
    message_type = "summary"
    if follow_up:
        assistant_text = model_reply or _fallback_assistant_reply(preferences, model_draft, follow_up)
        message_type = "follow_up"
    elif not model_reply:
        assistant_text = _fallback_assistant_reply(preferences, model_draft, follow_up=None)
    _append_message(
        conversation,
        _default_message("assistant", assistant_text, assistant_text, message_type),
    )

    compiled: CompiledTeam | None = None
    comparison: TeamComparison | None = None
    if request_compile or not preferences.unresolved_items:
        compiled = compile_team(model_draft, preferences)
        comparison = compare_to_default(compiled)

    raw = await _load_conversations()
    raw[conversation.conversation_id] = conversation.model_dump(mode="json")
    await _save_conversations(raw)
    return conversation, draft, compiled, comparison, bool(follow_up)


async def compile_strategy_conversation(
    conversation_id: str,
    user_settings: UserSettings,
) -> tuple[StrategyConversation, StrategyDraft, CompiledTeam, TeamComparison]:
    conversation = await get_strategy_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Unknown conversation: {conversation_id}")
    preferences = extract_preferences(conversation.messages)
    conversation.preferences = preferences
    heuristic_draft = _heuristic_team_draft(preferences)
    draft_team, _assistant_reply = await _model_team_draft(preferences, user_settings, heuristic_draft)
    draft = StrategyDraft(
        conversation_id=conversation.conversation_id,
        summary=f"Compiled draft for {draft_team.name}.",
        team_draft=draft_team,
        rationale="The conversation was compiled into an executable team with validated prompt packs and modifiers.",
        follow_up_question=None,
        unresolved_items=preferences.unresolved_items,
        default_team_comparison_note="Compared against the premade default team.",
    )
    conversation.latest_draft = draft
    compiled = compile_team(draft_team, preferences)
    comparison = compare_to_default(compiled)
    conversation.status = "draft_ready"
    raw = await _load_conversations()
    raw[conversation.conversation_id] = conversation.model_dump(mode="json")
    await _save_conversations(raw)
    return conversation, draft, compiled, comparison


async def list_team_versions() -> list[TeamVersion]:
    raw = await _load_team_versions()
    versions = []
    for version_list in raw.values():
        versions.extend(TeamVersion.model_validate(item) for item in version_list)
    versions.append(default_team_version())
    return sorted(versions, key=lambda item: (item.is_default, item.created_at), reverse=True)


async def get_team_versions_for(team_id: str) -> list[TeamVersion]:
    if team_id == DEFAULT_TEAM_ID:
        return [default_team_version()]
    raw = await _load_team_versions()
    return [TeamVersion.model_validate(item) for item in raw.get(team_id, [])]


async def get_team_version(team_id: str, version_number: int | None = None) -> TeamVersion | None:
    versions = await get_team_versions_for(team_id)
    if not versions:
        return None
    if version_number is None:
        return max(versions, key=lambda item: item.version_number)
    for version in versions:
        if version.version_number == version_number:
            return version
    return None


async def save_team_version(
    compiled_team: CompiledTeam,
    *,
    conversation_id: str | None,
    label: str,
    creation_source: str = "conversation",
) -> TeamVersion:
    if compiled_team.team_id == DEFAULT_TEAM_ID:
        raise ValueError("Default team cannot be overwritten")

    teams = await _load_team_versions()
    existing = [TeamVersion.model_validate(item) for item in teams.get(compiled_team.team_id, [])]
    next_version = (max((item.version_number for item in existing), default=0) + 1)
    compiled_payload = compiled_team.model_copy(deep=True)
    compiled_payload.version_number = next_version
    # Validate creation_source literal
    from typing import Literal, get_args
    _valid_sources = ("conversation", "premade", "custom_conversation", "studio_edit", "patch")
    safe_source = creation_source if creation_source in _valid_sources else "conversation"
    version = TeamVersion.from_compiled(
        compiled_payload,
        created_at=_now_iso(),
        label=label,
        source_conversation_id=conversation_id,
        is_default=False,
        status="draft",
        creation_source=safe_source,  # type: ignore[arg-type]
    )
    teams.setdefault(compiled_team.team_id, [])
    teams[compiled_team.team_id].append(version.model_dump(mode="json"))
    await _save_team_versions(teams)
    if conversation_id:
        conversations = await _load_conversations()
        if conversation_id in conversations:
            conversation = StrategyConversation.model_validate(conversations[conversation_id])
            conversation.final_team_version_id = f"{version.team_id}:{version.version_number}"
            conversation.status = "finalized"
            conversations[conversation_id] = conversation.model_dump(mode="json")
            await _save_conversations(conversations)
    return version


async def delete_team_version(team_id: str, version_number: int) -> bool:
    raw = await _load_team_versions()
    if team_id not in raw:
        return False
    raw[team_id] = [item for item in raw[team_id] if item.get("version_number") != version_number]
    if not raw[team_id]:
        del raw[team_id]
    await _save_team_versions(raw)
    return True


async def select_active_team(team_id: str, version_number: int | None = None) -> TeamVersion:
    version = await get_team_version(team_id, version_number)
    if version is None:
        raise ValueError(f"Unknown team selection: {team_id}#{version_number or 'latest'}")
    if team_id != DEFAULT_TEAM_ID:
        teams = await _load_team_versions()
        updated = []
        for payload in teams.get(team_id, []):
            item = TeamVersion.model_validate(payload)
            item.status = "active" if item.version_number == version.version_number else "archived"
            updated.append(item.model_dump(mode="json"))
        if updated:
            teams[team_id] = updated
            await _save_team_versions(teams)
    await save_state(
        ACTIVE_TEAM_KEY,
        {"team_id": version.team_id, "version_number": version.version_number},
    )
    return version


async def get_active_team() -> TeamVersion | None:
    payload = await load_state(ACTIVE_TEAM_KEY, None)
    if not payload:
        return None
    return await get_team_version(payload["team_id"], payload.get("version_number"))


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


async def resolve_effective_team(
    *,
    user_settings: UserSettings,
    team_config: dict[str, Any] | CompiledTeam | None = None,
    team_id: str | None = None,
    version_number: int | None = None,
) -> CompiledTeam:
    if team_config is not None:
        if isinstance(team_config, CompiledTeam):
            return team_config
        return CompiledTeam.model_validate(team_config)
    if team_id:
        version = await get_team_version(team_id, version_number)
        if version:
            return version.compiled_team
    active_team = await get_active_team()
    if active_team:
        return active_team.compiled_team
    return default_compiled_team()


def apply_team_overrides(user_settings: UserSettings, compiled_team: CompiledTeam) -> UserSettings:
    merged = user_settings.to_dict()
    overrides = compiled_team.team_overrides
    if "enable_bull_bear_debate" in overrides:
        merged["agents"]["enable_bull_bear_debate"] = bool(overrides["enable_bull_bear_debate"])
    if "min_confidence_threshold" in overrides:
        merged["agents"]["min_confidence_threshold"] = float(overrides["min_confidence_threshold"])
    return UserSettings.from_dict(merged)


def build_execution_snapshot(
    *,
    mode: str,
    ticker_or_universe: str,
    user_settings: UserSettings,
    compiled_team: CompiledTeam,
    data_boundary: DataBoundary,
    cost_model: dict[str, Any],
    notes: list[str] | None = None,
) -> ExecutionSnapshot:
    llm_settings = user_settings.llm
    prompt_pack_versions = {
        agent_name: f"{spec.prompt_pack_id}@{spec.prompt_pack_version}"
        for agent_name, spec in compiled_team.compiled_agent_specs.items()
    }
    model = llm_settings.model or (
        llm_settings.ollama_model if llm_settings.provider == "ollama" else ""
    )
    snap = ExecutionSnapshot(
        mode=mode,  # type: ignore[arg-type]
        created_at=_now_iso(),
        ticker_or_universe=ticker_or_universe,
        effective_team=compiled_team,
        provider=llm_settings.provider,
        model=model or "provider-default",
        prompt_pack_versions=prompt_pack_versions,
        settings_hash=_hash_payload(user_settings.to_dict()),
        team_hash=_hash_payload(compiled_team.model_dump(mode="json")),
        data_boundary=data_boundary,
        cost_model=cost_model,
        strict_temporal_mode=data_boundary.mode == "backtest_strict",
        notes=notes or [],
    )
    snap.team_classification = compiled_team.team_classification
    snap.prompt_override_present = compiled_team.execution_profile.has_prompt_override
    return snap
