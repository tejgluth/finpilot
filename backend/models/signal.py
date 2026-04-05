from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class DataCitation(BaseModel):
    field_name: str
    value: str
    source: str
    fetched_at: str


class ConfidenceScore(BaseModel):
    raw: float = Field(ge=0.0, le=1.0)
    final: float = Field(ge=0.0, le=1.0)
    warning: str = ""


class AgentSignal(BaseModel):
    ticker: str
    agent_name: str
    action: str
    raw_confidence: float = Field(ge=0.0, le=1.0)
    final_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str
    cited_data: list[DataCitation] = []
    unavailable_fields: list[str] = []
    data_coverage_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    oldest_data_age_minutes: float = 0.0
    warning: str = ""

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.match(r"^[A-Z]{1,5}(-[A-Z]{1,5})?(/[A-Z]{3})?$", normalized):
            raise ValueError(f"Invalid ticker: {value!r}")
        return normalized

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("Action must be BUY, SELL, or HOLD")
        return value

    @field_validator("reasoning")
    @classmethod
    def cap_reasoning(cls, value: str) -> str:
        return value[:500]


class DebateOutput(BaseModel):
    position: str
    thesis: str
    key_points: list[str]
    cited_agents: list[str]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"BULL", "BEAR"}:
            raise ValueError("position must be BULL or BEAR")
        return value

    @field_validator("key_points")
    @classmethod
    def max_five(cls, value: list[str]) -> list[str]:
        return value[:5]


class PortfolioDecision(BaseModel):
    ticker: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    cited_agents: list[str]
    bull_points_used: list[str]
    bear_points_addressed: list[str]
    risk_notes: str
    proposed_position_pct: float = Field(ge=0.0, le=20.0)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("Action must be BUY, SELL, or HOLD")
        return value
