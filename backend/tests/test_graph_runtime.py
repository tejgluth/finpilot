from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.agents.graph_runtime import run_graph_pipeline
from backend.llm.budget import BudgetTracker
from backend.llm.strategy_builder import build_execution_snapshot
from backend.llm.topology_compiler import compile_topology_to_flat_team
from backend.models.agent_team import ArchitectureDraft, DataBoundary, TeamEdge, TeamNode, TeamTopology
from backend.models.signal import AgentSignal
from backend.settings import build_default_user_settings


def _now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.mark.asyncio
async def test_validated_custom_team_routes_risk_and_decision_nodes_deterministically(monkeypatch):
    technicals = TeamNode(
        node_id="node-tech",
        display_name="Technicals",
        node_family="analysis",
        agent_type="technicals",
        influence_weight=70,
        enabled=True,
    )
    risk = TeamNode(
        node_id="node-risk",
        display_name="Risk Manager",
        node_family="risk",
        influence_weight=100,
        enabled=True,
    )
    decision = TeamNode(
        node_id="node-decision",
        display_name="Portfolio Manager",
        node_family="decision",
        influence_weight=100,
        enabled=True,
    )
    topology = TeamTopology(
        nodes=[technicals, risk, decision],
        edges=[
            TeamEdge(source_node_id=technicals.node_id, target_node_id=risk.node_id),
            TeamEdge(source_node_id=risk.node_id, target_node_id=decision.node_id),
        ],
    )
    compiled = compile_topology_to_flat_team(
        ArchitectureDraft(
            conversation_id="test",
            topology=topology,
            proposed_name="Validated Runtime Team",
        )
    )

    async def fake_analyze(self, **kwargs):  # noqa: ARG001
        return AgentSignal(
            ticker="AFL",
            agent_name="technicals",
            action="BUY",
            raw_confidence=0.7,
            final_confidence=0.7,
            reasoning="Mock technical breakout",
            cited_data=[],
            unavailable_fields=[],
            data_coverage_pct=1.0,
            oldest_data_age_minutes=15.0,
            warning="",
        )

    async def forbidden_reasoning(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Risk/decision nodes should not route through _run_reasoning_node.")

    monkeypatch.setattr("backend.agents.analysis.technicals.TechnicalsAgent.analyze", fake_analyze)
    monkeypatch.setattr("backend.agents.graph_runtime._run_reasoning_node", forbidden_reasoning)

    user_settings = build_default_user_settings()
    snapshot = build_execution_snapshot(
        mode="backtest_experimental",
        ticker_or_universe="AFL",
        user_settings=user_settings,
        compiled_team=compiled,
        data_boundary=DataBoundary(
            mode="backtest_experimental",
            as_of_datetime="2024-03-29T16:00:00+00:00",
            allow_latest_semantics=True,
        ),
        cost_model={"slippage_pct": 0.1, "commission_pct": 0.0},
        notes=[_now()],
    )

    signals, bull_case, bear_case, decision_output = await run_graph_pipeline(
        "AFL",
        user_settings,
        snapshot,
        BudgetTracker(max_cost_usd=10.0, max_tokens=20_000),
    )

    assert len(signals) == 1
    assert signals[0].source_agent_name == "technicals"
    assert decision_output.action == "BUY"
    assert decision_output.confidence > 0.0
    assert decision_output.risk_notes == "Risk checks passed."
    assert "Technicals" in decision_output.cited_agents
    assert bull_case is None or bull_case.cited_agents
    assert bear_case is None or bear_case.cited_agents
