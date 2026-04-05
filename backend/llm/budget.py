from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetTracker:
    max_cost_usd: float
    max_tokens: int
    spent_usd: float = 0.0
    used_tokens: int = 0

    def record(self, estimated_tokens: int, estimated_cost_usd: float) -> None:
        if self.used_tokens + estimated_tokens > self.max_tokens:
            raise ValueError("Token budget exceeded for this session.")
        if self.spent_usd + estimated_cost_usd > self.max_cost_usd:
            raise ValueError("Cost budget exceeded for this session.")
        self.used_tokens += estimated_tokens
        self.spent_usd += estimated_cost_usd
