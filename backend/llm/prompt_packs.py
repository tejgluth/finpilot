from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class PromptVariant(BaseModel):
    variant_id: str
    label: str
    inspiration: str
    summary: str
    prompt_suffix: str
    default_modifiers: dict[str, Any] = {}


class PromptModifierDefinition(BaseModel):
    key: str
    modifier_type: Literal["enum", "int", "float", "bool"]
    description: str
    default: Any
    allowed_values: list[Any] = []
    min_value: float | None = None
    max_value: float | None = None


class PromptPack(BaseModel):
    pack_id: str
    version: str = "1.0.0"
    agent_name: str
    base_system_prompt: str
    allowed_variants: list[PromptVariant]
    allowed_modifiers: list[PromptModifierDefinition]
    forbidden_capabilities: list[str]
    output_schema_name: str = "AgentSignal"


COMMON_FORBIDDEN = [
    "invent_new_data",
    "invent_new_tools",
    "invent_new_indicators",
    "ignore_data_boundary",
    "cross_agent_domain_access",
]


PROMPT_PACKS: dict[str, PromptPack] = {
    "fundamentals": PromptPack(
        pack_id="fundamentals-core",
        agent_name="fundamentals",
        base_system_prompt="Assess financial health strictly from fetched statement and filing evidence.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Core",
                inspiration="multi-factor grounded analysis",
                summary="Balances quality, leverage, and earnings execution.",
                prompt_suffix="Keep the view balanced across profitability, leverage, and earnings execution.",
            ),
            PromptVariant(
                variant_id="buffett_moat",
                label="Moat Compounder",
                inspiration="Warren Buffett style quality and moat focus",
                summary="Emphasizes capital efficiency, margins, and durable business quality.",
                prompt_suffix="Prefer durable profitability, margin strength, and balance-sheet discipline.",
            ),
            PromptVariant(
                variant_id="graham_deep_value",
                label="Deep Value",
                inspiration="Benjamin Graham margin-of-safety discipline",
                summary="Emphasizes valuation, current ratio, and downside protection.",
                prompt_suffix="Prioritize cheapness, liquidity, and downside protection over excitement.",
            ),
            PromptVariant(
                variant_id="lynch_garp",
                label="GARP Pragmatist",
                inspiration="Peter Lynch growth at a reasonable price",
                summary="Balances earnings execution with reasonable valuation and business strength.",
                prompt_suffix="Balance growth quality with practical valuation discipline.",
            ),
            PromptVariant(
                variant_id="quality_compounder",
                label="Steady Compounder Fundamentals",
                inspiration="quality factor investing",
                summary="Emphasizes consistent margins and high returns on capital across multiple periods — rewards stability over peak metrics.",
                prompt_suffix="Overweight evidence of compounding quality and stable profitability. Prefer margin consistency over margin peaks.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="emphasis",
                modifier_type="enum",
                description="Bias the framing toward conservatism or aggressiveness.",
                default="balanced",
                allowed_values=["defensive", "balanced", "aggressive"],
            ),
            PromptModifierDefinition(
                key="filing_weight",
                modifier_type="enum",
                description="How strongly sanitized filing excerpts should influence framing.",
                default="medium",
                allowed_values=["low", "medium", "high"],
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "technicals": PromptPack(
        pack_id="technicals-core",
        agent_name="technicals",
        base_system_prompt="Interpret only the provided technical indicators and trend context.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Technicals",
                inspiration="multi-signal trend analysis",
                summary="Balances trend, momentum, and overextension risk.",
                prompt_suffix="Use a balanced technical lens across trend, momentum, and exhaustion risk.",
            ),
            PromptVariant(
                variant_id="oneil_breakout",
                label="Breakout Hunter",
                inspiration="William O'Neil style breakout leadership",
                summary="Favors strong trend alignment and leadership behavior.",
                prompt_suffix="Prefer leadership setups, breakout confirmation, and constructive momentum.",
            ),
            PromptVariant(
                variant_id="minervini_trend_template",
                label="Trend Template",
                inspiration="Mark Minervini trend template discipline",
                summary="Demands strong trend structure and clean momentum alignment.",
                prompt_suffix="Require high-quality trend structure and avoid weak or messy setups.",
            ),
            PromptVariant(
                variant_id="mean_reversion",
                label="Mean Reversion",
                inspiration="mean reversion trading frameworks",
                summary="Looks for oversold or stretched conditions likely to snap back.",
                prompt_suffix="Look harder for exhaustion and reversion opportunities than for continuation.",
            ),
            PromptVariant(
                variant_id="turtle_trend",
                label="Trend Follower",
                inspiration="systematic trend following",
                summary="Focuses on continuation and trend persistence rather than turning points.",
                prompt_suffix="Prefer trend persistence and continuation over short-term countertrend moves.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="lookback_days",
                modifier_type="int",
                description="How much OHLCV history to emphasize.",
                default=260,
                min_value=90,
                max_value=520,
            ),
            PromptModifierDefinition(
                key="rsi_bias",
                modifier_type="enum",
                description="How to interpret RSI extremes.",
                default="balanced",
                allowed_values=["balanced", "trend_following", "mean_reversion"],
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "sentiment": PromptPack(
        pack_id="sentiment-core",
        agent_name="sentiment",
        base_system_prompt="Assess only sanitized sentiment, positioning, and social evidence from approved sources.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Sentiment",
                inspiration="multi-source sentiment synthesis",
                summary="Balances news tone, entity sentiment, social chatter, and options fear gauges.",
                prompt_suffix="Balance supportive and skeptical interpretations of sentiment inputs.",
            ),
            PromptVariant(
                variant_id="event_driven",
                label="Event Driven",
                inspiration="headline-driven trading",
                summary="Puts more weight on recent headline and entity sentiment changes.",
                prompt_suffix="Lean harder on headline shifts and entity sentiment changes.",
            ),
            PromptVariant(
                variant_id="contrarian_reset",
                label="Contrarian Reset",
                inspiration="contrarian positioning frameworks",
                summary="Looks for washed-out sentiment that can reverse.",
                prompt_suffix="Treat extreme negativity as potential contrarian fuel if the data supports it.",
            ),
            PromptVariant(
                variant_id="crowd_momentum",
                label="Crowd Momentum",
                inspiration="social proof and participation momentum",
                summary="Treats sustained positive participation as supportive.",
                prompt_suffix="Give more credit to persistent positive participation and crowd alignment.",
            ),
            PromptVariant(
                variant_id="skeptical_filter",
                label="Skeptical Filter",
                inspiration="risk-first sentiment reading",
                summary="Discounts noisy social and headline swings unless corroborated.",
                prompt_suffix="Discount noisy swings and require corroboration across sentiment sources.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="news_lookback_days",
                modifier_type="int",
                description="Lookback window for news headlines.",
                default=7,
                min_value=1,
                max_value=14,
            ),
            PromptModifierDefinition(
                key="reddit_lookback_hours",
                modifier_type="int",
                description="Lookback window for Reddit activity.",
                default=48,
                min_value=6,
                max_value=168,
            ),
            PromptModifierDefinition(
                key="source_weighting",
                modifier_type="enum",
                description="Which source family to emphasize.",
                default="balanced",
                allowed_values=["balanced", "news_first", "social_first", "options_first"],
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "macro": PromptPack(
        pack_id="macro-core",
        agent_name="macro",
        base_system_prompt="Assess the market regime only from fetched macro and cross-asset proxy data.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Macro",
                inspiration="macro regime assessment",
                summary="Balances rates, inflation, growth, and risk proxies.",
                prompt_suffix="Balance macro support and macro headwinds without overfitting one datapoint.",
            ),
            PromptVariant(
                variant_id="dalio_all_weather",
                label="All Weather",
                inspiration="Ray Dalio style regime balancing",
                summary="Focuses on regime resilience and cross-asset confirmation.",
                prompt_suffix="Emphasize regime balance, diversification logic, and cross-asset confirmation.",
            ),
            PromptVariant(
                variant_id="marks_cycle_watch",
                label="Cycle Watch",
                inspiration="Howard Marks cycle awareness",
                summary="Focuses on cycle maturity and asymmetric downside.",
                prompt_suffix="Be especially attentive to cycle maturity and downside asymmetry.",
            ),
            PromptVariant(
                variant_id="risk_on_risk_off",
                label="Risk On / Risk Off",
                inspiration="macro trading regime shifts",
                summary="Focuses on rapid changes in risk appetite.",
                prompt_suffix="Read the macro data through a risk-on versus risk-off lens.",
            ),
            PromptVariant(
                variant_id="rates_regime",
                label="Rate Environment Lens",
                inspiration="interest rate cycle and duration risk analysis",
                summary="Prioritizes rate level, direction, and yield curve shape to assess how the current rate environment affects equity valuations.",
                prompt_suffix="Focus your analysis on the rate environment: Fed funds level, yield curve shape, and CPI/PCE trajectory. Explicitly assess whether the rate environment is supportive or restrictive for equity valuations.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="defensive_tilt",
                modifier_type="bool",
                description="Raise the bar before declaring the regime constructive.",
                default=False,
            ),
            PromptModifierDefinition(
                key="inflation_priority",
                modifier_type="enum",
                description="Relative emphasis on inflation data.",
                default="balanced",
                allowed_values=["balanced", "high", "low"],
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "value": PromptPack(
        pack_id="value-core",
        agent_name="value",
        base_system_prompt="Apply a value lens strictly to provided valuation and filing context.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Value",
                inspiration="classic value investing",
                summary="Balances valuation, cash yield, and shareholder returns.",
                prompt_suffix="Balance cheapness with business durability and shareholder yield.",
            ),
            PromptVariant(
                variant_id="graham_margin_of_safety",
                label="Margin of Safety",
                inspiration="Benjamin Graham strict value discipline",
                summary="Prefers low valuation and a strong margin of safety.",
                prompt_suffix="Require a clearer margin of safety than usual.",
            ),
            PromptVariant(
                variant_id="buffett_quality_value",
                label="Quality Value",
                inspiration="Warren Buffett quality-at-a-fair-price mindset",
                summary="Accepts fair value for stronger business quality.",
                prompt_suffix="Accept fair value when the quality and cash generation look durable.",
            ),
            PromptVariant(
                variant_id="dividend_steward",
                label="Dividend Steward",
                inspiration="income and dividend growth investing",
                summary="Emphasizes dividend yield, growth, and capital return discipline.",
                prompt_suffix="Prioritize income durability and shareholder distribution discipline.",
            ),
            PromptVariant(
                variant_id="balance_sheet_discipline",
                label="Balance Sheet Discipline",
                inspiration="cycle-aware conservative value",
                summary="Focuses on valuation plus balance-sheet resilience.",
                prompt_suffix="Require cheapness plus stronger balance-sheet resilience.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="income_bias",
                modifier_type="enum",
                description="How much to favor income characteristics.",
                default="balanced",
                allowed_values=["balanced", "income_first", "capital_return_first"],
            ),
            PromptModifierDefinition(
                key="filing_weight",
                modifier_type="enum",
                description="How much to weigh management commentary.",
                default="medium",
                allowed_values=["low", "medium", "high"],
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "momentum": PromptPack(
        pack_id="momentum-core",
        agent_name="momentum",
        base_system_prompt="Assess momentum quality strictly from the provided return and relative-strength data.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Momentum",
                inspiration="relative-strength investing",
                summary="Balances medium-term strength with overextension awareness.",
                prompt_suffix="Balance leadership evidence with the risk of late-stage extension.",
            ),
            PromptVariant(
                variant_id="oneil_leader_tracking",
                label="Leadership Tracker",
                inspiration="William O'Neil leader identification",
                summary="Focuses on leadership versus the market benchmark.",
                prompt_suffix="Prioritize market leadership and relative-strength persistence.",
            ),
            PromptVariant(
                variant_id="minervini_breakout_quality",
                label="Breakout Quality",
                inspiration="Mark Minervini momentum quality",
                summary="Demands strong trend quality and healthy participation.",
                prompt_suffix="Require clean trend quality and healthy participation, not just raw speed.",
            ),
            PromptVariant(
                variant_id="druckenmiller_conviction_trend",
                label="Conviction Trend",
                inspiration="Stan Druckenmiller style trend conviction",
                summary="Favors forceful moves with broad confirmation.",
                prompt_suffix="Favor forceful, broad-confirmation trends rather than incremental leadership.",
            ),
            PromptVariant(
                variant_id="relative_strength_purist",
                label="Relative Strength Purist",
                inspiration="systematic relative-strength ranking",
                summary="Focuses almost entirely on benchmark-relative leadership.",
                prompt_suffix="Read the data primarily through relative strength versus SPY.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="benchmark_weight",
                modifier_type="enum",
                description="How strongly to emphasize relative strength versus SPY.",
                default="medium",
                allowed_values=["low", "medium", "high"],
            ),
            PromptModifierDefinition(
                key="position_in_range_floor",
                modifier_type="float",
                description="Minimum 52-week range position considered constructive.",
                default=0.65,
                min_value=0.2,
                max_value=0.95,
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
    "growth": PromptPack(
        pack_id="growth-core",
        agent_name="growth",
        base_system_prompt="Assess growth quality using only fetched revenue, earnings, and surprise data.",
        allowed_variants=[
            PromptVariant(
                variant_id="balanced",
                label="Balanced Growth",
                inspiration="multi-factor growth quality",
                summary="Balances top-line growth, earnings quality, and surprise history.",
                prompt_suffix="Balance growth acceleration with evidence of durable quality.",
            ),
            PromptVariant(
                variant_id="lynch_garp",
                label="Pragmatic Growth",
                inspiration="Peter Lynch style practical growth",
                summary="Favors durable, understandable growth rather than fragile hype.",
                prompt_suffix="Prefer practical, durable growth over flashy but fragile acceleration.",
            ),
            PromptVariant(
                variant_id="fisher_quality_growth",
                label="Quality Growth",
                inspiration="quality growth investing",
                summary="Emphasizes margin trend and growth quality over raw speed.",
                prompt_suffix="Emphasize quality of growth, especially margin durability.",
            ),
            PromptVariant(
                variant_id="earnings_revision",
                label="Beat Rate Acceleration",
                inspiration="earnings surprise and execution consistency frameworks",
                summary="Focuses on beat rate trends and earnings execution consistency. Note: evaluates historical beat consistency only — does not forecast forward estimate revisions.",
                prompt_suffix="Lean harder on repeated execution beats and earnings follow-through. Evaluate beat_rate trend across recent quarters. Do not claim forward estimate revision capability — scope is historical execution consistency only.",
            ),
            PromptVariant(
                variant_id="quality_compounder",
                label="Compounding Growth Quality",
                inspiration="durable compounder framework",
                summary="Seeks steady, predictable growth across multiple periods rather than explosive bursts — rewards low variance and consistent direction.",
                prompt_suffix="Prefer steady compounding growth over one-off spikes. Evaluate variance across all available growth quarters as a stability signal — low variance plus positive trend is preferable to high-peak / high-variance growth.",
            ),
        ],
        allowed_modifiers=[
            PromptModifierDefinition(
                key="surprise_weight",
                modifier_type="enum",
                description="How much to emphasize earnings surprise history.",
                default="medium",
                allowed_values=["low", "medium", "high"],
            ),
            PromptModifierDefinition(
                key="growth_floor",
                modifier_type="float",
                description="Minimum growth rate considered constructive.",
                default=0.08,
                min_value=0.0,
                max_value=0.3,
            ),
        ],
        forbidden_capabilities=COMMON_FORBIDDEN,
    ),
}

PROMPT_PACKS_BY_AGENT = {agent_name: pack for agent_name, pack in PROMPT_PACKS.items()}


def get_prompt_pack(agent_name: str) -> PromptPack:
    try:
        return PROMPT_PACKS_BY_AGENT[agent_name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"No prompt pack registered for agent {agent_name}") from exc


def get_variant(agent_name: str, variant_id: str) -> PromptVariant:
    pack = get_prompt_pack(agent_name)
    for variant in pack.allowed_variants:
        if variant.variant_id == variant_id:
            return variant
    raise ValueError(f"Unknown prompt variant {variant_id!r} for {agent_name}")


def validate_modifiers(agent_name: str, modifiers: dict[str, Any]) -> dict[str, Any]:
    pack = get_prompt_pack(agent_name)
    validated: dict[str, Any] = {}
    for definition in pack.allowed_modifiers:
        value = modifiers.get(definition.key, definition.default)
        if definition.modifier_type == "enum":
            if value not in definition.allowed_values:
                value = definition.default
        elif definition.modifier_type == "bool":
            value = bool(value)
        elif definition.modifier_type in {"int", "float"}:
            numeric = float(value)
            if definition.min_value is not None:
                numeric = max(definition.min_value, numeric)
            if definition.max_value is not None:
                numeric = min(definition.max_value, numeric)
            value = int(numeric) if definition.modifier_type == "int" else round(numeric, 4)
        validated[definition.key] = value
    return validated


def assemble_system_prompt(agent_name: str, domain_prompt: str, variant_id: str, modifiers: dict[str, Any]) -> str:
    pack = get_prompt_pack(agent_name)
    variant = get_variant(agent_name, variant_id)
    modifier_lines = [f"- {key}: {value}" for key, value in validate_modifiers(agent_name, modifiers).items()]
    modifier_text = "\n".join(modifier_lines) if modifier_lines else "- none"
    forbidden = "\n".join(f"- {item}" for item in pack.forbidden_capabilities)
    return "\n".join(
        [
            pack.base_system_prompt,
            domain_prompt.strip(),
            "",
            f"Prompt Variant: {variant.label} ({variant.variant_id})",
            f"Inspiration: {variant.inspiration}",
            variant.prompt_suffix,
            "",
            "Bounded Modifiers:",
            modifier_text,
            "",
            "Forbidden Capabilities:",
            forbidden,
        ]
    ).strip()
