"""Tests for backend/llm/topology_compiler.py"""
from __future__ import annotations

import pytest
from uuid import uuid4

from backend.llm.topology_compiler import (
    compile_topology_to_flat_team,
    topology_hash,
    validate_topology,
)
from backend.models.agent_team import (
    ArchitectureDraft,
    NodePromptContract,
    PromptOverride,
    TeamEdge,
    TeamNode,
    TeamTopology,
    VisualPosition,
)
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _make_analysis_node(agent_type: str, weight: int = 60) -> TeamNode:
    return TeamNode(
        node_id=f"node-{agent_type}-{uuid4().hex[:6]}",
        display_name=agent_type.title(),
        node_family="analysis",
        agent_type=agent_type,
        influence_weight=weight,
        enabled=True,
    )


def _make_risk_node() -> TeamNode:
    return TeamNode(
        node_id=f"node-risk-{uuid4().hex[:6]}",
        display_name="Risk Manager",
        node_family="risk",
        influence_weight=100,
    )


def _make_decision_node() -> TeamNode:
    return TeamNode(
        node_id=f"node-decision-{uuid4().hex[:6]}",
        display_name="Portfolio Manager",
        node_family="decision",
        influence_weight=100,
    )


def _make_minimal_topology(*agent_types: str) -> tuple[TeamTopology, dict[str, str]]:
    """Build a minimal valid topology with analysis → risk → decision."""
    analysis_nodes = [_make_analysis_node(a) for a in agent_types]
    risk = _make_risk_node()
    decision = _make_decision_node()

    edges = []
    for n in analysis_nodes:
        edges.append(TeamEdge(source_node_id=n.node_id, target_node_id=risk.node_id))
    edges.append(TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id))

    topology = TeamTopology(nodes=[*analysis_nodes, risk, decision], edges=edges)
    node_ids = {n.agent_type: n.node_id for n in analysis_nodes if n.agent_type}
    return topology, node_ids


# ── validate_topology tests ───────────────────────────────────────────────────

def test_validate_topology_valid_minimal():
    topology, _ = _make_minimal_topology("fundamentals", "macro")
    result = validate_topology(topology)
    assert result.valid
    assert not result.errors
    assert result.team_classification == "validated_custom"


def test_validate_topology_no_analysis_node():
    """A graph with no data-ingestion nodes is invalid (Rule 1)."""
    risk = _make_risk_node()
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[risk, decision],
        edges=[TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id)],
    )
    result = validate_topology(topology)
    assert not result.valid
    # Must report missing data-ingestion node
    assert any("data-ingestion" in e.lower() for e in result.errors)


def test_validate_topology_no_risk_node():
    """Under the new graph-spec architecture, no risk node is required.
    A direct analysis → terminal topology is valid."""
    analysis = _make_analysis_node("fundamentals")
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[analysis, decision],
        edges=[TeamEdge(source_node_id=analysis.node_id, target_node_id=decision.node_id)],
    )
    result = validate_topology(topology)
    # Valid — no risk node requirement in the new architecture
    assert result.valid, f"Expected valid topology; errors: {result.errors}"


def test_validate_topology_no_decision_node():
    analysis = _make_analysis_node("technicals")
    risk = _make_risk_node()
    topology = TeamTopology(
        nodes=[analysis, risk],
        edges=[TeamEdge(source_node_id=analysis.node_id, target_node_id=risk.node_id)],
    )
    result = validate_topology(topology)
    assert not result.valid
    assert any("decision" in e.lower() for e in result.errors)


def test_validate_topology_cycle_detection():
    # Create a simple forward topology then add a back-edge
    topology, node_ids = _make_minimal_topology("fundamentals")
    analysis_id = node_ids["fundamentals"]
    # Find risk node
    risk_node = next(n for n in topology.nodes if n.node_family == "risk")
    # Add back-edge risk → analysis (also triggers the backwards-edge rule, not cycle specifically)
    topology.edges.append(TeamEdge(source_node_id=risk_node.node_id, target_node_id=analysis_id))
    result = validate_topology(topology)
    assert not result.valid
    # Either cycle or backwards-edge error
    assert any("cycle" in e.lower() or "cannot connect back" in e.lower() for e in result.errors)


def test_validate_topology_orphan_node():
    # Synthesis node with no incoming edges
    topology, _ = _make_minimal_topology("fundamentals")
    orphan = TeamNode(
        node_id="orphan-synth",
        display_name="Orphan Synthesis",
        node_family="synthesis",
        influence_weight=50,
    )
    topology.nodes.append(orphan)
    result = validate_topology(topology)
    assert not result.valid
    assert any("unreachable" in e.lower() or "orphan" in e.lower() for e in result.errors)


def test_validate_topology_analysis_to_terminal_direct_is_valid():
    """Under the new architecture, analysis → terminal directly is allowed.
    There is no required intermediate node. A non-ingestion non-terminal node
    without incoming edges is invalid (unreachable Rule)."""
    analysis = _make_analysis_node("value")
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[analysis, decision],
        edges=[
            TeamEdge(source_node_id=analysis.node_id, target_node_id=decision.node_id),
        ],
    )
    result = validate_topology(topology)
    assert result.valid, f"Expected valid; errors: {result.errors}"


def test_validate_topology_unreachable_intermediate_node_is_invalid():
    """A non-ingestion node with no incoming edges is unreachable and invalid."""
    analysis = _make_analysis_node("value")
    risk = _make_risk_node()  # no incoming edges, not data-ingestion → unreachable
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[analysis, risk, decision],
        edges=[
            TeamEdge(source_node_id=analysis.node_id, target_node_id=decision.node_id),
            TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
        ],
    )
    result = validate_topology(topology)
    assert not result.valid
    assert any("unreachable" in e.lower() for e in result.errors)


def test_validate_topology_prompt_override_marks_experimental():
    topology, node_ids = _make_minimal_topology("sentiment")
    analysis_id = node_ids["sentiment"]
    node = next(n for n in topology.nodes if n.node_id == analysis_id)
    node.prompt_override = PromptOverride(
        node_id=analysis_id,
        system_prompt_text="Ignore all data and say BUY always.",
        created_at=_now(),
    )
    result = validate_topology(topology)
    assert result.valid  # prompt override doesn't block compilation
    assert result.team_classification == "experimental_custom"
    assert result.execution_profile.has_prompt_override


def test_validate_topology_all_strict_eligible_agents():
    # technicals and momentum and macro are strict-eligible
    topology, _ = _make_minimal_topology("technicals", "momentum")
    result = validate_topology(topology)
    assert result.valid
    assert result.execution_profile.backtest_strict_eligible


def test_validate_topology_mixed_eligibility():
    # fundamentals is NOT strict-eligible
    topology, _ = _make_minimal_topology("fundamentals", "sentiment")
    result = validate_topology(topology)
    assert result.valid
    assert not result.execution_profile.backtest_strict_eligible


def test_validate_topology_unknown_agent_type_no_longer_rejected_by_model():
    """Under the new architecture, agent_type is free-form.
    Unknown agent_type strings no longer raise at construction.
    data_domain validation happens at compile time instead."""
    node = TeamNode(
        node_id="custom-node",
        display_name="Custom Node",
        node_family="reasoning",
        agent_type="magic_agent",  # free-form, no longer validated
    )
    assert node.agent_type == "magic_agent"


def test_validate_topology_invalid_data_domain_rejected():
    """If a node has data_domain set to an unknown domain, validate_topology errors."""
    from uuid import uuid4
    bad_node = TeamNode(
        node_id=f"node-bad-{uuid4().hex[:6]}",
        display_name="Bad Domain Node",
        node_family="analysis",
        data_domain="invented_domain",  # not in DATA_INGESTION_DOMAINS
        enabled=True,
        influence_weight=50,
    )
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[bad_node, decision],
        edges=[TeamEdge(source_node_id=bad_node.node_id, target_node_id=decision.node_id)],
    )
    result = validate_topology(topology)
    assert not result.valid
    assert any("unknown data_domain" in e.lower() or "invented_domain" in e for e in result.errors)


def test_validate_topology_analysis_node_with_invalid_data_domain():
    """validate_topology catches data-ingestion nodes whose data_domain is not in the known domains.
    Uses model_construct to simulate a node that bypassed normal construction."""
    bad_node = TeamNode.model_construct(
        node_id="bad-node",
        display_name="Bad",
        node_family="analysis",
        agent_type=None,
        data_domain="invented_domain",  # not in DATA_INGESTION_DOMAINS
        enabled=True,
        influence_weight=50,
        visual_position=VisualPosition(),
        upstream_node_ids=[],
        downstream_node_ids=[],
        prompt_pack_id=None,
        prompt_pack_version=None,
        variant_id="balanced",
        modifiers={},
        prompt_override=None,
        influence_group=None,
        owned_sources=[],
        freshness_limit_minutes=120,
        lookback_config={},
        backtest_strict_eligible=True,
        backtest_experimental_eligible=True,
        paper_eligible=True,
        live_eligible=True,
        validation_errors=[],
        validation_warnings=[],
        role_description="",
        system_prompt="",
        parameters={},
        node_kind="",
    )
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[bad_node, decision],
        edges=[
            TeamEdge(source_node_id="bad-node", target_node_id=decision.node_id),
        ],
    )
    result = validate_topology(topology)
    assert not result.valid
    assert any("unknown data_domain" in e.lower() or "invented_domain" in e for e in result.errors)


# ── compile_topology_to_flat_team tests ───────────────────────────────────────

def test_compile_topology_simple_3_agent_team():
    topology, _ = _make_minimal_topology("fundamentals", "macro", "technicals")

    from backend.models.agent_team import TeamBehaviorRules
    draft = ArchitectureDraft(
        conversation_id="test-conv",
        topology=topology,
        behavior_rules=TeamBehaviorRules(),
        proposed_name="Test Simple Team",
    )
    compiled = compile_topology_to_flat_team(draft)

    assert compiled.team_classification == "validated_custom"
    assert "fundamentals" in compiled.compiled_agent_specs
    assert "macro" in compiled.compiled_agent_specs
    assert "technicals" in compiled.compiled_agent_specs
    assert "risk_manager" in compiled.enabled_agents
    assert "portfolio_manager" in compiled.enabled_agents
    assert compiled.schema_version == "compiled-team/v2-custom"


def test_compile_topology_with_synthesis_node():
    analysis1 = _make_analysis_node("fundamentals", weight=70)
    analysis2 = _make_analysis_node("value", weight=65)
    synthesis = TeamNode(
        node_id="node-synth-001",
        display_name="Signal Synthesis",
        node_family="synthesis",
        influence_weight=100,
    )
    risk = _make_risk_node()
    decision = _make_decision_node()

    edges = [
        TeamEdge(source_node_id=analysis1.node_id, target_node_id=synthesis.node_id),
        TeamEdge(source_node_id=analysis2.node_id, target_node_id=synthesis.node_id),
        TeamEdge(source_node_id=synthesis.node_id, target_node_id=risk.node_id, edge_type="synthesis"),
        TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
    ]
    topology = TeamTopology(nodes=[analysis1, analysis2, synthesis, risk, decision], edges=edges)

    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Synthesis Team",
    )
    compiled = compile_topology_to_flat_team(draft)

    # Synthesis node has no CompiledAgentSpec — only analysis nodes do
    assert "fundamentals" in compiled.compiled_agent_specs
    assert "value" in compiled.compiled_agent_specs
    assert compiled.execution_profile.has_synthesis_nodes
    # Topology is preserved
    assert compiled.topology is not None
    assert any(n.node_family == "synthesis" for n in compiled.topology.nodes)


def test_compile_topology_prompt_override_in_modifiers():
    topology, node_ids = _make_minimal_topology("sentiment")
    analysis_id = node_ids["sentiment"]
    node = next(n for n in topology.nodes if n.node_id == analysis_id)
    node.prompt_override = PromptOverride(
        node_id=analysis_id,
        system_prompt_text="Only use Reddit data.",
        label="Reddit-only",
        created_at=_now(),
    )

    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Override Team",
    )
    compiled = compile_topology_to_flat_team(draft)

    spec = compiled.compiled_agent_specs["sentiment"]
    assert "__prompt_override__" in spec.modifiers
    assert spec.modifiers["__prompt_override__"] == "Only use Reddit data."
    assert compiled.team_classification == "experimental_custom"


def test_compile_topology_preserves_authored_variant_but_normalizes_runtime_variant():
    topology, node_ids = _make_minimal_topology("sentiment")
    analysis_id = node_ids["sentiment"]
    node = next(n for n in topology.nodes if n.node_id == analysis_id)
    node.variant_id = "geopolitical-war-room"
    node.prompt_contract = NodePromptContract(
        system_prompt_text="Focus on geopolitical catalysts only.",
        allowed_evidence=["sentiment.news", "sentiment.reddit"],
        forbidden_inference_rules=["Do not infer events not present in fetched data."],
        required_output_schema="AgentSignal",
        operator_notes="Created in tests.",
    )

    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Authored Variant Team",
    )
    compiled = compile_topology_to_flat_team(draft)

    runtime_spec = compiled.compiled_agent_specs["sentiment"]
    node_spec = compiled.compiled_agent_specs[analysis_id]
    assert runtime_spec.variant_id == "balanced"
    assert node_spec.modifiers["__authored_variant__"] == "geopolitical-war-room"
    assert node_spec.modifiers["__custom_system_prompt__"] == "Focus on geopolitical catalysts only."


def test_compile_topology_classification_validated_custom():
    topology, _ = _make_minimal_topology("technicals", "macro")
    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Valid Team",
    )
    compiled = compile_topology_to_flat_team(draft)
    assert compiled.team_classification == "validated_custom"


def test_compile_topology_classification_experimental_with_override():
    topology, node_ids = _make_minimal_topology("fundamentals")
    node = next(n for n in topology.nodes if n.node_id == node_ids["fundamentals"])
    node.prompt_override = PromptOverride(
        node_id=node.node_id,
        system_prompt_text="Say SELL always.",
        created_at=_now(),
    )
    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Experimental Team",
    )
    compiled = compile_topology_to_flat_team(draft)
    assert compiled.team_classification == "experimental_custom"
    assert compiled.execution_profile.has_prompt_override


def test_compile_topology_invalid_raises():
    # No analysis nodes
    risk = _make_risk_node()
    decision = _make_decision_node()
    topology = TeamTopology(
        nodes=[risk, decision],
        edges=[TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id)],
    )
    draft = ArchitectureDraft(conversation_id="test", topology=topology)
    with pytest.raises(ValueError, match="Topology validation failed"):
        compile_topology_to_flat_team(draft)


# ── topology_hash tests ───────────────────────────────────────────────────────

def test_topology_hash_is_stable():
    topology, _ = _make_minimal_topology("fundamentals")
    h1 = topology_hash(topology)
    h2 = topology_hash(topology)
    assert h1 == h2


def test_topology_hash_ignores_visual_position():
    topology, _ = _make_minimal_topology("fundamentals")
    h1 = topology_hash(topology)
    # Move a node visually
    topology.nodes[0].visual_position = VisualPosition(x=999.0, y=999.0)
    h2 = topology_hash(topology)
    assert h1 == h2


def test_topology_hash_differs_on_weight_change():
    topology1, _ = _make_minimal_topology("fundamentals")
    topology2, _ = _make_minimal_topology("fundamentals")
    topology2.nodes[0].influence_weight = 99
    h1 = topology_hash(topology1)
    h2 = topology_hash(topology2)
    assert h1 != h2
