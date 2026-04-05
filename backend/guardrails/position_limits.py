from __future__ import annotations

from dataclasses import dataclass

from backend.settings.user_settings import GuardrailConfig


@dataclass
class GuardrailCheckResult:
    allowed: bool
    reasons: list[str]
    clamped_position_pct: float


def check_position_limits(
    proposed_position_pct: float,
    open_positions: int,
    sector_exposure_pct: float,
    daily_loss_pct: float,
    total_drawdown_pct: float,
    guardrails: GuardrailConfig,
    trades_today: int = 0,
) -> GuardrailCheckResult:
    reasons: list[str] = []
    clamped = min(proposed_position_pct, guardrails.max_position_pct)

    if proposed_position_pct > guardrails.max_position_pct:
        reasons.append("Proposed position exceeds max position size.")
    if open_positions >= guardrails.max_open_positions:
        reasons.append("Maximum open positions reached.")
    if sector_exposure_pct > guardrails.max_sector_pct:
        reasons.append("Sector exposure exceeds configured maximum.")
    if daily_loss_pct > guardrails.max_daily_loss_pct:
        reasons.append("Daily loss circuit breaker triggered.")
    if total_drawdown_pct > guardrails.max_total_drawdown_pct:
        reasons.append("Total drawdown limit exceeded.")
    if trades_today >= guardrails.max_trades_per_day:
        reasons.append("Maximum trades per day reached.")
    if guardrails.kill_switch_active:
        reasons.append("Kill switch is active.")

    return GuardrailCheckResult(
        allowed=not reasons,
        reasons=reasons,
        clamped_position_pct=round(clamped, 2),
    )
