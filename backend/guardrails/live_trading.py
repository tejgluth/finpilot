from __future__ import annotations

from backend.config import settings
from backend.permissions.model import UserPermissions
from backend.portfolio_state import count_paper_trading_days
from backend.settings.user_settings import UserSettings


async def evaluate_live_trading_gates(
    permissions: UserPermissions,
    runtime_settings: UserSettings,
) -> dict[str, object]:
    paper_days_completed = await count_paper_trading_days()
    minimum_days = runtime_settings.system.paper_trading_minimum_days
    gates = [
        {
            "id": "broker_credentials",
            "label": "Valid Alpaca credentials",
            "passed": settings.has_alpaca(),
            "detail": "Configured in the local backend only.",
        },
        {
            "id": "risk_disclosures",
            "label": "9 risk disclosures acknowledged",
            "passed": permissions.live_trading_acknowledged_risks,
            "detail": "Required once per local workspace.",
        },
        {
            "id": "paper_track_record",
            "label": f"{minimum_days}+ paper-trading days completed",
            "passed": paper_days_completed >= minimum_days,
            "detail": f"{paper_days_completed} of {minimum_days} required days completed inside FinPilot.",
        },
        {
            "id": "explicit_live_enable",
            "label": "Explicit live enable confirmed in-app",
            "passed": permissions.live_trading_enabled,
            "detail": "Final gate that must be turned on manually after the other gates pass.",
        },
    ]
    return {
        "ready": all(bool(gate["passed"]) for gate in gates),
        "paper_trading_days_completed": paper_days_completed,
        "minimum_paper_trading_days": minimum_days,
        "gates": gates,
    }
