from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import json

from backend.agents.analysis import (
    FundamentalsAgent,
    GrowthAgent,
    MacroAgent,
    MomentumAgent,
    SentimentAgent,
    TechnicalsAgent,
    ValueAgent,
)
from backend.agents.base_agent import ANTI_HALLUCINATION_SUFFIX
from backend.agents.debate.bear_researcher import build_bear_case
from backend.agents.debate.bull_researcher import build_bull_case
from backend.agents.decision.portfolio_manager import decide_portfolio_action
from backend.agents.decision.risk_manager import evaluate_risk
from backend.llm.budget import BudgetTracker
from backend.llm.provider import get_llm_client
from backend.models.agent_team import ExecutionSnapshot, ReasoningOutput, TeamNode
from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision
from backend.security.output_validator import parse_llm_json
from backend.settings.user_settings import UserSettings


AGENT_FACTORY = {
    "fundamentals": FundamentalsAgent,
    "technicals": TechnicalsAgent,
    "sentiment": SentimentAgent,
    "macro": MacroAgent,
    "value": ValueAgent,
    "momentum": MomentumAgent,
    "growth": GrowthAgent,
}


@dataclass
class GateResult:
    passed: bool
    note: str


@dataclass
class GraphNodeResult:
    signals: list[AgentSignal] = field(default_factory=list)
    reasoning_outputs: list[ReasoningOutput] = field(default_factory=list)
    bull_case: DebateOutput | None = None
    bear_case: DebateOutput | None = None
    gate: GateResult | None = None
    risk: Any | None = None
    decision: PortfolioDecision | None = None


async def run_graph_pipeline(
    ticker: str,
    runtime_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot,
    budget: BudgetTracker,
) -> tuple[list[AgentSignal], DebateOutput | None, DebateOutput | None, PortfolioDecision]:
    team = execution_snapshot.effective_team
    topology = team.topology
    if topology is None:
        raise ValueError("Graph runtime requires a topology-backed team.")

    nodes = {node.node_id: node for node in topology.nodes if node.enabled}
    edges_by_source: dict[str, list[str]] = {}
    indegree: dict[str, int] = {node_id: 0 for node_id in nodes}
    for edge in topology.edges:
        if edge.source_node_id not in nodes or edge.target_node_id not in nodes:
            continue
        edges_by_source.setdefault(edge.source_node_id, []).append(edge.target_node_id)
        indegree[edge.target_node_id] = indegree.get(edge.target_node_id, 0) + 1

    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for downstream in edges_by_source.get(node_id, []):
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                queue.append(downstream)

    results: dict[str, GraphNodeResult] = {}
    all_signals: list[AgentSignal] = []
    final_bull: DebateOutput | None = None
    final_bear: DebateOutput | None = None
    final_decision: PortfolioDecision | None = None
    blocked_nodes: set[str] = set()

    for node_id in order:
        node = nodes[node_id]
        if node_id in blocked_nodes:
            results[node_id] = GraphNodeResult(
                gate=GateResult(
                    passed=False,
                    note=f"{node.display_name} did not run because an upstream gate blocked this branch.",
                ),
            )
            continue

        upstream_ids = [
            edge.source_node_id
            for edge in topology.edges
            if edge.target_node_id == node_id and edge.source_node_id in results
        ]
        upstream_results = [results[source_id] for source_id in upstream_ids]

        # Determine effective type for routing
        is_ingestion = bool(
            node.data_domain
            or (node.node_family == "analysis" and node.agent_type and node.agent_type in AGENT_FACTORY)
        )
        is_terminal = bool(node.parameters.get("is_terminal") or node.node_family == "decision")
        has_system_prompt = bool(
            node.system_prompt
            or (node.prompt_contract and node.prompt_contract.system_prompt_text)
            or (node.prompt_override and node.prompt_override.system_prompt_text)
        )

        if is_ingestion:
            result = await _run_analysis_node(
                ticker=ticker,
                node=node,
                runtime_settings=runtime_settings,
                execution_snapshot=execution_snapshot,
                compiled_spec=team.compiled_agent_specs.get(node.node_id)
                or team.compiled_agent_specs.get(node.data_domain or "")
                or (team.compiled_agent_specs.get(node.agent_type or "") if node.agent_type else None),
                budget=budget,
            )
            all_signals.extend(result.signals)
        elif node.node_family == "data_preparation":
            result = _run_data_preparation_node(upstream_results)
        elif node.node_family == "synthesis":
            result = _run_synthesis_node(ticker, node, upstream_results)
            all_signals.extend(result.signals)
        elif node.node_family == "debate":
            result = _run_debate_node(upstream_results)
            final_bull = result.bull_case or final_bull
            final_bear = result.bear_case or final_bear
        elif node.node_family == "gate":
            result = _run_gate_node(node, upstream_results)
            if result.gate is not None and not result.gate.passed:
                blocked_nodes.update(_descendants(node_id, edges_by_source))
        elif node.node_family == "risk":
            result = _run_risk_node(node, upstream_results, runtime_settings)
        elif node.node_family == "decision" and not has_system_prompt:
            result = _run_decision_node(
                ticker=ticker,
                node=node,
                upstream_results=upstream_results,
                runtime_settings=runtime_settings,
                team_weights=team.agent_weights,
            )
            final_bull = result.bull_case or final_bull
            final_bear = result.bear_case or final_bear
            final_decision = result.decision or final_decision
        elif has_system_prompt or node.node_family in ("reasoning", "output"):
            # Custom reasoning node — run LLM with system_prompt and upstream context
            result = await _run_reasoning_node(
                ticker=ticker,
                node=node,
                upstream_results=upstream_results,
                runtime_settings=runtime_settings,
                execution_snapshot=execution_snapshot,
                budget=budget,
            )
            all_signals.extend(result.signals)
            if result.decision:
                final_decision = result.decision
            final_bull = result.bull_case or final_bull
            final_bear = result.bear_case or final_bear
        elif is_terminal:
            # Output/terminal nodes with no custom prompt use the deterministic fallback.
            result = await _run_terminal_fallback(
                ticker=ticker,
                node=node,
                upstream_results=upstream_results,
                runtime_settings=runtime_settings,
                agent_weights=team.agent_weights,
                execution_snapshot=execution_snapshot,
                budget=budget,
            )
            final_bull = result.bull_case or final_bull
            final_bear = result.bear_case or final_bear
            final_decision = result.decision or final_decision
        else:
            result = GraphNodeResult()

        results[node_id] = result

    if final_decision is None:
        final_bull = final_bull or (build_bull_case(all_signals) if runtime_settings.agents.enable_bull_bear_debate else None)
        final_bear = final_bear or (build_bear_case(all_signals) if runtime_settings.agents.enable_bull_bear_debate else None)
        risk = evaluate_risk(all_signals, runtime_settings.guardrails, runtime_settings.agents)
        final_decision = decide_portfolio_action(
            ticker=ticker,
            signals=all_signals,
            bull_case=final_bull,
            bear_case=final_bear,
            proposed_position_pct=risk.proposed_position_pct,
            agent_weights=team.agent_weights,
            risk_notes=risk.notes if risk.allowed else f"Trade blocked: {risk.notes}",
            max_data_age_minutes=runtime_settings.data_sources.max_data_age_minutes,
        )
        if not risk.allowed:
            final_decision.action = "HOLD"
            final_decision.proposed_position_pct = 0.0

    return all_signals, final_bull, final_bear, final_decision


def _descendants(node_id: str, edges_by_source: dict[str, list[str]]) -> set[str]:
    blocked: set[str] = set()
    queue = deque(edges_by_source.get(node_id, []))
    while queue:
        current = queue.popleft()
        if current in blocked:
            continue
        blocked.add(current)
        queue.extend(edges_by_source.get(current, []))
    return blocked


async def _run_analysis_node(
    *,
    ticker: str,
    node: TeamNode,
    runtime_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot,
    compiled_spec,
    budget: BudgetTracker,
) -> GraphNodeResult:
    # data_domain takes priority; fall back to agent_type for backward compat
    domain_key = node.data_domain or node.agent_type or ""
    if domain_key not in AGENT_FACTORY:
        return GraphNodeResult()
    spec = compiled_spec
    if spec is None:
        spec = AGENT_FACTORY[domain_key]()._default_compiled_spec()  # type: ignore[attr-defined]
    agent = AGENT_FACTORY[domain_key]()
    signal = await agent.analyze(
        ticker=ticker,
        data_settings=runtime_settings.data_sources,
        llm_settings=runtime_settings.llm,
        budget=budget,
        compiled_spec=spec,
        execution_snapshot=execution_snapshot,
    )
    signal.agent_name = node.display_name
    signal.source_agent_name = node.agent_type
    signal.graph_node_id = node.node_id
    return GraphNodeResult(signals=[signal])


def _run_data_preparation_node(upstream_results: list[GraphNodeResult]) -> GraphNodeResult:
    return GraphNodeResult(
        signals=_collect_upstream_signals(upstream_results),
        bull_case=next((item.bull_case for item in reversed(upstream_results) if item.bull_case is not None), None),
        bear_case=next((item.bear_case for item in reversed(upstream_results) if item.bear_case is not None), None),
        gate=next((item.gate for item in reversed(upstream_results) if item.gate is not None), None),
    )


def _run_synthesis_node(ticker: str, node: TeamNode, upstream_results: list[GraphNodeResult]) -> GraphNodeResult:
    upstream_signals = _collect_upstream_signals(upstream_results)
    if not upstream_signals:
        return GraphNodeResult()
    weighted_total = 0.0
    signed_total = 0.0
    citations = []
    cited_names = []
    for signal in upstream_signals:
        direction = 1.0 if signal.action == "BUY" else -1.0 if signal.action == "SELL" else 0.0
        strength = max(signal.final_confidence, signal.raw_confidence)
        weighted_total += strength
        signed_total += direction * strength
        citations.extend(signal.cited_data[:2])
        cited_names.append(signal.agent_name)
    confidence = 0.0 if weighted_total <= 0 else min(1.0, abs(signed_total) / weighted_total)
    action = "BUY" if signed_total > 0.08 else "SELL" if signed_total < -0.08 else "HOLD"
    synthesized = AgentSignal(
        ticker=ticker,
        agent_name=node.display_name,
        source_agent_name="synthesis",
        graph_node_id=node.node_id,
        action=action,
        raw_confidence=round(confidence, 4),
        final_confidence=round(confidence, 4),
        reasoning=(
            f"{node.display_name} synthesized {len(upstream_signals)} upstream views from "
            f"{', '.join(dict.fromkeys(cited_names))}."
        )[:500],
        cited_data=citations[:8],
        unavailable_fields=[],
        data_coverage_pct=round(sum(item.data_coverage_pct for item in upstream_signals) / len(upstream_signals), 4),
        oldest_data_age_minutes=max((item.oldest_data_age_minutes for item in upstream_signals), default=0.0),
        warning="",
    )
    return GraphNodeResult(signals=[synthesized])


def _run_debate_node(upstream_results: list[GraphNodeResult]) -> GraphNodeResult:
    signals = _collect_upstream_signals(upstream_results)
    if not signals:
        return GraphNodeResult()
    return GraphNodeResult(
        bull_case=build_bull_case(signals),
        bear_case=build_bear_case(signals),
    )


def _run_gate_node(node: TeamNode, upstream_results: list[GraphNodeResult]) -> GraphNodeResult:
    signals = _collect_upstream_signals(upstream_results)
    threshold = float(node.modifiers.get("min_confidence_threshold", 0.45))
    if not signals:
        gate = GateResult(False, f"{node.display_name} blocked execution because no upstream signals were present.")
        return GraphNodeResult(gate=gate)
    avg_conf = sum(signal.final_confidence for signal in signals) / len(signals)
    passed = avg_conf >= threshold
    note = (
        f"{node.display_name} passed with average confidence {avg_conf:.2f}."
        if passed
        else f"{node.display_name} blocked execution because average confidence {avg_conf:.2f} was below {threshold:.2f}."
    )
    return GraphNodeResult(gate=GateResult(passed=passed, note=note))


def _run_risk_node(node: TeamNode, upstream_results: list[GraphNodeResult], runtime_settings: UserSettings) -> GraphNodeResult:
    signals = _collect_upstream_signals(upstream_results)
    risk = evaluate_risk(signals, runtime_settings.guardrails, runtime_settings.agents)
    gate_notes = [item.gate.note for item in upstream_results if item.gate is not None and not item.gate.passed]
    if gate_notes:
        risk.allowed = False
        risk.notes = " ".join([risk.notes, *gate_notes]).strip()
    result = GraphNodeResult(signals=signals)
    result.risk = risk
    return result


def _run_decision_node(
    ticker: str,
    node: TeamNode,
    upstream_results: list[GraphNodeResult],
    runtime_settings: UserSettings,
    team_weights: dict[str, int],
) -> GraphNodeResult:
    signals = _collect_upstream_signals(upstream_results)
    bull_case = next((item.bull_case for item in reversed(upstream_results) if item.bull_case is not None), None)
    bear_case = next((item.bear_case for item in reversed(upstream_results) if item.bear_case is not None), None)
    risk = next((item.risk for item in reversed(upstream_results) if item.risk is not None), None)
    if risk is None:
        risk = evaluate_risk(signals, runtime_settings.guardrails, runtime_settings.agents)
    decision = decide_portfolio_action(
        ticker=ticker,
        signals=signals,
        bull_case=bull_case,
        bear_case=bear_case,
        proposed_position_pct=risk.proposed_position_pct,
        agent_weights=team_weights,
        risk_notes=risk.notes if risk.allowed else f"Trade blocked: {risk.notes}",
        max_data_age_minutes=runtime_settings.data_sources.max_data_age_minutes,
    )
    if not risk.allowed:
        decision.action = "HOLD"
        decision.proposed_position_pct = 0.0
    decision.reasoning = (
        f"{node.display_name} followed the custom graph routing to aggregate upstream nodes into the final action."
    )[:500]
    return GraphNodeResult(
        signals=signals,
        bull_case=bull_case,
        bear_case=bear_case,
        decision=decision,
    )


async def _run_reasoning_node(
    *,
    ticker: str,
    node: TeamNode,
    upstream_results: list[GraphNodeResult],
    runtime_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot,
    budget: BudgetTracker,
) -> GraphNodeResult:
    from backend.security.audit_logger import AuditLogger

    upstream_signals = _collect_upstream_signals(upstream_results)
    upstream_reasoning = _collect_upstream_reasoning(upstream_results)

    context_payload = {
        "node_name": node.display_name,
        "ticker": ticker,
        "upstream_agent_signals": [s.model_dump() for s in upstream_signals],
        "upstream_reasoning_outputs": [r.model_dump() for r in upstream_reasoning],
    }

    system = (node.system_prompt or "") + "\n" + ANTI_HALLUCINATION_SUFFIX
    output_schema = node.parameters.get("output_schema", "ReasoningOutput")
    schema_map = {
        "ReasoningOutput": ReasoningOutput,
        "PortfolioDecision": PortfolioDecision,
        "AgentSignal": AgentSignal,
    }
    schema_class = schema_map.get(output_schema, ReasoningOutput)

    client = get_llm_client(runtime_settings.llm)
    raw = await client.chat(
        system=system,
        messages=[{"role": "user", "content": json.dumps(context_payload)}],
        max_tokens=int(node.parameters.get("max_tokens", 600)),
        temperature=float(node.parameters.get("temperature", 0.3)),
        budget=budget,
    )

    parsed = parse_llm_json(raw, schema_class)

    AuditLogger.log("system", "custom_reasoning_node_executed", {
        "node_id": node.node_id,
        "node_name": node.display_name,
        "output_schema": output_schema,
        "ticker": ticker,
    })

    if isinstance(parsed, PortfolioDecision):
        return GraphNodeResult(decision=parsed)
    elif isinstance(parsed, AgentSignal):
        parsed.agent_name = node.display_name
        parsed.source_agent_name = getattr(node, "agent_type", "") or "custom"
        parsed.graph_node_id = node.node_id
        return GraphNodeResult(signals=[parsed])
    else:
        parsed.node_id = node.node_id
        parsed.node_name = node.display_name
        return GraphNodeResult(reasoning_outputs=[parsed])


async def _run_terminal_fallback(
    *,
    ticker: str,
    node: TeamNode,
    upstream_results: list[GraphNodeResult],
    runtime_settings: UserSettings,
    agent_weights: dict[str, int],
    execution_snapshot: ExecutionSnapshot,
    budget: BudgetTracker,
) -> GraphNodeResult:
    signals = _collect_upstream_signals(upstream_results)
    bull_case = next((item.bull_case for item in reversed(upstream_results) if item.bull_case is not None), None)
    bear_case = next((item.bear_case for item in reversed(upstream_results) if item.bear_case is not None), None)

    if bull_case is None and runtime_settings.agents.enable_bull_bear_debate:
        bull_case = build_bull_case(signals)
    if bear_case is None and runtime_settings.agents.enable_bull_bear_debate:
        bear_case = build_bear_case(signals)

    risk = next((item.risk for item in reversed(upstream_results) if item.risk is not None), None)
    if risk is None:
        risk = evaluate_risk(signals, runtime_settings.guardrails, runtime_settings.agents)

    decision = decide_portfolio_action(
        ticker=ticker,
        signals=signals,
        bull_case=bull_case,
        bear_case=bear_case,
        proposed_position_pct=risk.proposed_position_pct,
        agent_weights=agent_weights,
        risk_notes=risk.notes if risk.allowed else f"Trade blocked: {risk.notes}",
        max_data_age_minutes=runtime_settings.data_sources.max_data_age_minutes,
    )
    if not risk.allowed:
        decision.action = "HOLD"
        decision.proposed_position_pct = 0.0
    decision.reasoning = (
        f"{node.display_name} aggregated upstream signals into the final portfolio action."
    )[:500]
    return GraphNodeResult(
        signals=signals,
        bull_case=bull_case,
        bear_case=bear_case,
        decision=decision,
    )


def _collect_upstream_reasoning(upstream_results: list[GraphNodeResult]) -> list[ReasoningOutput]:
    outputs: list[ReasoningOutput] = []
    for result in upstream_results:
        outputs.extend(result.reasoning_outputs)
    return outputs


def _collect_upstream_signals(upstream_results: list[GraphNodeResult]) -> list[AgentSignal]:
    signals: list[AgentSignal] = []
    for result in upstream_results:
        signals.extend(result.signals)
    return signals
