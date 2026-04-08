from __future__ import annotations

from uuid import uuid4

import pytest

from backend.llm.studio_patcher import (
    _heuristic_patch_from_instruction,
    _sanitize_generated_patch,
    apply_patch,
    generate_patch_from_nl,
)
from backend.llm.topology_compiler import compile_topology_to_flat_team, validate_topology
from backend.models.agent_team import ArchitectureDraft, ArchitecturePatch, TeamEdge, TeamNode, TeamTopology
from backend.settings.user_settings import default_user_settings


def _make_analysis_node(agent_type: str, weight: int = 60) -> TeamNode:
    return TeamNode(
        node_id=f"node-{agent_type}-{uuid4().hex[:6]}",
        display_name=f"{agent_type.title()} Architect",
        node_family="analysis",
        agent_type=agent_type,
        influence_weight=weight,
        enabled=True,
    )


def _make_base_compiled_team():
    analysis = _make_analysis_node("fundamentals")
    risk = TeamNode(
        node_id=f"node-risk-{uuid4().hex[:6]}",
        display_name="Risk Manager",
        node_family="risk",
        influence_weight=100,
    )
    decision = TeamNode(
        node_id=f"node-decision-{uuid4().hex[:6]}",
        display_name="Portfolio Manager",
        node_family="decision",
        influence_weight=100,
    )
    topology = TeamTopology(
        nodes=[analysis, risk, decision],
        edges=[
            TeamEdge(source_node_id=analysis.node_id, target_node_id=risk.node_id),
            TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
        ],
    )
    draft = ArchitectureDraft(conversation_id="test", topology=topology, proposed_name="Patched Team")
    return compile_topology_to_flat_team(draft)


def test_apply_patch_can_add_debate_node_with_edges():
    compiled = _make_base_compiled_team()
    analysis = next(node for node in compiled.topology.nodes if node.node_family == "analysis")
    risk = next(node for node in compiled.topology.nodes if node.node_family == "risk")

    patch = ArchitecturePatch(
        source_team_id=compiled.team_id,
        source_version_number=compiled.version_number,
        node_changes=[
            {
                "action": "add",
                "node_id": "node-debate-war-room",
                "fields": {
                    "node_family": "debate",
                    "display_name": "War-Room Debate",
                    "role_description": "Cross-examines geopolitical theses before risk sizing.",
                    "influence_weight": 100,
                },
            }
        ],
        edge_changes=[
            {"action": "remove", "source_node_id": analysis.node_id, "target_node_id": risk.node_id},
            {"action": "add", "source_node_id": analysis.node_id, "target_node_id": "node-debate-war-room"},
            {"action": "add", "source_node_id": "node-debate-war-room", "target_node_id": risk.node_id},
        ],
    )

    draft = apply_patch(compiled, patch, default_user_settings())
    validation = validate_topology(draft.topology)

    assert validation.valid, validation.errors
    assert any(node.node_family == "debate" for node in draft.topology.nodes)


def test_apply_patch_can_add_analysis_node_with_custom_prompt_contract():
    compiled = _make_base_compiled_team()
    risk = next(node for node in compiled.topology.nodes if node.node_family == "risk")

    patch = ArchitecturePatch(
        source_team_id=compiled.team_id,
        source_version_number=compiled.version_number,
        node_changes=[
            {
                "action": "add",
                "node_id": "node-macro-war-scorer",
                "fields": {
                    "node_family": "analysis",
                    "agent_type": "macro",
                    "display_name": "Conflict Spillover Scorer",
                    "role_description": "Scores second-order macro spillovers from geopolitical conflict.",
                    "variant_id": "war-spillover-lab",
                    "prompt_contract": {
                        "system_prompt_text": "Model only the spillover regime changes visible in bound macro data.",
                        "allowed_evidence": ["macro.yield_curve", "macro.vix"],
                        "forbidden_inference_rules": ["Do not infer conflict escalation from memory."],
                        "required_output_schema": "AgentSignal",
                        "operator_notes": "Custom authored in test.",
                    },
                },
            }
        ],
        edge_changes=[
            {"action": "add", "source_node_id": "node-macro-war-scorer", "target_node_id": risk.node_id},
        ],
    )

    draft = apply_patch(compiled, patch, default_user_settings())
    validation = validate_topology(draft.topology)

    assert validation.valid, validation.errors
    new_node = next(node for node in draft.topology.nodes if node.node_id == "node-macro-war-scorer")
    assert new_node.prompt_contract is not None
    assert new_node.prompt_contract.system_prompt_text.startswith("Model only the spillover")
    assert len(new_node.capability_bindings) > 0


@pytest.mark.asyncio
async def test_generate_patch_explains_when_topology_missing():
    compiled = _make_base_compiled_team()
    compiled.topology = None

    patch = await generate_patch_from_nl(
        compiled,
        "Increase the weight of fundamentals.",
        default_user_settings(),
    )

    assert "missing its editable topology" in patch.patch_description


def test_heuristic_patch_handles_raise_and_reduce_separately():
    compiled = _make_base_compiled_team()
    technicals = TeamNode(
        node_id=f"node-technicals-{uuid4().hex[:6]}",
        display_name="Technicals",
        node_family="analysis",
        agent_type="technicals",
        influence_weight=55,
        enabled=True,
    )
    sentiment = TeamNode(
        node_id=f"node-sentiment-{uuid4().hex[:6]}",
        display_name="Sentiment",
        node_family="analysis",
        agent_type="sentiment",
        influence_weight=40,
        enabled=True,
    )
    compiled.topology.nodes.extend([technicals, sentiment])

    patch = _heuristic_patch_from_instruction(
        compiled,
        "Increase technicals weight and reduce sentiment",
    )

    assert patch is not None
    changes = {change["node_id"]: change["fields"]["influence_weight"] for change in patch.node_changes}
    assert changes[technicals.node_id] == 70
    assert changes[sentiment.node_id] == 25


def test_sanitize_generated_patch_drops_edge_like_nodes_and_keeps_terminal():
    compiled = _make_base_compiled_team()
    terminal = next(node for node in compiled.topology.nodes if node.node_family == "decision")

    patch = ArchitecturePatch(
        source_team_id=compiled.team_id,
        source_version_number=compiled.version_number,
        node_changes=[
            {
                "action": "add",
                "node_id": "edge-synthesis-fundamentals-connection-0",
                "fields": {
                    "source_node_id": compiled.topology.nodes[0].node_id,
                    "target_node_id": terminal.node_id,
                    "edge_type": "signal",
                },
            },
            {
                "action": "remove",
                "node_id": terminal.node_id,
            },
        ],
    )

    sanitized = _sanitize_generated_patch(compiled, patch)

    assert all(not change["node_id"].startswith("edge-") for change in sanitized.node_changes)
    assert all(change.get("node_id") != terminal.node_id or change.get("action") != "remove" for change in sanitized.node_changes)
    assert any(edge["target_node_id"] == terminal.node_id for edge in sanitized.edge_changes)


@pytest.mark.asyncio
async def test_generate_patch_recovers_from_truncated_llm_json(monkeypatch):
    compiled = _make_base_compiled_team()
    technicals = TeamNode(
        node_id=f"node-technicals-{uuid4().hex[:6]}",
        display_name="Technicals",
        node_family="analysis",
        agent_type="technicals",
        influence_weight=55,
        enabled=True,
    )
    compiled.topology.nodes.append(technicals)
    settings = default_user_settings()
    settings.llm.provider = "ollama"
    settings.llm.model = "gemma4"

    class MockClient:
        provider_name = "ollama"
        available = True

        async def chat(self, **kwargs):
            return """
            {
              "patch_description": "Raise technicals weight.",
              "node_changes": [
                {
                  "action": "update",
                  "node_id": "%s",
                  "fields": {
                    "influence_weight": 80
                  }
                }
            """ % technicals.node_id

    monkeypatch.setattr("backend.llm.studio_patcher.get_llm_client", lambda *_args, **_kwargs: MockClient())

    patch = await generate_patch_from_nl(compiled, "Increase technicals to 80", settings)

    assert "technicals" in patch.patch_description.lower()
    assert patch.node_changes[0]["node_id"] == technicals.node_id
