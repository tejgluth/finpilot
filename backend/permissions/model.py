"""
User-configurable permission levels.
FinPilot can warn about live trading, but mode selection stays with the user.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import Enum


class PermissionLevel(Enum):
    FULL_MANUAL = "full_manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


PERMISSION_LEVEL_INFO = {
    PermissionLevel.FULL_MANUAL: {
        "label": "Full Manual",
        "icon": "GREEN",
        "summary": "You approve every trade before it executes.",
        "detail": "Nothing is sent to your broker without your explicit per-trade confirmation.",
        "best_for": "New users, strategies under evaluation, anyone who wants complete control.",
        "risk": "Lowest. You are in the loop for every action.",
    },
    PermissionLevel.SEMI_AUTO: {
        "label": "Semi-Automatic",
        "icon": "AMBER",
        "summary": "Small trades execute automatically; larger ones need your approval.",
        "detail": "Set your auto-confirm limit in Guardrail Settings. Trades below it execute automatically.",
        "best_for": "Users comfortable with their strategy after backtesting.",
        "risk": "Moderate. Set your auto-confirm limit conservatively.",
    },
    PermissionLevel.FULL_AUTO: {
        "label": "Full Automatic",
        "icon": "RED",
        "summary": "All trades execute automatically within your guardrails.",
        "detail": "You are notified of every execution. Kill switch always available.",
        "best_for": "Experienced users with thoroughly tested strategies.",
        "risk": "Highest automation risk. Start with Full Manual or Semi-Auto first.",
    },
}


@dataclass
class UserPermissions:
    level: PermissionLevel = PermissionLevel.FULL_MANUAL
    paper_trading_days_completed: int = 0
    live_trading_acknowledged_risks: bool = False
    live_trading_enabled: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["level"] = self.level.value
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, object] | None) -> "UserPermissions":
        if not raw:
            return cls()
        data = dict(raw)
        data["level"] = PermissionLevel(data.get("level", PermissionLevel.FULL_MANUAL.value))
        allowed = {field.name for field in fields(cls)}
        filtered = {key: value for key, value in data.items() if key in allowed}
        return cls(**filtered)
