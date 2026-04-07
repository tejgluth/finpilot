from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import load_state
from backend.llm.premade_catalog import get_catalog, get_premade_team
from backend.llm.strategy_builder import (
    compare_to_default,
    compile_from_template,
    compile_strategy_conversation,
    create_strategy_conversation,
    default_team_version,
    delete_team_version,
    get_active_team,
    get_strategy_conversation,
    get_team_version,
    list_strategy_conversations,
    list_team_versions,
    process_strategy_message,
    save_team_version,
    select_active_team,
)
from backend.llm.team_matching import match_team
from backend.models.agent_team import CompiledTeam, StrategyPreferences
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


class StartConversationRequest(BaseModel):
    seed_prompt: str | None = None


class StrategyMessageRequest(BaseModel):
    content: str
    request_compile: bool = False


class SaveTeamRequest(BaseModel):
    conversation_id: str | None = None
    compiled_team: CompiledTeam
    label: str = "Saved Team"


class TeamSelectRequest(BaseModel):
    version_number: int | None = None


class CompareRequest(BaseModel):
    candidate_compiled_team: CompiledTeam | None = None
    team_id: str | None = None
    version_number: int | None = None


async def _runtime_settings() -> UserSettings:
    raw = await load_state("user_settings", None)
    return UserSettings.from_dict(raw) if raw else default_user_settings()


@router.get("/conversations")
async def get_conversations():
    conversations = await list_strategy_conversations()
    return {"conversations": [item.model_dump(mode="json") for item in conversations]}


@router.post("/conversations")
async def start_conversation(payload: StartConversationRequest | None = None):
    conversation = await create_strategy_conversation(
        await _runtime_settings(),
        seed_prompt=payload.seed_prompt if payload else None,
    )
    AuditLogger.log("strategy", "conversation_started", {"conversation_id": conversation.conversation_id})
    return conversation.model_dump(mode="json")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = await get_strategy_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.model_dump(mode="json")


@router.post("/conversations/{conversation_id}/messages")
async def post_message(conversation_id: str, payload: StrategyMessageRequest):
    try:
        conversation, draft, compiled, comparison, needs_follow_up = await process_strategy_message(
            conversation_id=conversation_id,
            content=payload.content,
            request_compile=payload.request_compile,
            user_settings=await _runtime_settings(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    AuditLogger.log(
        "strategy",
        "conversation_message_processed",
        {
            "conversation_id": conversation_id,
            "needs_follow_up": needs_follow_up,
            "compiled": bool(compiled),
        },
    )
    return {
        "conversation": conversation.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "compiled_team": compiled.model_dump(mode="json") if compiled else None,
        "comparison": comparison.model_dump(mode="json") if comparison else None,
        "needs_follow_up": needs_follow_up,
    }


@router.post("/conversations/{conversation_id}/compile")
async def compile_conversation(conversation_id: str):
    try:
        conversation, draft, compiled, comparison = await compile_strategy_conversation(
            conversation_id,
            await _runtime_settings(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    AuditLogger.log(
        "strategy",
        "conversation_compiled",
        {"conversation_id": conversation_id, "team_id": compiled.team_id},
    )
    return {
        "conversation": conversation.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "compiled_team": compiled.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
        "validation_report": compiled.validation_report.model_dump(mode="json"),
    }


@router.post("/teams")
async def save_team(payload: SaveTeamRequest):
    version = await save_team_version(
        payload.compiled_team,
        conversation_id=payload.conversation_id,
        label=payload.label,
    )
    AuditLogger.log(
        "strategy",
        "team_saved",
        {
            "conversation_id": payload.conversation_id,
            "team_id": version.team_id,
            "version_number": version.version_number,
        },
    )
    return version.model_dump(mode="json")


@router.get("/teams")
async def get_teams():
    teams = await list_team_versions()
    active = await get_active_team()
    return {
        "teams": [item.model_dump(mode="json") for item in teams],
        "active_team": active.model_dump(mode="json") if active else default_team_version().model_dump(mode="json"),
    }


@router.get("/teams/{team_id}")
async def get_latest_team(team_id: str):
    team = await get_team_version(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team.model_dump(mode="json")


@router.get("/teams/{team_id}/versions/{version_number}")
async def get_versioned_team(team_id: str, version_number: int):
    team = await get_team_version(team_id, version_number)
    if team is None:
        raise HTTPException(status_code=404, detail="Team version not found")
    return team.model_dump(mode="json")


@router.post("/teams/{team_id}/select")
async def select_team(team_id: str, payload: TeamSelectRequest):
    try:
        selected = await select_active_team(team_id, payload.version_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    AuditLogger.log(
        "strategy",
        "team_selected",
        {"team_id": selected.team_id, "version_number": selected.version_number},
    )
    return {"active_team_id": selected.team_id, "active_version_number": selected.version_number}


@router.delete("/teams/{team_id}/versions/{version_number}")
async def delete_team_version_route(team_id: str, version_number: int):
    deleted = await delete_team_version(team_id, version_number)
    if not deleted:
        raise HTTPException(status_code=404, detail="Team version not found")
    AuditLogger.log("strategy", "team_deleted", {"team_id": team_id, "version_number": version_number})
    return {"ok": True}


@router.get("/default-team")
async def get_default_team():
    return default_team_version().model_dump(mode="json")


@router.get("/premade-teams")
async def list_premade_teams():
    catalog = get_catalog()
    return catalog.model_dump(mode="json")


@router.get("/premade-teams/{team_id}")
async def get_premade_team_by_id(team_id: str):
    template = get_premade_team(team_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Premade team '{team_id}' not found")
    return template.model_dump(mode="json")


@router.post("/premade-teams/{team_id}/compile")
async def compile_premade_team(team_id: str):
    template = get_premade_team(team_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Premade team '{team_id}' not found")
    compiled = compile_from_template(template)
    comparison = compare_to_default(compiled)
    AuditLogger.log("strategy", "premade_team_compiled", {"team_id": team_id})
    return {
        "compiled_team": compiled.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
    }


@router.post("/match-team")
async def match_team_endpoint(payload: StrategyPreferences):
    recommendation = match_team(payload)
    return recommendation.model_dump(mode="json")


@router.post("/compare")
async def compare_team(payload: CompareRequest):
    compiled = payload.candidate_compiled_team
    if compiled is None and payload.team_id:
        version = await get_team_version(payload.team_id, payload.version_number)
        if version:
            compiled = version.compiled_team
    if compiled is None:
        raise HTTPException(status_code=400, detail="Provide candidate_compiled_team or team_id")
    return compare_to_default(compiled).model_dump(mode="json")
