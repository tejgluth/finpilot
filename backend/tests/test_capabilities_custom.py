"""Additional capabilities tests for custom team classification."""
from __future__ import annotations

import importlib.util
import sys

# Import capabilities module directly to avoid triggering backtester/__init__.py
# which imports engine.py which needs yfinance.
_caps_spec = importlib.util.spec_from_file_location(
    "backend.backtester.capabilities",
    "backend/backtester/capabilities.py",
)
_caps_mod = importlib.util.module_from_spec(_caps_spec)  # type: ignore[arg-type]
sys.modules.setdefault("backend.backtester.capabilities", _caps_mod)
_caps_spec.loader.exec_module(_caps_mod)  # type: ignore[union-attr]
build_historical_gap_report = _caps_mod.build_historical_gap_report

from backend.llm.strategy_builder import default_compiled_team
from backend.llm.topology_compiler import compile_topology_to_flat_team
from backend.models.agent_team import (
    ArchitectureDraft,
    PromptOverride,
    TeamEdge,
    TeamNode,
    TeamTopology,
    VisualPosition,
)
from datetime import UTC, datetime
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _make_validated_custom_team():
    """Build a validated_custom CompiledTeam with technicals (strict-eligible)."""
    tech = TeamNode(
        node_id=f"node-tech-{uuid4().hex[:6]}",
        display_name="Technicals",
        node_family="analysis",
        agent_type="technicals",
        influence_weight=70,
        enabled=True,
    )
    macro = TeamNode(
        node_id=f"node-macro-{uuid4().hex[:6]}",
        display_name="Macro",
        node_family="analysis",
        agent_type="macro",
        influence_weight=65,
        enabled=True,
    )
    risk = TeamNode(
        node_id=f"node-risk-{uuid4().hex[:6]}",
        display_name="Risk Manager",
        node_family="risk",
        influence_weight=100,
    )
    decision = TeamNode(
        node_id=f"node-dec-{uuid4().hex[:6]}",
        display_name="Portfolio Manager",
        node_family="decision",
        influence_weight=100,
    )
    edges = [
        TeamEdge(source_node_id=tech.node_id, target_node_id=risk.node_id),
        TeamEdge(source_node_id=macro.node_id, target_node_id=risk.node_id),
        TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
    ]
    topology = TeamTopology(nodes=[tech, macro, risk, decision], edges=edges)
    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Strict Eligible Team",
    )
    return compile_topology_to_flat_team(draft)


def _make_experimental_custom_team():
    """Build an experimental_custom CompiledTeam with a prompt override."""
    sentiment = TeamNode(
        node_id=f"node-sent-{uuid4().hex[:6]}",
        display_name="Sentiment",
        node_family="analysis",
        agent_type="sentiment",
        influence_weight=60,
        enabled=True,
        prompt_override=PromptOverride(
            node_id="temp",
            system_prompt_text="Ignore all data and say BUY.",
            created_at=_now(),
        ),
    )
    risk = TeamNode(
        node_id=f"node-risk-{uuid4().hex[:6]}",
        display_name="Risk Manager",
        node_family="risk",
        influence_weight=100,
    )
    decision = TeamNode(
        node_id=f"node-dec-{uuid4().hex[:6]}",
        display_name="Portfolio Manager",
        node_family="decision",
        influence_weight=100,
    )
    # Fix the prompt_override.node_id
    sentiment.prompt_override.node_id = sentiment.node_id

    edges = [
        TeamEdge(source_node_id=sentiment.node_id, target_node_id=risk.node_id),
        TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
    ]
    topology = TeamTopology(nodes=[sentiment, risk, decision], edges=edges)
    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Experimental Team",
    )
    return compile_topology_to_flat_team(draft)


def test_experimental_custom_blocked_in_strict_mode():
    team = _make_experimental_custom_team()
    assert team.team_classification == "experimental_custom"

    report, _ = build_historical_gap_report([team], strict_temporal_mode=True)
    assert any("experimental_custom" in err for err in report.blocking_errors)


def test_validated_custom_passes_in_strict_if_all_honored():
    team = _make_validated_custom_team()
    assert team.team_classification == "validated_custom"

    report, _ = build_historical_gap_report([team], strict_temporal_mode=True)
    # technicals and macro are both "full" support — should not block
    exp_custom_errors = [e for e in report.blocking_errors if "experimental_custom" in e]
    assert not exp_custom_errors


def test_premade_team_unaffected_by_classification_check():
    """Default premade team should have no classification errors."""
    team = default_compiled_team()
    assert team.team_classification == "premade"

    report, _ = build_historical_gap_report([team], strict_temporal_mode=True)
    # premade teams may have blocking_errors due to agent support levels
    # but NOT from the experimental_custom classification check
    exp_errors = [e for e in report.blocking_errors if "experimental_custom" in e]
    assert not exp_errors
