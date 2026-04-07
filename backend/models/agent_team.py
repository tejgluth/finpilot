from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


VALID_ANALYSIS_AGENTS = {
    "fundamentals",
    "technicals",
    "sentiment",
    "macro",
    "value",
    "momentum",
    "growth",
}
REQUIRED_DECISION_AGENTS = {"risk_manager", "portfolio_manager"}
VALID_TEAM_AGENTS = VALID_ANALYSIS_AGENTS | REQUIRED_DECISION_AGENTS
VALID_RISK_LEVELS = {"conservative", "moderate", "aggressive"}
VALID_TIME_HORIZONS = {"short", "medium", "long"}
VALID_NODE_FAMILIES = {
    "analysis",
    "synthesis",
    "risk",
    "decision",
    "output",
    "debate",
    "gate",
    "data_preparation",
}
VALID_TEAM_CLASSIFICATIONS = {"premade", "validated_custom", "experimental_custom"}
VALID_CONSENSUS_RULES = {"majority", "unanimous", "weighted_majority", "any", "all_required"}
VALID_EXECUTION_MODES = {"analyze", "paper", "live", "backtest_strict", "backtest_experimental"}
VALID_SECTORS = {
    "communication_services",
    "consumer_discretionary",
    "consumer_staples",
    "energy",
    "financials",
    "healthcare",
    "industrials",
    "information_technology",
    "materials",
    "real_estate",
    "utilities",
}


# ── Custom Team Models ────────────────────────────────────────────────────────

class VisualPosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class PromptOverride(BaseModel):
    override_id: str = Field(default_factory=lambda: uuid4().hex)
    node_id: str
    label: str = ""
    system_prompt_text: str
    created_at: str
    warning: str = (
        "Prompt overrides disable strict backtest eligibility and mark the team as experimental_custom."
    )


class CapabilityBinding(BaseModel):
    capability_id: str
    label: str
    description: str = ""
    source_ids: list[str] = []
    required: bool = True
    configured: bool = True
    strict_backtest_supported: bool = True
    supported_modes: list[str] = Field(default_factory=lambda: sorted(VALID_EXECUTION_MODES))
    detail: str = ""


class NodePromptContract(BaseModel):
    system_prompt_text: str = ""
    allowed_evidence: list[str] = []
    forbidden_inference_rules: list[str] = []
    required_output_schema: str = "AgentSignal"
    operator_notes: str = ""


class NodeModeEligibility(BaseModel):
    analyze: bool = True
    paper: bool = True
    live: bool = True
    backtest_strict: bool = True
    backtest_experimental: bool = True
    reasons: list[str] = []

    def supported_modes_list(self) -> list[str]:
        modes = []
        for mode in ("analyze", "paper", "live", "backtest_strict", "backtest_experimental"):
            if getattr(self, mode):
                modes.append(mode)
        return modes


class ConversationRequirement(BaseModel):
    requirement_id: str
    label: str
    question: str = ""
    value: str = ""
    status: Literal["resolved", "open"] = "open"
    source: Literal["user", "llm", "system"] = "system"


class CapabilityGap(BaseModel):
    capability_id: str
    label: str
    detail: str
    source_ids: list[str] = []
    status: Literal["configured", "available_but_disabled", "missing_key", "requires_new_source"] = "configured"
    can_proceed_degraded: bool = False
    recommended_action: str = ""


class ReasoningOutput(BaseModel):
    """Output produced by a custom reasoning node at runtime."""
    node_id: str = ""
    node_name: str = ""
    recommendation: str = ""        # "BUY" | "SELL" | "HOLD" | "" (optional pass-through)
    confidence: float = 0.5
    reasoning: str = ""
    structured: dict[str, Any] = {}  # arbitrary JSON this node wants to pass forward
    cited_input_ids: list[str] = []  # node_ids this output references


class CompiledReasoningSpec(BaseModel):
    """Compiled spec for a non-data-ingestion (reasoning / output) node."""
    node_id: str
    node_name: str
    node_kind: str = ""
    system_prompt: str
    parameters: dict[str, Any] = {}
    input_node_ids: list[str] = []
    output_schema: str = "ReasoningOutput"
    is_terminal: bool = False
    is_data_ingestion: bool = False
    data_domain: str | None = None


class TeamNode(BaseModel):
    node_id: str
    display_name: str
    # node_family is free-text to allow fully custom reasoning architectures.
    # Known values: "analysis"/"data_ingestion", "reasoning", "output", "synthesis",
    #               "risk", "decision", "debate", "gate", "data_preparation".
    # The compiler uses data_domain (not node_family) to identify ingestion nodes.
    node_family: str = "analysis"
    agent_type: str | None = None  # Free-form identity label; no longer validated against enum
    role_description: str = ""
    enabled: bool = True
    visual_position: VisualPosition = Field(default_factory=VisualPosition)
    upstream_node_ids: list[str] = []
    downstream_node_ids: list[str] = []
    prompt_pack_id: str | None = None
    prompt_pack_version: str | None = None
    variant_id: str = "balanced"
    modifiers: dict[str, Any] = {}
    prompt_override: PromptOverride | None = None
    influence_weight: int = Field(default=50, ge=0, le=100)
    influence_group: str | None = None
    owned_sources: list[str] = []
    capability_bindings: list[CapabilityBinding] = []
    prompt_contract: NodePromptContract | None = None
    mode_eligibility: NodeModeEligibility = Field(default_factory=NodeModeEligibility)
    freshness_limit_minutes: int = 120
    lookback_config: dict[str, int] = {}
    backtest_strict_eligible: bool = True
    backtest_experimental_eligible: bool = True
    paper_eligible: bool = True
    live_eligible: bool = True
    validation_errors: list[str] = []
    validation_warnings: list[str] = []

    # ── Graph-spec fields (custom team architecture) ──────────────────────────
    # data_domain: the data-fetching engine for ingestion nodes.
    # Presence of this field marks the node as a data-ingestion node.
    # Must be one of the 7 known domains when set.
    data_domain: str | None = None

    # system_prompt: first-class prompt for this node.
    # For data-ingestion nodes: specialization prompt (anti-hallucination suffix always appended).
    # For custom reasoning nodes: the entire node behavior is defined here.
    # Takes precedence over prompt_contract.system_prompt_text when set.
    system_prompt: str = ""

    # parameters: per-node runtime parameters authored by the LLM or user.
    # Recognized keys: temperature (float), max_tokens (int), output_schema (str),
    #                  input_merge ("concatenate"|"first_only"|"weighted_vote"),
    #                  is_terminal (bool)
    parameters: dict[str, Any] = {}

    # node_kind: free-text descriptor (e.g., "ranking_layer", "consensus_filter").
    # Used only for display and documentation; compiler ignores it for logic.
    node_kind: str = ""


class TeamEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: uuid4().hex)
    source_node_id: str
    target_node_id: str
    label: str = ""
    edge_type: Literal["signal", "veto", "gate", "synthesis", "reasoning"] = "signal"


class TeamTopology(BaseModel):
    topology_id: str = Field(default_factory=lambda: uuid4().hex)
    nodes: list[TeamNode] = []
    edges: list[TeamEdge] = []

    def node_by_id(self, node_id: str) -> "TeamNode | None":
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def adjacency(self) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for edge in self.edges:
            adj.setdefault(edge.source_node_id, []).append(edge.target_node_id)
        return adj


class ConsensusRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: uuid4().hex)
    description: str = ""
    required_agent_types: list[str] = []
    consensus_type: str = "weighted_majority"
    min_agreement_pct: float = 0.5
    veto_on_fail: bool = False


class TeamBehaviorRules(BaseModel):
    consensus_rules: list[ConsensusRule] = []
    gate_conditions: list[str] = []
    routing_notes: str = ""
    debate_enabled: bool = True
    min_confidence_threshold: float = 0.55


class TeamExecutionProfile(BaseModel):
    team_classification: Literal["premade", "validated_custom", "experimental_custom"] = "validated_custom"
    has_prompt_override: bool = False
    has_synthesis_nodes: bool = False
    backtest_strict_eligible: bool = True
    backtest_experimental_eligible: bool = True
    paper_eligible: bool = True
    live_eligible: bool = True
    ineligibility_reasons: list[str] = []
    experimental_warnings: list[str] = []

    def supported_execution_modes_list(self) -> list[str]:
        modes = ["analyze"]
        if self.paper_eligible:
            modes.append("paper")
        if self.backtest_strict_eligible:
            modes.append("backtest_strict")
        if self.backtest_experimental_eligible:
            modes.append("backtest_experimental")
        return modes


class TeamValidationResult(BaseModel):
    valid: bool = True
    team_classification: Literal["premade", "validated_custom", "experimental_custom"] = "validated_custom"
    errors: list[str] = []
    warnings: list[str] = []
    normalized_fields: list[str] = []
    execution_profile: TeamExecutionProfile = Field(default_factory=TeamExecutionProfile)
    topology_errors: list[str] = []
    node_results: dict[str, list[str]] = {}


class ArchitectureIntent(BaseModel):
    """Extended StrategyPreferences with topology-specific intent fields for the custom team flow."""
    goal_summary: str = ""
    risk_level: str = ""
    time_horizon: str = ""
    asset_universe: str = "us_equities"
    sector_exclusions: list[str] = []
    preferred_factors: list[str] = []
    deemphasized_factors: list[str] = []
    disabled_agents: list[str] = []
    source_preferences: dict[str, list[str]] = {}
    style_tags: list[str] = []
    agent_modifier_preferences: dict[str, dict[str, Any]] = {}
    backtest_mode_default: Literal["backtest_strict", "backtest_experimental"] = "backtest_strict"
    comparison_target: str = "default_team"
    unresolved_items: list[str] = []
    # Custom-team-specific topology intent
    desired_complexity: Literal["simple", "moderate", "complex"] = "moderate"
    desired_analysis_node_count: int | None = None
    wants_synthesis_stage: bool = False
    wants_debate_stage: bool = True
    consensus_rules_natural_language: list[str] = []
    manual_control_level: Literal["low", "medium", "high"] = "medium"
    wants_prompt_editing: bool = False
    custom_team_name: str | None = None
    custom_team_description: str | None = None

    def to_strategy_preferences(self) -> "StrategyPreferences":
        """Convert to a StrategyPreferences for use with existing compiler functions."""
        return StrategyPreferences(
            goal_summary=self.goal_summary,
            risk_level=self.risk_level,
            time_horizon=self.time_horizon,
            asset_universe=self.asset_universe,
            sector_exclusions=self.sector_exclusions,
            preferred_factors=self.preferred_factors,
            deemphasized_factors=self.deemphasized_factors,
            disabled_agents=self.disabled_agents,
            source_preferences=self.source_preferences,
            style_tags=self.style_tags,
            agent_modifier_preferences=self.agent_modifier_preferences,
            backtest_mode_default=self.backtest_mode_default,
            comparison_target=self.comparison_target,
            unresolved_items=self.unresolved_items,
        )


class ArchitectureDraft(BaseModel):
    draft_id: str = Field(default_factory=lambda: uuid4().hex)
    conversation_id: str
    intent: ArchitectureIntent = Field(default_factory=ArchitectureIntent)
    topology: TeamTopology = Field(default_factory=TeamTopology)
    behavior_rules: TeamBehaviorRules = Field(default_factory=TeamBehaviorRules)
    rationale: str = ""
    follow_up_question: str | None = None
    unresolved_items: list[str] = []
    proposed_name: str = "Custom Team"
    proposed_description: str = ""
    validation_result: TeamValidationResult | None = None


class ArchitectureConversationTurn(BaseModel):
    assistant_message: str = ""
    resolved_requirements: list[ConversationRequirement] = []
    open_questions: list[ConversationRequirement] = []
    graph_change_summary: list[str] = []
    capability_gaps: list[CapabilityGap] = []
    mode_compatibility: NodeModeEligibility = Field(default_factory=NodeModeEligibility)
    validation_state: TeamValidationResult | None = None


class ArchitecturePatch(BaseModel):
    patch_id: str = Field(default_factory=lambda: uuid4().hex)
    source_team_id: str
    source_version_number: int
    patch_description: str = ""
    node_changes: list[dict[str, Any]] = []
    edge_changes: list[dict[str, Any]] = []
    behavior_changes: list[dict[str, Any]] = []
    requires_recompile: bool = True
    user_confirmed: bool = False
    created_at: str = ""


class CustomConversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: f"cconv-{uuid4().hex[:12]}")
    created_at: str
    updated_at: str
    status: Literal[
        "collecting_requirements",
        "draft_ready",
        "compiled",
        "finalized",
    ] = "collecting_requirements"
    messages: list["StrategyMessage"] = []
    intent: ArchitectureIntent = Field(default_factory=ArchitectureIntent)
    latest_draft: ArchitectureDraft | None = None
    latest_turn: ArchitectureConversationTurn = Field(default_factory=ArchitectureConversationTurn)
    final_team_version_id: str | None = None


# ── End Custom Team Models ────────────────────────────────────────────────────


class AgentWeight(BaseModel):
    agent_name: str
    weight: int = Field(ge=0, le=100)


class AgentConfig(BaseModel):
    name: str
    enabled: bool = True
    weight: int = Field(default=50, ge=0, le=100)
    data_sources: list[str] = []


class StrategyMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    role: Literal["user", "assistant", "system"]
    content: str
    sanitized_content: str
    timestamp: str
    message_type: Literal["input", "follow_up", "summary", "draft", "final"] = "input"


class StrategyPreferences(BaseModel):
    goal_summary: str = ""
    risk_level: str = ""
    time_horizon: str = ""
    asset_universe: str = "us_equities"
    sector_exclusions: list[str] = []
    preferred_factors: list[str] = []
    deemphasized_factors: list[str] = []
    disabled_agents: list[str] = []
    source_preferences: dict[str, list[str]] = {}
    style_tags: list[str] = []
    agent_modifier_preferences: dict[str, dict[str, Any]] = {}
    backtest_mode_default: Literal["backtest_strict", "backtest_experimental"] = "backtest_strict"
    comparison_target: str = "default_team"
    unresolved_items: list[str] = []

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        if not value:
            return value
        value = value.strip().lower()
        if value not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {sorted(VALID_RISK_LEVELS)}")
        return value

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, value: str) -> str:
        if not value:
            return value
        value = value.strip().lower()
        if value not in VALID_TIME_HORIZONS:
            raise ValueError(f"time_horizon must be one of {sorted(VALID_TIME_HORIZONS)}")
        return value

    @field_validator("sector_exclusions")
    @classmethod
    def validate_sectors(cls, value: list[str]) -> list[str]:
        normalized = []
        for sector in value:
            item = sector.strip().lower()
            if item not in VALID_SECTORS:
                raise ValueError(f"Unsupported sector exclusion: {sector}")
            normalized.append(item)
        return sorted(set(normalized))


class TeamDraft(BaseModel):
    team_id: str | None = None
    name: str
    description: str
    enabled_agents: list[str]
    agent_weights: dict[str, int]
    agent_modifiers: dict[str, dict[str, Any]] = {}
    risk_level: str
    time_horizon: str
    asset_universe: str = "us_equities"
    sector_exclusions: list[str] = []
    team_overrides: dict[str, Any] = {}
    portfolio_construction: "PortfolioConstructionProfile" = Field(
        default_factory=lambda: PortfolioConstructionProfile()
    )

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        value = value.strip()[:64]
        if not value:
            raise ValueError("name is required")
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", value):
            raise ValueError("Team name contains invalid characters")
        return value

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {sorted(VALID_RISK_LEVELS)}")
        return value

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_TIME_HORIZONS:
            raise ValueError(f"time_horizon must be one of {sorted(VALID_TIME_HORIZONS)}")
        return value

    @field_validator("enabled_agents")
    @classmethod
    def registered_only(cls, value: list[str]) -> list[str]:
        normalized = []
        for agent in value:
            item = agent.strip().lower()
            if item not in VALID_TEAM_AGENTS:
                raise ValueError(f"Unknown agent: {agent}")
            normalized.append(item)
        return list(dict.fromkeys(normalized))

    @field_validator("agent_weights")
    @classmethod
    def clamp_weights(cls, value: dict[str, int]) -> dict[str, int]:
        return {key.strip().lower(): max(0, min(100, int(weight))) for key, weight in value.items()}

    @field_validator("sector_exclusions")
    @classmethod
    def validate_sectors(cls, value: list[str]) -> list[str]:
        return StrategyPreferences.validate_sectors(value)

    @model_validator(mode="after")
    def enforce_required_agents(self) -> "TeamDraft":
        enabled = set(self.enabled_agents)
        enabled.update(REQUIRED_DECISION_AGENTS)
        self.enabled_agents = sorted(enabled, key=lambda item: (item in REQUIRED_DECISION_AGENTS, item))
        return self


class StrategyDraft(BaseModel):
    draft_id: str = Field(default_factory=lambda: uuid4().hex)
    conversation_id: str
    summary: str
    team_draft: TeamDraft
    rationale: str
    follow_up_question: str | None = None
    unresolved_items: list[str] = []
    default_team_comparison_note: str = ""


class CompiledAgentSpec(BaseModel):
    agent_name: str
    enabled: bool = True
    weight: int = Field(ge=0, le=100)
    prompt_pack_id: str
    prompt_pack_version: str
    variant_id: str
    modifiers: dict[str, Any] = {}
    owned_sources: list[str] = []
    freshness_limit_minutes: int = Field(ge=1)
    lookback_config: dict[str, int] = {}

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, value: str) -> str:
        # Only validate agents that are known standard agents.
        # Custom team compilation may produce specs for data-ingestion agents
        # identified by node_id (not standard agent_name), so allow those through.
        value = value.strip().lower()
        if value and value not in VALID_TEAM_AGENTS:
            # Allow if it looks like a node_id (contains hyphen prefix pattern)
            # or any custom identity string — callers are responsible for valid agent_name.
            pass
        return value


class ValidationReport(BaseModel):
    valid: bool = True
    warnings: list[str] = []
    normalized_fields: list[str] = []


class PortfolioConstructionProfile(BaseModel):
    concentration_style: Literal["concentrated", "balanced", "diversified"] = "balanced"
    sizing_style: Literal["aggressive", "balanced", "defensive"] = "balanced"
    turnover_style: Literal["low", "medium", "high"] = "medium"
    cash_policy: Literal["fully_invested", "cash_optional", "defensive_cash"] = "cash_optional"
    sector_exposure_mode: Literal["capped", "sector_neutral", "unconstrained"] = "capped"
    weighting_mode: Literal[
        "capped_conviction",
        "risk_budgeted",
        "equal_weight",
        "confidence_weighted",
    ] = "capped_conviction"
    risk_adjustment_mode: Literal["none", "mild_inverse_vol", "full_inverse_vol"] = "mild_inverse_vol"
    rebalance_frequency_preference: Literal["weekly", "biweekly", "monthly"] = "monthly"
    candidate_pool_size: int = Field(default=60, ge=5, le=250)
    top_n_target: int = Field(default=10, ge=1, le=100)
    min_conviction_score: float = Field(default=0.18, ge=0.0, le=1.0)
    min_position_pct: float = Field(default=2.0, ge=0.0, le=100.0)
    max_position_pct: float = Field(default=12.0, ge=0.0, le=100.0)
    cash_floor_pct: float = Field(default=5.0, ge=0.0, le=100.0)
    max_gross_exposure_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    sector_cap_pct: float = Field(default=35.0, ge=0.0, le=100.0)
    score_exponent: float = Field(default=1.6, ge=1.0, le=4.0)
    selection_buffer_pct: float = Field(default=0.5, ge=0.0, le=1.0)
    turnover_buffer_pct: float = Field(default=0.35, ge=0.0, le=0.95)
    max_turnover_pct: float = Field(default=25.0, ge=0.0, le=100.0)
    hold_zone_pct: float = Field(default=1.0, ge=0.0, le=100.0)
    replacement_threshold: float = Field(default=0.06, ge=0.0, le=1.0)
    persistence_bonus: float = Field(default=0.03, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_position_bounds(self) -> "PortfolioConstructionProfile":
        if self.min_position_pct > self.max_position_pct:
            raise ValueError("portfolio_construction.min_position_pct cannot exceed max_position_pct")
        if self.cash_floor_pct > self.max_gross_exposure_pct:
            raise ValueError("portfolio_construction.cash_floor_pct cannot exceed max_gross_exposure_pct")
        return self


class CompiledTeam(BaseModel):
    schema_version: str = "compiled-team/v1"
    team_id: str = Field(default_factory=lambda: f"team-{uuid4().hex[:12]}")
    version_number: int = 0
    name: str
    description: str
    enabled_agents: list[str]
    agent_weights: dict[str, int]
    compiled_agent_specs: dict[str, CompiledAgentSpec]
    risk_level: str
    time_horizon: str
    asset_universe: str = "us_equities"
    sector_exclusions: list[str] = []
    team_overrides: dict[str, Any] = {}
    portfolio_construction: PortfolioConstructionProfile = Field(
        default_factory=PortfolioConstructionProfile
    )
    default_team_reference: str = "default-balanced-core"
    compiler_version: str = "1.0.0"
    validation_report: ValidationReport = Field(default_factory=ValidationReport)
    # Custom team fields (optional, default to premade-compatible values)
    team_classification: Literal["premade", "validated_custom", "experimental_custom"] = "premade"
    topology: TeamTopology | None = None
    behavior_rules: TeamBehaviorRules | None = None
    execution_profile: TeamExecutionProfile = Field(default_factory=lambda: TeamExecutionProfile(team_classification="premade"))
    # Graph-spec: compiled specs for all non-data-ingestion nodes (reasoning / output nodes).
    compiled_reasoning_specs: dict[str, "CompiledReasoningSpec"] = {}

    @field_validator("enabled_agents")
    @classmethod
    def validate_enabled_agents(cls, value: list[str]) -> list[str]:
        normalized = []
        for agent in value:
            item = agent.strip().lower()
            if item not in VALID_TEAM_AGENTS:
                raise ValueError(f"Unknown agent: {agent}")
            normalized.append(item)
        normalized = list(dict.fromkeys(normalized))
        for required in REQUIRED_DECISION_AGENTS:
            if required not in normalized:
                normalized.append(required)
        return normalized

    @field_validator("agent_weights")
    @classmethod
    def validate_weights(cls, value: dict[str, int]) -> dict[str, int]:
        return {key.strip().lower(): max(0, min(100, int(weight))) for key, weight in value.items()}

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        return TeamDraft.validate_risk_level(value)

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, value: str) -> str:
        return TeamDraft.validate_time_horizon(value)

    @field_validator("sector_exclusions")
    @classmethod
    def validate_sectors(cls, value: list[str]) -> list[str]:
        return StrategyPreferences.validate_sectors(value)

    @model_validator(mode="after")
    def validate_specs(self) -> "CompiledTeam":
        # Custom teams (validated_custom or experimental_custom) may have topology-only nodes
        # (reasoning nodes, output nodes) with no CompiledAgentSpec — those go in compiled_reasoning_specs.
        if self.team_classification in ("validated_custom", "experimental_custom"):
            # Sync weights from compiled_agent_specs — no strict validation of unknown keys.
            for spec_key, spec in self.compiled_agent_specs.items():
                label_key = spec_key if spec_key in self.agent_weights else spec.agent_name
                if spec.weight != self.agent_weights.get(label_key, spec.weight):
                    self.agent_weights[label_key] = spec.weight
        else:
            missing = [
                agent
                for agent in self.enabled_agents
                if agent not in REQUIRED_DECISION_AGENTS and agent not in self.compiled_agent_specs
            ]
            if missing:
                raise ValueError(f"compiled_agent_specs missing analysis agents: {missing}")
            for agent_name, spec in self.compiled_agent_specs.items():
                if agent_name not in self.enabled_agents:
                    raise ValueError(f"compiled_agent_spec present for disabled agent: {agent_name}")
                if spec.weight != self.agent_weights.get(agent_name, spec.weight):
                    self.agent_weights[agent_name] = spec.weight
        return self


class TeamComparison(BaseModel):
    default_team_id: str
    candidate_team_id: str
    agent_diff: dict[str, list[str]]
    weight_diff: dict[str, dict[str, int]]
    modifier_diff: dict[str, dict[str, Any]]
    risk_diff: dict[str, str]
    horizon_diff: dict[str, str]
    exclusion_diff: dict[str, list[str]]
    summary: str


class TeamVersion(BaseModel):
    team_id: str
    version_number: int
    created_at: str
    source_conversation_id: str | None = None
    is_default: bool = False
    label: str
    compiled_team: CompiledTeam
    content_hash: str
    status: Literal["draft", "active", "archived"] = "draft"
    # Custom team metadata (optional for backward compat)
    creation_source: Literal["conversation", "premade", "custom_conversation", "studio_edit", "patch"] = "conversation"
    team_classification: Literal["premade", "validated_custom", "experimental_custom"] = "premade"
    topology_hash: str | None = None
    prompt_override_present: bool = False
    supported_execution_modes: list[str] = Field(
        default_factory=lambda: ["analyze", "paper", "backtest_strict", "backtest_experimental"]
    )

    @classmethod
    def from_compiled(
        cls,
        compiled_team: CompiledTeam,
        *,
        created_at: str,
        label: str,
        source_conversation_id: str | None = None,
        is_default: bool = False,
        status: Literal["draft", "active", "archived"] = "draft",
        creation_source: Literal["conversation", "premade", "custom_conversation", "studio_edit", "patch"] = "conversation",
    ) -> "TeamVersion":
        payload = compiled_team.model_dump(mode="json", exclude_none=True)
        payload["version_number"] = 0
        content_hash = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        ep = compiled_team.execution_profile
        return cls(
            team_id=compiled_team.team_id,
            version_number=compiled_team.version_number,
            created_at=created_at,
            source_conversation_id=source_conversation_id,
            is_default=is_default,
            label=label,
            compiled_team=compiled_team,
            content_hash=content_hash,
            status=status,
            creation_source=creation_source,
            team_classification=compiled_team.team_classification,
            prompt_override_present=ep.has_prompt_override,
            supported_execution_modes=ep.supported_execution_modes_list(),
        )


class DataBoundary(BaseModel):
    mode: Literal["live", "paper", "backtest_strict", "backtest_experimental"]
    as_of_datetime: str | None = None
    market_session_reference: str = "NYSE"
    allow_latest_semantics: bool = False


class ExecutionSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"snap-{uuid4().hex[:12]}")
    mode: Literal["analyze", "paper", "live", "backtest_strict", "backtest_experimental"]
    created_at: str
    ticker_or_universe: str
    effective_team: CompiledTeam
    provider: str
    model: str
    prompt_pack_versions: dict[str, str]
    settings_hash: str
    team_hash: str
    data_boundary: DataBoundary
    cost_model: dict[str, Any]
    benchmark_symbol: str = "SPY"
    strict_temporal_mode: bool = False
    notes: list[str] = []
    team_classification: Literal["premade", "validated_custom", "experimental_custom"] = "premade"
    prompt_override_present: bool = False


class StrategyConversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: f"conv-{uuid4().hex[:12]}")
    created_at: str
    updated_at: str
    status: Literal["collecting_requirements", "draft_ready", "finalized"] = "collecting_requirements"
    messages: list[StrategyMessage] = []
    preferences: StrategyPreferences = Field(default_factory=StrategyPreferences)
    latest_draft: StrategyDraft | None = None
    selected_default_comparison: str = "default_team"
    final_team_version_id: str | None = None


class PremadeTeamTemplate(BaseModel):
    team_id: str
    display_name: str
    description: str
    target_user: str
    suitable_for: list[str] = []
    risk_level: str
    time_horizon: str
    enabled_analysis_agents: list[str]
    weights: dict[str, int]
    agent_variants: dict[str, str] = {}
    team_overrides: dict[str, Any] = {}
    portfolio_construction: PortfolioConstructionProfile = Field(
        default_factory=PortfolioConstructionProfile
    )
    excluded_sectors: list[str] = []
    complexity: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    is_default: bool = False
    is_featured: bool = False
    is_hidden: bool = False
    why_distinct: str = ""
    known_limitations: list[str] = []
    not_for: list[str] = []

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {sorted(VALID_RISK_LEVELS)}")
        return value

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_TIME_HORIZONS:
            raise ValueError(f"time_horizon must be one of {sorted(VALID_TIME_HORIZONS)}")
        return value

    @field_validator("enabled_analysis_agents")
    @classmethod
    def validate_analysis_agents(cls, value: list[str]) -> list[str]:
        invalid = set(value) - VALID_ANALYSIS_AGENTS
        if invalid:
            raise ValueError(f"Invalid analysis agents: {invalid}")
        if not value:
            raise ValueError("At least one analysis agent is required")
        return sorted(set(value))

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: dict[str, int]) -> dict[str, int]:
        out: dict[str, int] = {}
        for agent, weight in value.items():
            if agent not in VALID_ANALYSIS_AGENTS:
                raise ValueError(f"Weight key '{agent}' is not a valid analysis agent")
            out[agent] = max(0, min(100, int(weight)))
        return out

    @field_validator("excluded_sectors")
    @classmethod
    def validate_excluded_sectors(cls, value: list[str]) -> list[str]:
        invalid = set(value) - VALID_SECTORS
        if invalid:
            raise ValueError(f"Invalid sectors: {invalid}")
        return sorted(set(value))


class PremadeTeamCatalog(BaseModel):
    catalog_version: str
    teams: list[PremadeTeamTemplate]
    default_team_id: str
    featured_team_ids: list[str] = []
    hidden_team_ids: list[str] = []

    @field_validator("teams")
    @classmethod
    def validate_catalog_teams(cls, value: list[PremadeTeamTemplate]) -> list[PremadeTeamTemplate]:
        ids = [t.team_id for t in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate team_ids in catalog")
        defaults = [t for t in value if t.is_default]
        if len(defaults) != 1:
            raise ValueError(f"Exactly one team must have is_default=true, found {len(defaults)}")
        return value


class TeamMatchExplanation(BaseModel):
    team_id: str
    match_score: float = Field(ge=0.0, le=1.0)
    matched_dimensions: list[str] = []
    unmatched_dimensions: list[str] = []
    contradictions_detected: list[str] = []
    explanation: str = ""


class TeamRecommendation(BaseModel):
    recommended_team_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: TeamMatchExplanation
    alternatives: list[TeamMatchExplanation] = []
    follow_up_question: str | None = None
    is_premade: bool = True
    is_fallback_to_default: bool = False
    extracted_preferences_summary: str = ""
    error_code: str | None = None


# Legacy compatibility alias while routes/components migrate.
AgentTeamConfig = CompiledTeam
AgentTeam = TeamVersion
