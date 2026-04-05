from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import load_state, save_state
from backend.guardrails.live_trading import evaluate_live_trading_gates
from backend.models.disclosure import REQUIRED_ACKNOWLEDGMENT_IDS, UserDisclosure
from backend.permissions.model import PERMISSION_LEVEL_INFO, PermissionLevel, UserPermissions
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


async def _permissions() -> UserPermissions:
    raw = await load_state("user_permissions", None)
    return UserPermissions.from_dict(raw)


async def _runtime_settings() -> UserSettings:
    raw = await load_state("user_settings", None)
    return UserSettings.from_dict(raw) if raw else default_user_settings()


class PermissionUpdate(BaseModel):
    level: PermissionLevel


def _frontend_permissions_payload(permissions: UserPermissions, live_unlock: dict[str, object] | None = None) -> dict:
    return {
        "level": permissions.level.value,
        "paper_trading_days_completed": permissions.paper_trading_days_completed,
        "live_trading_acknowledged_risks": permissions.live_trading_acknowledged_risks,
        "live_trading_enabled": permissions.live_trading_enabled,
        "level_info": {level.value: info for level, info in PERMISSION_LEVEL_INFO.items()},
        "live_unlock": live_unlock or {},
    }


@router.get("/")
async def get_permissions():
    permissions = await _permissions()
    runtime_settings = await _runtime_settings()
    live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
    permissions.paper_trading_days_completed = int(live_unlock["paper_trading_days_completed"])
    return _frontend_permissions_payload(permissions, live_unlock)


@router.patch("/")
async def update_permissions(payload: PermissionUpdate):
    permissions = await _permissions()
    permissions.level = payload.level
    await save_state("user_permissions", permissions.to_dict())
    AuditLogger.log("user", "permission_changed", permissions.to_dict())
    runtime_settings = await _runtime_settings()
    live_unlock = await evaluate_live_trading_gates(permissions, runtime_settings)
    permissions.paper_trading_days_completed = int(live_unlock["paper_trading_days_completed"])
    return _frontend_permissions_payload(permissions, live_unlock)


@router.post("/acknowledge-risks")
async def acknowledge_risks(payload: UserDisclosure):
    if not set(REQUIRED_ACKNOWLEDGMENT_IDS).issubset(set(payload.accepted_ids)):
        raise HTTPException(status_code=400, detail="All 9 risk acknowledgment items are required.")
    permissions = await _permissions()
    permissions.live_trading_acknowledged_risks = True
    await save_state("user_permissions", permissions.to_dict())
    AuditLogger.log("user", "risk_acknowledged", {"accepted_ids": payload.accepted_ids})
    return {
        "ok": True,
        "acknowledged": permissions.live_trading_acknowledged_risks,
        "live_trading_enabled": permissions.live_trading_enabled,
    }
