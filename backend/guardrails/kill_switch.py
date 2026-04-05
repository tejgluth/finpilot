from __future__ import annotations

from backend.brokers.alpaca_broker import AlpacaBroker
from backend.database import load_state, save_state
from backend.security.audit_logger import AuditLogger


KILL_SWITCH_KEY = "kill_switch"


async def get_kill_switch_state() -> dict[str, str | bool]:
    payload = await load_state(KILL_SWITCH_KEY, {"active": False, "reason": ""})
    return {
        "active": bool(payload.get("active", False)),
        "reason": str(payload.get("reason", "")),
    }


async def is_active() -> bool:
    payload = await get_kill_switch_state()
    return bool(payload["active"])


async def activate(reason: str) -> dict[str, str | bool]:
    cancel_result = await AlpacaBroker().cancel_all_orders()
    payload = {"active": True, "reason": reason, "cancel_result": cancel_result}
    await save_state(KILL_SWITCH_KEY, payload)
    AuditLogger.log("user", "kill_switch_activated", payload)
    return payload


async def deactivate() -> dict[str, str | bool]:
    payload = {"active": False, "reason": ""}
    await save_state(KILL_SWITCH_KEY, payload)
    AuditLogger.log("user", "kill_switch_deactivated", payload)
    return payload


async def activate_kill_switch(reason: str) -> dict[str, str | bool]:
    return await activate(reason)


async def deactivate_kill_switch() -> dict[str, str | bool]:
    return await deactivate()
