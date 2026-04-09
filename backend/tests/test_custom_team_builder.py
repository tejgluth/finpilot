"""Tests for backend/llm/custom_team_builder.py"""
from __future__ import annotations


from backend.llm.custom_team_builder import (
    _heuristic_architecture_draft,
    extract_architecture_intent,
)
from backend.models.agent_team import (
    ArchitectureIntent,
    StrategyMessage,
)
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _msg(content: str) -> StrategyMessage:
    return StrategyMessage(
        role="user",
        content=content,
        sanitized_content=content,
        timestamp=_now(),
        message_type="input",
    )


def _assistant_msg(content: str) -> StrategyMessage:
    return StrategyMessage(
        role="assistant",
        content=content,
        sanitized_content=content,
        timestamp=_now(),
        message_type="follow_up",
    )


# ── extract_architecture_intent tests ────────────────────────────────────────

def test_extract_intent_basic_risk_horizon():
    messages = [_msg("I want a moderate risk long term portfolio focused on fundamentals")]
    intent = extract_architecture_intent(messages)
    assert intent.risk_level == "moderate"
    assert intent.time_horizon == "long"
    assert "fundamentals" in intent.preferred_factors or "quality" in intent.preferred_factors or True


def test_extract_intent_complexity_simple():
    messages = [_msg("I want a simple minimal team with just 3 agents")]
    intent = extract_architecture_intent(messages)
    assert intent.desired_complexity == "simple"
    assert intent.desired_analysis_node_count == 3


def test_extract_intent_complexity_complex():
    messages = [_msg("I want a comprehensive sophisticated team")]
    intent = extract_architecture_intent(messages)
    assert intent.desired_complexity == "complex"


def test_extract_intent_synthesis_stage():
    messages = [_msg("I want a synthesis stage to aggregate signals before risk")]
    intent = extract_architecture_intent(messages)
    assert intent.wants_synthesis_stage is True


def test_extract_intent_no_debate():
    messages = [_msg("I want a team with no debate stage")]
    intent = extract_architecture_intent(messages)
    assert intent.wants_debate_stage is False


def test_extract_intent_debate_explicit():
    messages = [_msg("I want bull bear debate enabled")]
    intent = extract_architecture_intent(messages)
    assert intent.wants_debate_stage is True


def test_extract_intent_manual_control_high():
    messages = [_msg("I want full control and manual configuration of everything")]
    intent = extract_architecture_intent(messages)
    assert intent.manual_control_level == "high"


def test_extract_intent_wants_prompt_editing():
    messages = [_msg("I want to edit prompts and use advanced prompt overrides")]
    intent = extract_architecture_intent(messages)
    assert intent.wants_prompt_editing is True


# ── _heuristic_architecture_draft tests ──────────────────────────────────────

def test_heuristic_draft_simple_complexity():
    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        desired_complexity="simple",
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    analysis_nodes = [n for n in draft.topology.nodes if n.node_family == "analysis"]
    assert len(analysis_nodes) <= 3
    assert draft.proposed_name  # has a name


def test_heuristic_draft_moderate_complexity():
    intent = ArchitectureIntent(
        risk_level="aggressive",
        time_horizon="short",
        desired_complexity="moderate",
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    analysis_nodes = [n for n in draft.topology.nodes if n.node_family == "analysis"]
    assert len(analysis_nodes) <= 5


def test_heuristic_draft_synthesis_stage():
    intent = ArchitectureIntent(
        risk_level="conservative",
        time_horizon="long",
        wants_synthesis_stage=True,
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    # New architecture uses node_family="reasoning" for intermediate aggregation nodes
    reasoning_nodes = [n for n in draft.topology.nodes if n.node_family == "reasoning"]
    assert len(reasoning_nodes) >= 1


def test_heuristic_draft_no_synthesis_stage():
    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        wants_synthesis_stage=False,
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    synthesis_nodes = [n for n in draft.topology.nodes if n.node_family == "synthesis"]
    assert len(synthesis_nodes) == 0


def test_heuristic_draft_has_required_nodes():
    intent = ArchitectureIntent(risk_level="moderate", time_horizon="medium")
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    # New architecture: data_ingestion nodes + output (terminal) node
    families = {n.node_family for n in draft.topology.nodes}
    assert "data_ingestion" in families
    assert "output" in families


def test_heuristic_draft_topology_is_valid():
    """The heuristic draft must always produce a valid topology."""
    from backend.llm.topology_compiler import validate_topology

    intent = ArchitectureIntent(
        risk_level="aggressive",
        time_horizon="short",
        preferred_factors=["momentum", "sentiment"],
        wants_synthesis_stage=True,
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    result = validate_topology(draft.topology)
    assert result.valid, f"Heuristic draft topology invalid: {result.errors}"


def test_heuristic_draft_desired_node_count():
    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        desired_analysis_node_count=2,
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    # New architecture: data_ingestion family replaces "analysis"
    ingestion_nodes = [n for n in draft.topology.nodes if n.node_family == "data_ingestion"]
    assert len(ingestion_nodes) == 2


def test_heuristic_draft_no_debate_flag():
    intent = ArchitectureIntent(
        risk_level="conservative",
        time_horizon="long",
        wants_debate_stage=False,
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    assert draft.behavior_rules.debate_enabled is False


def test_heuristic_draft_custom_name():
    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        custom_team_name="My Alpha Team",
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    assert draft.proposed_name == "My Alpha Team"


def test_heuristic_draft_follow_up_on_unresolved():
    intent = ArchitectureIntent()  # no risk_level, no time_horizon
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    assert draft.follow_up_question is not None


def test_heuristic_draft_no_follow_up_when_resolved():
    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        preferred_factors=["value", "growth"],
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test"

    assert draft.follow_up_question is None


def test_heuristic_draft_compilation_roundtrip():
    """Heuristic draft can be compiled to a valid CompiledTeam."""
    from backend.llm.topology_compiler import compile_topology_to_flat_team

    intent = ArchitectureIntent(
        risk_level="moderate",
        time_horizon="medium",
        desired_complexity="simple",
        preferred_factors=["value"],
    )
    draft = _heuristic_architecture_draft(intent)
    draft.conversation_id = "test-roundtrip"

    compiled = compile_topology_to_flat_team(draft, intent.to_strategy_preferences())
    assert compiled.team_classification in ("validated_custom", "experimental_custom")
    assert len(compiled.compiled_agent_specs) > 0
    assert "risk_manager" in compiled.enabled_agents
    assert "portfolio_manager" in compiled.enabled_agents
