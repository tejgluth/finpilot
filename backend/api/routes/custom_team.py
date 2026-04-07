"""
Custom Team API Routes — /api/strategy/custom/

All routes for the custom team conversation builder, topology validator,
patch generation/application, and team saving.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.llm.custom_team_builder import (
    compile_custom_conversation,
    create_custom_conversation,
    get_custom_conversation,
    list_custom_conversations,
    process_custom_message,
)
from backend.llm.studio_patcher import apply_patch, generate_patch_from_nl
from backend.llm.strategy_builder import save_team_version
from backend.llm.topology_compiler import (
    compile_topology_to_flat_team,
    validate_topology,
)
from backend.models.agent_team import (
    ArchitectureIntent,
    ArchitecturePatch,
    CompiledTeam,
    CustomConversation,
    TeamTopology,
    TeamValidationResult,
    TeamVersion,
)
from backend.security.audit_logger import AuditLogger
from backend.settings.user_settings import UserSettings, default_user_settings
from backend.database import load_state

router = APIRouter()


async def _get_settings() -> UserSettings:
    data = await load_state("user_settings", None)
    if data:
        return UserSettings.from_dict(data)
    return default_user_settings()


# ── Request / Response models ──────────────────────────────────────────────────

class StartCustomConversationRequest(BaseModel):
    seed_prompt: str | None = None


class CustomMessageRequest(BaseModel):
    content: str
    request_compile: bool = False


class SaveCustomTeamRequest(BaseModel):
    conversation_id: str | None = None
    compiled_team: CompiledTeam
    label: str = "Custom Team"


class ApplyPatchRequest(BaseModel):
    source_team_id: str
    source_version_number: int | None = None
    patch: ArchitecturePatch
    label: str = "Studio Edit"
    # If provided, use this directly instead of looking up from the database.
    # Enables patching unsaved in-memory compiled teams.
    compiled_team: CompiledTeam | None = None


class NLPatchRequest(BaseModel):
    source_team_id: str
    source_version_number: int | None = None
    instruction: str
    # If provided, use this directly instead of looking up from the database.
    # Enables refining unsaved in-memory compiled teams.
    compiled_team: CompiledTeam | None = None


class ValidateTopologyRequest(BaseModel):
    topology: TeamTopology
    intent: ArchitectureIntent | None = None


class CompileTopologyRequest(BaseModel):
    topology: TeamTopology
    intent: ArchitectureIntent | None = None
    proposed_name: str = "Custom Team"
    proposed_description: str = ""


# ── Conversations ──────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=CustomConversation)
async def start_custom_conversation(
    payload: StartCustomConversationRequest,
    settings: UserSettings = Depends(_get_settings),
) -> CustomConversation:
    conv = await create_custom_conversation(settings, seed_prompt=payload.seed_prompt)
    AuditLogger.log("user", "custom_conversation_started", {
        "conversation_id": conv.conversation_id,
        "has_seed_prompt": bool(payload.seed_prompt),
    })
    return conv


@router.get("/conversations", response_model=dict)
async def list_custom_conversations_route() -> dict:
    convs = await list_custom_conversations()
    return {"conversations": [c.model_dump(mode="json") for c in convs]}


@router.get("/conversations/{conversation_id}", response_model=CustomConversation)
async def get_custom_conversation_route(conversation_id: str) -> CustomConversation:
    conv = await get_custom_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Custom conversation not found: {conversation_id}")
    return conv


@router.post("/conversations/{conversation_id}/messages", response_model=dict)
async def send_custom_message(
    conversation_id: str,
    payload: CustomMessageRequest,
    settings: UserSettings = Depends(_get_settings),
) -> dict:
    try:
        conv, draft, compiled, needs_follow_up = await process_custom_message(
            conversation_id=conversation_id,
            content=payload.content,
            request_compile=payload.request_compile,
            user_settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    AuditLogger.log("user", "custom_conversation_message", {
        "conversation_id": conversation_id,
        "needs_follow_up": needs_follow_up,
        "has_compiled_team": compiled is not None,
    })

    return {
        "conversation": conv.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "compiled_team": compiled.model_dump(mode="json") if compiled else None,
        "needs_follow_up": needs_follow_up,
        "assistant_message": conv.latest_turn.assistant_message,
        "resolved_requirements": [item.model_dump(mode="json") for item in conv.latest_turn.resolved_requirements],
        "open_questions": [item.model_dump(mode="json") for item in conv.latest_turn.open_questions],
        "graph_change_summary": conv.latest_turn.graph_change_summary,
        "capability_gaps": [item.model_dump(mode="json") for item in conv.latest_turn.capability_gaps],
        "mode_compatibility": conv.latest_turn.mode_compatibility.model_dump(mode="json"),
        "validation_state": conv.latest_turn.validation_state.model_dump(mode="json") if conv.latest_turn.validation_state else None,
    }


@router.post("/conversations/{conversation_id}/compile", response_model=dict)
async def compile_custom_conversation_route(
    conversation_id: str,
    settings: UserSettings = Depends(_get_settings),
) -> dict:
    try:
        conv, draft, compiled = await compile_custom_conversation(conversation_id, settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    validation_result = validate_topology(draft.topology)

    AuditLogger.log("user", "custom_team_compiled", {
        "conversation_id": conversation_id,
        "team_classification": compiled.team_classification,
        "valid": validation_result.valid,
    })

    return {
        "conversation": conv.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "compiled_team": compiled.model_dump(mode="json"),
        "validation_result": validation_result.model_dump(mode="json"),
        "assistant_message": conv.latest_turn.assistant_message,
        "resolved_requirements": [item.model_dump(mode="json") for item in conv.latest_turn.resolved_requirements],
        "open_questions": [item.model_dump(mode="json") for item in conv.latest_turn.open_questions],
        "graph_change_summary": conv.latest_turn.graph_change_summary,
        "capability_gaps": [item.model_dump(mode="json") for item in conv.latest_turn.capability_gaps],
        "mode_compatibility": conv.latest_turn.mode_compatibility.model_dump(mode="json"),
        "validation_state": conv.latest_turn.validation_state.model_dump(mode="json") if conv.latest_turn.validation_state else None,
    }


# ── Topology validation & compilation ─────────────────────────────────────────

@router.post("/validate-topology", response_model=TeamValidationResult)
async def validate_topology_route(payload: ValidateTopologyRequest) -> TeamValidationResult:
    return validate_topology(payload.topology)


@router.post("/compile-topology", response_model=dict)
async def compile_topology_route(
    payload: CompileTopologyRequest,
    settings: UserSettings = Depends(_get_settings),
) -> dict:
    from backend.models.agent_team import ArchitectureDraft

    intent = payload.intent or ArchitectureIntent()
    draft = ArchitectureDraft(
        conversation_id="",
        intent=intent,
        topology=payload.topology,
        proposed_name=payload.proposed_name,
        proposed_description=payload.proposed_description,
    )
    try:
        compiled = compile_topology_to_flat_team(draft, intent.to_strategy_preferences())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "compiled_team": compiled.model_dump(mode="json"),
        "validation_result": validate_topology(payload.topology).model_dump(mode="json"),
    }


# ── Team saving ────────────────────────────────────────────────────────────────

@router.post("/teams", response_model=dict)
async def save_custom_team(payload: SaveCustomTeamRequest) -> dict:
    try:
        version = await save_team_version(
            payload.compiled_team,
            conversation_id=payload.conversation_id,
            label=payload.label,
            creation_source="custom_conversation",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    AuditLogger.log("user", "custom_team_saved", {
        "team_id": version.team_id,
        "version_number": version.version_number,
        "team_classification": version.team_classification,
        "prompt_override_present": version.prompt_override_present,
    })

    return {"team_version": version.model_dump(mode="json")}


# ── Studio patch ───────────────────────────────────────────────────────────────

@router.post("/patch/generate", response_model=ArchitecturePatch)
async def generate_patch_route(
    payload: NLPatchRequest,
    settings: UserSettings = Depends(_get_settings),
) -> ArchitecturePatch:
    if payload.compiled_team is not None:
        compiled = payload.compiled_team
    else:
        from backend.llm.strategy_builder import get_team_version
        version = await get_team_version(payload.source_team_id, payload.source_version_number)
        if version is None:
            raise HTTPException(status_code=404, detail=f"Team not found: {payload.source_team_id}")
        compiled = version.compiled_team

    patch = await generate_patch_from_nl(compiled, payload.instruction, settings)

    AuditLogger.log("user", "studio_patch_generated", {
        "team_id": payload.source_team_id,
        "patch_id": patch.patch_id,
        "instruction_len": len(payload.instruction),
    })

    return patch


@router.post("/patch/apply", response_model=dict)
async def apply_patch_route(
    payload: ApplyPatchRequest,
    settings: UserSettings = Depends(_get_settings),
) -> dict:
    if payload.compiled_team is not None:
        base_team = payload.compiled_team
    else:
        from backend.llm.strategy_builder import get_team_version
        version = await get_team_version(payload.source_team_id, payload.source_version_number)
        if version is None:
            raise HTTPException(status_code=404, detail=f"Team not found: {payload.source_team_id}")
        base_team = version.compiled_team

    try:
        draft = apply_patch(base_team, payload.patch, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        compiled = compile_topology_to_flat_team(draft)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Patch produced invalid topology: {exc}")

    validation_result = validate_topology(draft.topology)

    AuditLogger.log("user", "studio_patch_applied", {
        "source_team_id": payload.source_team_id,
        "patch_id": payload.patch.patch_id,
        "team_classification": compiled.team_classification,
    })

    return {
        "compiled_team": compiled.model_dump(mode="json"),
        "validation_result": validation_result.model_dump(mode="json"),
    }
