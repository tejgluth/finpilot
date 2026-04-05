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
        value = value.strip().lower()
        if value not in VALID_TEAM_AGENTS:
            raise ValueError(f"Unknown agent_name: {value}")
        return value


class ValidationReport(BaseModel):
    valid: bool = True
    warnings: list[str] = []
    normalized_fields: list[str] = []


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
    default_team_reference: str = "default-balanced-core"
    compiler_version: str = "1.0.0"
    validation_report: ValidationReport = Field(default_factory=ValidationReport)

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
    ) -> "TeamVersion":
        payload = compiled_team.model_dump(mode="json", exclude_none=True)
        payload["version_number"] = 0
        content_hash = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
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
