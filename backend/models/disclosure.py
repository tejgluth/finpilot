from __future__ import annotations

from pydantic import BaseModel, Field


REQUIRED_ACKNOWLEDGMENT_IDS = [
    "not_advice",
    "past_performance",
    "ai_errors",
    "real_money",
    "guardrails_not_perfect",
    "automation_risk",
    "my_responsibility",
    "keys_security",
    "paper_first",
]


class UserDisclosure(BaseModel):
    accepted_ids: list[str] = Field(default_factory=list)

    def all_required_present(self) -> bool:
        return set(REQUIRED_ACKNOWLEDGMENT_IDS).issubset(set(self.accepted_ids))


class AcknowledgmentRecord(BaseModel):
    accepted_ids: list[str]
    accepted_at: str
    version: str = "v1"
