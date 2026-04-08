"""
Studio Patcher — generates and applies ArchitecturePatch objects.

Used by the Team Studio when a user requests LLM-assisted refinements
or makes manual structural edits in the visual editor.
"""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
import re

from backend.llm.capability_catalog import bindings_for_agent
from backend.llm.provider import get_llm_client
from backend.llm.topology_compiler import validate_topology
from backend.models.agent_team import (
    ArchitectureDraft,
    ArchitecturePatch,
    CapabilityBinding,
    CompiledTeam,
    NodePromptContract,
    TeamEdge,
    TeamNode,
    TeamTopology,
    VALID_ANALYSIS_AGENTS,
    VisualPosition,
)
from backend.security.input_sanitizer import ContentSource, sanitize
from backend.security.output_validator import parse_llm_json
from backend.settings.user_settings import UserSettings


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()

_ALLOWED_EDGE_TYPES: frozenset[str] = frozenset({"signal", "veto", "gate", "synthesis", "reasoning"})


def _default_prompt_contract(
    *,
    agent_type: str,
    display_name: str,
    role_description: str,
    capability_bindings: list[CapabilityBinding],
) -> NodePromptContract:
    return NodePromptContract(
        system_prompt_text=(
            f"You are {display_name}. {role_description or f'Own the {agent_type} evidence lane.'} "
            "Use only the bound capabilities listed below, cite what you use, and never infer missing facts from memory."
        ),
        allowed_evidence=[binding.capability_id for binding in capability_bindings],
        forbidden_inference_rules=[
            "Do not cite data outside your declared capability bindings.",
            "Do not fabricate external events, prices, filings, or macro facts.",
        ],
        required_output_schema="AgentSignal",
    )


_AGENT_ALIASES: dict[str, tuple[str, ...]] = {
    "fundamentals": ("fundamentals", "fundamental"),
    "technicals": ("technicals", "technical", "technicals agent", "technicals agent"),
    "sentiment": ("sentiment", "news", "reddit"),
    "macro": ("macro", "macroeconomic"),
    "value": ("value",),
    "momentum": ("momentum",),
    "growth": ("growth",),
}


def _is_terminal_node(node: TeamNode) -> bool:
    return bool(node.parameters.get("is_terminal")) or node.node_family == "decision"


def _find_agent_node_ids(compiled_team: CompiledTeam) -> dict[str, str]:
    if compiled_team.topology is None:
        return {}
    result: dict[str, str] = {}
    for node in compiled_team.topology.nodes:
        domain = (node.data_domain or node.agent_type or "").strip().lower()
        if domain in VALID_ANALYSIS_AGENTS and domain not in result:
            result[domain] = node.node_id
    return result


def _extract_requested_weight(fragment: str) -> int | None:
    explicit = re.search(r"\b(?:to|at)\s+(\d{1,3})\b", fragment)
    if explicit:
        return max(0, min(100, int(explicit.group(1))))
    return None


def _heuristic_patch_from_instruction(
    compiled_team: CompiledTeam,
    instruction: str,
) -> ArchitecturePatch | None:
    if compiled_team.topology is None:
        return None

    normalized = re.sub(r"[^a-z0-9\s%-]+", " ", instruction.lower())
    node_ids = _find_agent_node_ids(compiled_team)
    current_nodes = {node.node_id: node for node in compiled_team.topology.nodes}
    node_changes: list[dict] = []
    summaries: list[str] = []
    clauses = [fragment.strip() for fragment in re.split(r"\b(?:and|then)\b|,", normalized) if fragment.strip()]

    for clause in clauses:
        for agent_name, aliases in _AGENT_ALIASES.items():
            if not any(re.search(rf"\b{re.escape(alias)}\b", clause) for alias in aliases):
                continue
            node_id = node_ids.get(agent_name)
            if not node_id:
                continue
            node = current_nodes[node_id]
            target_weight = _extract_requested_weight(clause)

            if re.search(r"\b(disable|turn off|deactivate|mute)\b", clause):
                node_changes.append({"action": "update", "node_id": node_id, "fields": {"enabled": False}})
                summaries.append(f"Disabled {agent_name}.")
                continue

            if re.search(r"\b(enable|turn on|reactivate)\b", clause):
                node_changes.append({"action": "update", "node_id": node_id, "fields": {"enabled": True}})
                summaries.append(f"Enabled {agent_name}.")
                continue

            if re.search(r"\b(increase|raise|boost|upweight|more)\b", clause):
                next_weight = target_weight if target_weight is not None else min(100, node.influence_weight + 15)
                node_changes.append({"action": "update", "node_id": node_id, "fields": {"influence_weight": next_weight}})
                summaries.append(f"Raised {agent_name} weight to {next_weight}.")
                continue

            if re.search(r"\b(decrease|reduce|lower|downweight|less)\b", clause):
                next_weight = target_weight if target_weight is not None else max(0, node.influence_weight - 15)
                node_changes.append({"action": "update", "node_id": node_id, "fields": {"influence_weight": next_weight}})
                summaries.append(f"Lowered {agent_name} weight to {next_weight}.")
                continue

    rename_match = re.search(r"\brename team to\s+([a-z0-9 _-]{3,80})\b", normalized)
    behavior_changes: list[dict] = []
    if rename_match:
        summaries.append(f"Rename request noted for '{rename_match.group(1).strip()}'.")

    if not node_changes and not behavior_changes:
        return None

    return ArchitecturePatch(
        source_team_id=compiled_team.team_id,
        source_version_number=compiled_team.version_number,
        patch_description=" ".join(summaries),
        node_changes=node_changes,
        behavior_changes=behavior_changes,
        requires_recompile=True,
        user_confirmed=False,
        created_at=_now_iso(),
    )


def _sanitize_generated_patch(
    compiled_team: CompiledTeam,
    patch: ArchitecturePatch,
) -> ArchitecturePatch:
    if compiled_team.topology is None:
        return patch

    terminal_node_ids = {node.node_id for node in compiled_team.topology.nodes if _is_terminal_node(node)}
    sanitized_node_changes: list[dict] = []
    sanitized_edge_changes: list[dict] = []

    # Normalize edge changes first (the model sometimes uses edge_type="input" or uses "type" key).
    for change in patch.edge_changes:
        if not isinstance(change, dict):
            continue
        normalized = dict(change)
        if "edge_type" not in normalized and "type" in normalized:
            normalized["edge_type"] = normalized.get("type")
        raw_edge_type = str(normalized.get("edge_type", "signal")).strip().lower()
        normalized["edge_type"] = raw_edge_type if raw_edge_type in _ALLOWED_EDGE_TYPES else "signal"
        sanitized_edge_changes.append(normalized)

    for change in patch.node_changes:
        action = str(change.get("action", "update")).lower()
        node_id = str(change.get("node_id", "")).strip()
        fields = change.get("fields") if isinstance(change.get("fields"), dict) else None
        if not fields:
            fields = {k: v for k, v in change.items() if k not in {"action", "node_id"}}

        if node_id.startswith("edge-") or {"source_node_id", "target_node_id"} & set(fields):
            src = fields.get("source_node_id") or change.get("source_node_id")
            tgt = fields.get("target_node_id") or change.get("target_node_id")
            if src and tgt:
                raw_edge_type = str(fields.get("edge_type", change.get("edge_type", "signal"))).strip().lower()
                edge_type = raw_edge_type if raw_edge_type in _ALLOWED_EDGE_TYPES else "signal"
                sanitized_edge_changes.append(
                    {
                        "action": "remove" if action == "remove" else "add",
                        "source_node_id": src,
                        "target_node_id": tgt,
                        "edge_type": edge_type,
                    }
                )
            continue

        if action == "remove" and node_id in terminal_node_ids:
            continue

        if action == "update" and node_id in terminal_node_ids and isinstance(fields, dict):
            fields = dict(fields)
            if fields.get("node_family") and fields.get("node_family") != "decision":
                fields.pop("node_family", None)
            if "parameters" in fields and isinstance(fields["parameters"], dict):
                fields["parameters"] = {**fields["parameters"], "is_terminal": True}
            elif "parameters" not in fields:
                fields["parameters"] = {"is_terminal": True}
            change = {"action": action, "node_id": node_id, "fields": fields}

        sanitized_node_changes.append(change)

    return patch.model_copy(
        update={
            "node_changes": sanitized_node_changes,
            "edge_changes": sanitized_edge_changes,
        }
    )


async def generate_patch_from_nl(
    compiled_team: CompiledTeam,
    instruction: str,
    user_settings: UserSettings,
) -> ArchitecturePatch:
    """
    Generate an ArchitecturePatch from a natural-language instruction.

    The patch is unconfirmed — it must be applied via apply_patch()
    after the user reviews and approves it.
    """
    sanitized = sanitize(instruction, ContentSource.USER_STRATEGY_INPUT)
    safe_instruction = sanitized.sanitized_text

    heuristic_patch = _heuristic_patch_from_instruction(compiled_team, safe_instruction)
    if heuristic_patch is not None:
        return heuristic_patch

    if compiled_team.topology is None:
        return ArchitecturePatch(
            source_team_id=compiled_team.team_id,
            source_version_number=compiled_team.version_number,
            patch_description=(
                "This team is missing its editable topology, so AI Refine cannot modify it yet. "
                "Recompile the team in Studio and try again."
            ),
            requires_recompile=False,
            created_at=_now_iso(),
        )

    client = get_llm_client(user_settings.llm)
    if not client.available and client.provider_name != "ollama":
        return ArchitecturePatch(
            source_team_id=compiled_team.team_id,
            source_version_number=compiled_team.version_number,
            patch_description=(
                f"LLM provider '{client.provider_name}' is not configured for AI Refine. "
                "Update Settings -> LLM or switch to Ollama, then try again."
            ),
            requires_recompile=False,
            created_at=_now_iso(),
        )

    from backend.llm.budget import BudgetTracker

    budget = BudgetTracker(
        max_cost_usd=user_settings.llm.max_cost_per_session_usd,
        max_tokens=user_settings.llm.max_tokens_per_request,
    )

    system = (
        "You are a team architecture editor for a graph-spec investment agent system. "
        "Given the current topology and an instruction, propose a structured patch. "
        "Return JSON with these fields: "
        "patch_description (str), "
        "node_changes (list of {action: 'add'|'update'|'remove', node_id, fields?}), "
        "edge_changes (list of {action: 'add'|'remove', source_node_id, target_node_id, edge_type?}), "
        "behavior_changes (list of {field, old_value, new_value}), "
        "requires_recompile (bool). "
        "\n\nNode families in this system:\n"
        "- data_ingestion: fetches market data. Has data_domain (one of: fundamentals, technicals, sentiment, macro, value, momentum, growth) and system_prompt.\n"
        "- reasoning: custom analysis/synthesis nodes. Has system_prompt (required), parameters (temperature, max_tokens, output_schema, input_merge, is_terminal).\n"
        "- output: the single terminal node that produces a PortfolioDecision. Has system_prompt and parameters.is_terminal=true.\n"
        "\nFor node action='update', fields may include: "
        "display_name, role_description, system_prompt, node_kind, influence_weight, "
        "enabled, variant_id, data_domain, parameters, freshness_limit_minutes. "
        "Set system_prompt to update a node's instructions entirely. "
        "Set parameters as a dict to update runtime settings (e.g. {\"temperature\": 0.4}). "
        "\nFor node action='add', required fields: node_family, display_name. "
        "data_ingestion nodes also need data_domain. reasoning/output nodes need system_prompt. "
        "Whenever you add a node, also add edges so the graph stays reachable. "
        "\nGraph rules: must remain a DAG, exactly one terminal node (output family), "
        "at least one data_ingestion node. "
        "Do NOT add prompt_override fields. "
        "If the change is unclear, set requires_recompile=false and explain in patch_description."
    )

    topology_summary = {
        "nodes": [
            {
                "node_id": n.node_id,
                "display_name": n.display_name,
                "node_family": n.node_family,
                "data_domain": n.data_domain,
                "node_kind": n.node_kind,
                "system_prompt": n.system_prompt or "",
                "parameters": n.parameters,
                "enabled": n.enabled,
                "influence_weight": n.influence_weight,
            }
            for n in compiled_team.topology.nodes
        ],
        "edges": [
            {"source": e.source_node_id, "target": e.target_node_id, "type": e.edge_type}
            for e in compiled_team.topology.edges
        ],
    }

    user_payload = json.dumps({
        "topology": topology_summary,
        "instruction": safe_instruction,
        "team_name": compiled_team.name,
        "risk_level": compiled_team.risk_level,
        "time_horizon": compiled_team.time_horizon,
        "data_ingestion_domains": sorted(VALID_ANALYSIS_AGENTS),
    }, indent=2)

    from pydantic import BaseModel as _BaseModel

    class _PatchResponseSchema(_BaseModel):
        patch_description: str = ""
        node_changes: list[dict] = []
        edge_changes: list[dict] = []
        behavior_changes: list[dict] = []
        requires_recompile: bool = True

    try:
        async with asyncio.timeout(120.0):
            raw = await client.chat(
                system=system,
                messages=[{"role": "user", "content": user_payload}],
                max_tokens=min(2000, user_settings.llm.max_tokens_per_request),
                temperature=user_settings.llm.temperature_strategy,
                budget=budget,
            )
        parsed = parse_llm_json(raw, _PatchResponseSchema, allow_partial=True)
        patch = _sanitize_generated_patch(
            compiled_team,
            ArchitecturePatch(
                source_team_id=compiled_team.team_id,
                source_version_number=compiled_team.version_number,
                patch_description=parsed.patch_description,
                node_changes=parsed.node_changes,
                edge_changes=parsed.edge_changes,
                behavior_changes=parsed.behavior_changes,
                requires_recompile=parsed.requires_recompile,
                user_confirmed=False,
                created_at=_now_iso(),
            ),
        )
        preview_draft = apply_patch(compiled_team, patch, user_settings)
        preview_validation = validate_topology(preview_draft.topology)
        if preview_validation.valid:
            return patch

        repair_system = (
            system
            + " Your first patch produced an invalid topology. Repair it so the graph is acyclic, "
            "all non-ingestion source nodes are gone, and exactly one terminal node exists."
        )
        repair_payload = json.dumps({
            "topology": topology_summary,
            "instruction": safe_instruction,
            "previous_patch": patch.model_dump(mode="json"),
            "validation_errors": preview_validation.errors,
        }, indent=2)
        async with asyncio.timeout(120.0):
            repair_raw = await client.chat(
                system=repair_system,
                messages=[{"role": "user", "content": repair_payload}],
                max_tokens=min(2000, user_settings.llm.max_tokens_per_request),
                temperature=user_settings.llm.temperature_strategy,
                budget=budget,
            )
        repaired = parse_llm_json(repair_raw, _PatchResponseSchema, allow_partial=True)
        repaired_patch = _sanitize_generated_patch(
            compiled_team,
            ArchitecturePatch(
                source_team_id=compiled_team.team_id,
                source_version_number=compiled_team.version_number,
                patch_description=repaired.patch_description,
                node_changes=repaired.node_changes,
                edge_changes=repaired.edge_changes,
                behavior_changes=repaired.behavior_changes,
                requires_recompile=repaired.requires_recompile,
                user_confirmed=False,
                created_at=_now_iso(),
            ),
        )
        repaired_draft = apply_patch(compiled_team, repaired_patch, user_settings)
        repaired_validation = validate_topology(repaired_draft.topology)
        if repaired_validation.valid:
            return repaired_patch

        heuristic_repair = _heuristic_patch_from_instruction(compiled_team, safe_instruction)
        if heuristic_repair is not None:
            heuristic_preview = apply_patch(compiled_team, heuristic_repair, user_settings)
            heuristic_validation = validate_topology(heuristic_preview.topology)
            if heuristic_validation.valid:
                return heuristic_repair

        return ArchitecturePatch(
            source_team_id=compiled_team.team_id,
            source_version_number=compiled_team.version_number,
            patch_description=(
                "Could not produce a valid refinement patch. Validation errors: "
                + "; ".join(repaired_validation.errors[:4])
            ),
            requires_recompile=False,
            created_at=_now_iso(),
        )
    except TimeoutError:
        return ArchitecturePatch(
            source_team_id=compiled_team.team_id,
            source_version_number=compiled_team.version_number,
            patch_description="Patch generation timed out. The LLM took too long to respond. Please try a simpler instruction.",
            requires_recompile=False,
            created_at=_now_iso(),
        )
    except Exception as exc:
        return ArchitecturePatch(
            source_team_id=compiled_team.team_id,
            source_version_number=compiled_team.version_number,
            patch_description=f"Could not generate patch: {str(exc) or type(exc).__name__}",
            requires_recompile=False,
            created_at=_now_iso(),
        )


def apply_patch(
    compiled_team: CompiledTeam,
    patch: ArchitecturePatch,
    user_settings: UserSettings | None = None,
) -> ArchitectureDraft:
    """
    Apply a confirmed ArchitecturePatch to a CompiledTeam's topology,
    returning an ArchitectureDraft ready for recompilation.

    Deep-copies the topology to preserve immutability of the source team.
    """
    if compiled_team.topology is None:
        raise ValueError("Cannot apply patch to a team with no topology (premade teams are not editable via studio).")

    topology = deepcopy(compiled_team.topology)
    nodes_by_id = {n.node_id: n for n in topology.nodes}

    settings = user_settings or UserSettings()

    # Apply node changes
    _ALLOWED_NODE_FIELDS = {
        "node_family",
        "agent_type",
        "display_name",
        "role_description",
        "influence_weight",
        "variant_id",
        "enabled",
        "modifiers",
        "prompt_contract",
        "visual_position",
        "freshness_limit_minutes",
        # Graph-spec fields
        "system_prompt",
        "parameters",
        "data_domain",
        "node_kind",
    }
    _CHANGE_META_KEYS = {"action", "node_id"}
    for change in patch.node_changes:
        action = str(change.get("action", "update")).lower()
        node_id = change.get("node_id")
        if not node_id:
            continue
        # Accept fields either nested under "fields" key OR spread at the top level of the change dict
        if isinstance(change.get("fields"), dict):
            fields: dict | None = change["fields"]
        else:
            top_level = {k: v for k, v in change.items() if k not in _CHANGE_META_KEYS}
            fields = top_level if top_level else None
        if action == "remove":
            node = nodes_by_id.pop(node_id, None)
            if node is None:
                continue
            topology.nodes = [item for item in topology.nodes if item.node_id != node_id]
            topology.edges = [
                edge
                for edge in topology.edges
                if edge.source_node_id != node_id and edge.target_node_id != node_id
            ]
            continue
        if action == "add":
            if not fields:
                continue
            node_family = str(fields.get("node_family", "reasoning"))
            agent_type = fields.get("agent_type")
            display_name = str(fields.get("display_name", node_id)).strip()[:80] or str(node_id)
            role_description = str(fields.get("role_description", "")).strip()[:200]
            influence_weight = int(fields.get("influence_weight", 50))
            variant_id = str(fields.get("variant_id", "balanced")).strip() or "balanced"
            modifiers = fields.get("modifiers", {}) if isinstance(fields.get("modifiers"), dict) else {}
            visual_position = fields.get("visual_position", {}) if isinstance(fields.get("visual_position"), dict) else {}
            # Graph-spec fields for new nodes
            data_domain = fields.get("data_domain")
            system_prompt = str(fields.get("system_prompt", "")).strip()
            parameters = fields.get("parameters", {}) if isinstance(fields.get("parameters"), dict) else {}
            node_kind = str(fields.get("node_kind", "")).strip()
            is_ingestion = node_family in ("data_ingestion", "analysis") or bool(data_domain)
            capability_bindings = (
                bindings_for_agent(str(data_domain or agent_type), settings)
                if is_ingestion and isinstance(data_domain or agent_type, str)
                else []
            )
            prompt_contract_payload = fields.get("prompt_contract")
            if isinstance(prompt_contract_payload, dict):
                prompt_contract = NodePromptContract.model_validate(prompt_contract_payload)
            elif is_ingestion and isinstance(agent_type or data_domain, str):
                effective_type = str(data_domain or agent_type)
                prompt_contract = _default_prompt_contract(
                    agent_type=effective_type,
                    display_name=display_name,
                    role_description=role_description,
                    capability_bindings=capability_bindings,
                )
            else:
                prompt_contract = None
            new_node = TeamNode(
                node_id=str(node_id),
                display_name=display_name,
                node_family=node_family,
                agent_type=str(agent_type) if isinstance(agent_type, str) and agent_type else None,
                data_domain=str(data_domain) if isinstance(data_domain, str) and data_domain else None,
                system_prompt=system_prompt,
                parameters=parameters,
                node_kind=node_kind,
                role_description=role_description,
                enabled=bool(fields.get("enabled", True)),
                visual_position=VisualPosition(
                    x=float(visual_position.get("x", 240.0)),
                    y=float(visual_position.get("y", 180.0)),
                ),
                influence_weight=max(0, min(100, influence_weight)),
                variant_id=variant_id,
                modifiers=modifiers,
                prompt_contract=prompt_contract,
                capability_bindings=capability_bindings,
                freshness_limit_minutes=max(1, int(fields.get("freshness_limit_minutes", 120))),
            )
            topology.nodes.append(new_node)
            nodes_by_id[new_node.node_id] = new_node
            continue

        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        if not fields:
            continue
        for field, new_value in fields.items():
            if field not in _ALLOWED_NODE_FIELDS:
                continue
            if field == "influence_weight" and isinstance(new_value, (int, float)):
                node.influence_weight = max(0, min(100, int(new_value)))
            elif field == "variant_id" and isinstance(new_value, str):
                node.variant_id = new_value
            elif field == "enabled" and isinstance(new_value, bool):
                node.enabled = new_value
            elif field == "modifiers" and isinstance(new_value, dict):
                node.modifiers.update(new_value)
            elif field == "display_name" and isinstance(new_value, str):
                node.display_name = new_value[:80]
            elif field == "role_description" and isinstance(new_value, str):
                node.role_description = new_value[:200]
            elif field == "freshness_limit_minutes" and isinstance(new_value, (int, float)):
                node.freshness_limit_minutes = max(1, int(new_value))
            elif field == "prompt_contract" and isinstance(new_value, dict):
                node.prompt_contract = NodePromptContract.model_validate(new_value)
            elif field == "visual_position" and isinstance(new_value, dict):
                node.visual_position = VisualPosition(
                    x=float(new_value.get("x", node.visual_position.x)),
                    y=float(new_value.get("y", node.visual_position.y)),
                )
            elif field == "agent_type" and isinstance(new_value, str):
                node.agent_type = new_value
                if node.node_family == "analysis":
                    node.capability_bindings = bindings_for_agent(new_value, settings)
                    if node.prompt_contract is None:
                        node.prompt_contract = _default_prompt_contract(
                            agent_type=new_value,
                            display_name=node.display_name,
                            role_description=node.role_description,
                            capability_bindings=node.capability_bindings,
                        )
            elif field == "node_family" and isinstance(new_value, str):
                node.node_family = new_value
            elif field == "system_prompt" and isinstance(new_value, str):
                node.system_prompt = new_value
            elif field == "node_kind" and isinstance(new_value, str):
                node.node_kind = new_value
            elif field == "data_domain" and (new_value is None or isinstance(new_value, str)):
                node.data_domain = new_value or None
                if node.data_domain:
                    node.capability_bindings = bindings_for_agent(node.data_domain, settings)
            elif field == "parameters" and isinstance(new_value, dict):
                # Merge parameters so partial updates (e.g. just temperature) work
                node.parameters = {**node.parameters, **new_value}

    # Apply edge changes
    for change in patch.edge_changes:
        action = change.get("action")
        src = change.get("source_node_id")
        tgt = change.get("target_node_id")
        if action == "remove" and src and tgt:
            topology.edges = [
                e for e in topology.edges
                if not (e.source_node_id == src and e.target_node_id == tgt)
            ]
        elif action == "add" and src and tgt:
            if src in nodes_by_id and tgt in nodes_by_id:
                raw_edge_type = str(change.get("edge_type", "signal")).strip().lower()
                edge_type = raw_edge_type if raw_edge_type in _ALLOWED_EDGE_TYPES else "signal"
                new_edge = TeamEdge(
                    source_node_id=src,
                    target_node_id=tgt,
                    edge_type=edge_type,
                )
                topology.edges.append(new_edge)

    # Apply behavior changes
    behavior_rules = deepcopy(compiled_team.behavior_rules) if compiled_team.behavior_rules else None
    from backend.models.agent_team import TeamBehaviorRules
    if behavior_rules is None:
        behavior_rules = TeamBehaviorRules()

    for change in patch.behavior_changes:
        field = change.get("field")
        new_value = change.get("new_value")
        if field == "debate_enabled" and isinstance(new_value, bool):
            behavior_rules.debate_enabled = new_value
        elif field == "min_confidence_threshold" and isinstance(new_value, (int, float)):
            behavior_rules.min_confidence_threshold = max(0.0, min(1.0, float(new_value)))

    # Reconstruct draft for recompilation
    from backend.models.agent_team import ArchitectureIntent
    intent = ArchitectureIntent(
        risk_level=compiled_team.risk_level,
        time_horizon=compiled_team.time_horizon,
        asset_universe=compiled_team.asset_universe,
        sector_exclusions=compiled_team.sector_exclusions,
    )

    draft = ArchitectureDraft(
        conversation_id="",
        intent=intent,
        topology=topology,
        behavior_rules=behavior_rules,
        rationale=f"Patched from team {compiled_team.team_id} v{compiled_team.version_number}: {patch.patch_description}",
        proposed_name=compiled_team.name,
        proposed_description=compiled_team.description,
    )
    return draft
