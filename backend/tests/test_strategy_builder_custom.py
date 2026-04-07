"""Tests for custom-team-related additions to strategy_builder."""
from __future__ import annotations

import pytest

from backend.llm.strategy_builder import (
    build_execution_snapshot,
    default_compiled_team,
    save_team_version,
)
from backend.llm.topology_compiler import compile_topology_to_flat_team
from backend.models.agent_team import (
    ArchitectureDraft,
    DataBoundary,
    TeamEdge,
    TeamNode,
    TeamTopology,
)
from backend.settings import build_default_user_settings
from backend.database import init_db
from datetime import UTC, datetime
from uuid import uuid4
import pytest


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _make_simple_custom_team():
    tech = TeamNode(
        node_id=f"node-tech-{uuid4().hex[:6]}",
        display_name="Technicals",
        node_family="analysis",
        agent_type="technicals",
        influence_weight=70,
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
        TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
    ]
    topology = TeamTopology(nodes=[tech, risk, decision], edges=edges)
    draft = ArchitectureDraft(
        conversation_id="test",
        topology=topology,
        proposed_name="Custom Tech Team",
    )
    return compile_topology_to_flat_team(draft)


@pytest.mark.asyncio
async def test_save_team_version_preserves_team_classification(tmp_path, monkeypatch):
    monkeypatch.setenv("FINPILOT_DB_PATH", str(tmp_path / "test.db"))
    await init_db()

    custom_team = _make_simple_custom_team()
    assert custom_team.team_classification == "validated_custom"

    version = await save_team_version(
        custom_team,
        conversation_id="cconv-test",
        label="My Custom Team",
        creation_source="custom_conversation",
    )

    assert version.team_classification == "validated_custom"
    assert version.creation_source == "custom_conversation"
    assert version.version_number >= 1


@pytest.mark.asyncio
async def test_save_team_version_custom_source_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("FINPILOT_DB_PATH", str(tmp_path / "test.db"))
    await init_db()

    custom_team = _make_simple_custom_team()
    version = await save_team_version(
        custom_team,
        conversation_id=None,
        label="Studio Edit",
        creation_source="studio_edit",
    )
    assert version.creation_source == "studio_edit"


def test_build_execution_snapshot_stamps_classification():
    settings = build_default_user_settings()
    custom_team = _make_simple_custom_team()

    snap = build_execution_snapshot(
        mode="analyze",
        ticker_or_universe="AAPL",
        user_settings=settings,
        compiled_team=custom_team,
        data_boundary=DataBoundary(mode="live"),
        cost_model={"slippage_pct": 0.001, "commission_pct": 0.001},
    )

    assert snap.team_classification == "validated_custom"
    assert snap.prompt_override_present is False


def test_build_execution_snapshot_premade_classification():
    settings = build_default_user_settings()
    premade = default_compiled_team()
    assert premade.team_classification == "premade"

    snap = build_execution_snapshot(
        mode="analyze",
        ticker_or_universe="AAPL",
        user_settings=settings,
        compiled_team=premade,
        data_boundary=DataBoundary(mode="live"),
        cost_model={},
    )

    assert snap.team_classification == "premade"
    assert snap.prompt_override_present is False
