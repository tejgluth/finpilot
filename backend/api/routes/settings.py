from __future__ import annotations

from copy import deepcopy

from fastapi import APIRouter

from backend.database import load_state, save_state
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


def deep_merge(base: dict, patch: dict) -> dict:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@router.get("/")
async def get_settings():
    raw = await load_state("user_settings", None)
    current = UserSettings.from_dict(raw) if raw else default_user_settings()
    return current.to_dict()


@router.patch("/")
async def update_settings(patch: dict):
    if "patch" in patch and isinstance(patch["patch"], dict):
        patch = patch["patch"]
    raw = await load_state("user_settings", None)
    current = UserSettings.from_dict(raw) if raw else default_user_settings()
    merged = deep_merge(current.to_dict(), patch)
    updated = UserSettings.from_dict(merged)
    updated.guardrails.clamp()
    await save_state("user_settings", updated.to_dict())
    return updated.to_dict()
