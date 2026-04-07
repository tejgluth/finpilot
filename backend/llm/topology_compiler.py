"""
Deterministic compiler: ArchitectureDraft → CompiledTeam.

This module validates a TeamTopology, computes execution eligibility,
and produces a CompiledTeam artifact for custom teams. The topology
remains the runtime source of truth; the flat spec layer exists so the
grounded analysis agents and historical tooling can reuse the existing
compiled-agent infrastructure safely.
"""
from __future__ import annotations

import json
from collections import deque
from copy import deepcopy
from hashlib import sha256
from typing import Any

from backend.llm.prompt_packs import PROMPT_PACKS_BY_AGENT

# Strict-backtest eligibility per analysis agent.
# This mirrors HISTORICAL_SUPPORT in backtester/capabilities.py but is
# kept here to avoid importing the engine (which requires yfinance) at
# compile time. Keep in sync with capabilities.py.
_STRICT_ELIGIBLE: frozenset[str] = frozenset({"technicals", "momentum", "macro"})


def _get_historical_support() -> dict:
    """Return the HISTORICAL_SUPPORT dict, loaded lazily to avoid yfinance dependency at import time."""
    try:
        import importlib
        caps = importlib.import_module("backend.backtester.capabilities")
        return caps.HISTORICAL_SUPPORT  # type: ignore[attr-defined]
    except Exception:
        # Fallback: build a minimal dict from the in-module constant
        result: dict = {}
        for agent in ("fundamentals", "technicals", "sentiment", "macro", "value", "momentum", "growth"):
            result[agent] = {"honored_in_strict": agent in _STRICT_ELIGIBLE}
        return result
from backend.models.agent_team import (
    REQUIRED_DECISION_AGENTS,
    VALID_ANALYSIS_AGENTS,
    ArchitectureDraft,
    CompiledAgentSpec,
    CompiledReasoningSpec,
    CompiledTeam,
    NodeModeEligibility,
    StrategyPreferences,
    TeamBehaviorRules,
    TeamEdge,
    TeamExecutionProfile,
    TeamNode,
    TeamTopology,
    TeamValidationResult,
    ValidationReport,
)

# Data domains that have real data fetchers.
DATA_INGESTION_DOMAINS: frozenset[str] = frozenset(VALID_ANALYSIS_AGENTS)


# ── Validation ────────────────────────────────────────────────────────────────

def _is_ingestion_node(node: TeamNode) -> bool:
    """A node is a data-ingestion node if it has data_domain set, OR uses the old analysis family without data_domain (backward compat)."""
    if node.data_domain:
        return True
    # Backward compat: old-style analysis nodes identified only by agent_type
    if node.node_family == "analysis" and node.agent_type and node.agent_type in DATA_INGESTION_DOMAINS:
        return True
    return False


def _is_terminal_node(node: TeamNode) -> bool:
    """A terminal node produces the final PortfolioDecision output."""
    if node.parameters.get("is_terminal"):
        return True
    # Backward compat: old-style decision nodes
    if node.node_family == "decision":
        return True
    return False


def validate_topology(topology: TeamTopology) -> TeamValidationResult:
    """Run all graph validity checks. Returns TeamValidationResult."""
    errors: list[str] = []
    warnings: list[str] = []
    node_results: dict[str, list[str]] = {}

    nodes_by_id = {n.node_id: n for n in topology.nodes}
    edges_by_source: dict[str, list[TeamEdge]] = {}
    edges_by_target: dict[str, list[TeamEdge]] = {}

    for edge in topology.edges:
        edges_by_source.setdefault(edge.source_node_id, []).append(edge)
        edges_by_target.setdefault(edge.target_node_id, []).append(edge)

    # Rule: all edge endpoints must reference valid node_ids
    for edge in topology.edges:
        if edge.source_node_id not in nodes_by_id:
            errors.append(f"Edge {edge.edge_id} references unknown source node '{edge.source_node_id}'.")
        if edge.target_node_id not in nodes_by_id:
            errors.append(f"Edge {edge.edge_id} references unknown target node '{edge.target_node_id}'.")

    ingestion_nodes = [n for n in topology.nodes if _is_ingestion_node(n)]
    terminal_nodes = [n for n in topology.nodes if _is_terminal_node(n)]
    # Backward compat collections for eligibility computation
    analysis_nodes = ingestion_nodes  # alias

    # Rule 1: at least one data-ingestion node
    if not ingestion_nodes:
        errors.append("At least one data-ingestion node (with data_domain set) is required.")

    # Rule 2: exactly one terminal output node
    if not terminal_nodes:
        errors.append(
            "A terminal output node is required. "
            "Set parameters.is_terminal=true on the final decision node, or use node_family='decision'."
        )
    elif len(terminal_nodes) > 1:
        errors.append(f"Only one terminal output node is allowed; found {len(terminal_nodes)}.")

    # Rule 3: validate data_domain for ingestion nodes
    for node in ingestion_nodes:
        nres: list[str] = []
        effective_domain = node.data_domain or node.agent_type
        if not effective_domain or effective_domain not in DATA_INGESTION_DOMAINS:
            msg = (
                f"Data-ingestion node '{node.node_id}' has unknown data_domain '{effective_domain}'. "
                f"Must be one of: {sorted(DATA_INGESTION_DOMAINS)}."
            )
            errors.append(msg)
            nres.append(msg)
        if nres:
            node_results[node.node_id] = nres

    # Rule 4: reasoning nodes with outgoing edges should have a system_prompt
    for node in topology.nodes:
        if _is_ingestion_node(node) or _is_terminal_node(node):
            continue
        if edges_by_source.get(node.node_id):
            # Has outgoing edges — should have a prompt
            effective_prompt = node.system_prompt or (
                node.prompt_contract.system_prompt_text if node.prompt_contract else ""
            )
            if not effective_prompt.strip():
                warnings.append(
                    f"Reasoning node '{node.node_id}' ({node.display_name}) has outgoing edges but no system_prompt. "
                    "Runtime will use passthrough behavior."
                )

    # Adjacency rules (only check when edge refs are valid)
    valid_edge_refs = all(
        e.source_node_id in nodes_by_id and e.target_node_id in nodes_by_id
        for e in topology.edges
    )
    if valid_edge_refs:
        # Terminal nodes cannot have outgoing edges
        for edge in topology.edges:
            src = nodes_by_id[edge.source_node_id]
            if _is_terminal_node(src):
                errors.append(
                    f"Terminal node '{src.node_id}' cannot have outgoing connections."
                )

        # Rule: non-source nodes must have incoming edges
        source_node_ids = {
            node.node_id for node in topology.nodes if _is_ingestion_node(node)
        }
        for node in topology.nodes:
            if node.node_id in source_node_ids:
                continue
            incoming = edges_by_target.get(node.node_id, [])
            if not incoming:
                errors.append(
                    f"Node '{node.node_id}' ({node.display_name}) is unreachable — no incoming edges."
                )

        # Rule: cycle detection via DFS
        adj = topology.adjacency()
        visited: set[str] = set()
        in_stack: set[str] = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            in_stack.add(node_id)
            for neighbour in adj.get(node_id, []):
                if neighbour not in visited:
                    if has_cycle(neighbour):
                        return True
                elif neighbour in in_stack:
                    return True
            in_stack.discard(node_id)
            return False

        for node in topology.nodes:
            if node.node_id not in visited:
                if has_cycle(node.node_id):
                    errors.append("Cycle detected in topology graph. Custom teams must be acyclic.")
                    break

        # Rule: path must exist from at least one ingestion node to the terminal
        if ingestion_nodes and terminal_nodes:
            terminal_id = terminal_nodes[0].node_id
            reachable: set[str] = set()
            queue_r = list(source_node_ids)
            while queue_r:
                nid = queue_r.pop()
                if nid in reachable:
                    continue
                reachable.add(nid)
                queue_r.extend(t for e in edges_by_source.get(nid, []) for t in [e.target_node_id])
            if terminal_id not in reachable:
                errors.append(
                    "No path exists from any data-ingestion node to the terminal output node."
                )

    # Warnings: prompt overrides → experimental_custom
    for node in topology.nodes:
        if node.prompt_override is not None:
            warnings.append(
                f"Node '{node.node_id}' has a prompt override; team will be classified as experimental_custom."
            )

    # Warnings: strict backtest eligibility
    _hs = _get_historical_support()
    strict_eligible_agents = [
        n for n in ingestion_nodes
        if (n.data_domain or n.agent_type) and n.enabled
        and _hs.get(n.data_domain or n.agent_type or "", {}).get("honored_in_strict", False)
    ]
    if ingestion_nodes and not strict_eligible_agents:
        warnings.append(
            "No enabled data-ingestion agents are strict-backtest-eligible; backtest_strict mode will be unavailable."
        )

    # Compute per-node mode eligibility for ingestion nodes
    for node in ingestion_nodes:
        mode_eligibility = _compute_node_mode_eligibility(node)
        node.backtest_strict_eligible = mode_eligibility.backtest_strict
        node.backtest_experimental_eligible = mode_eligibility.backtest_experimental
        node.paper_eligible = mode_eligibility.paper
        node.live_eligible = mode_eligibility.live
        node.mode_eligibility = mode_eligibility
        if not node.capability_bindings:
            warnings.append(
                f"Node '{node.node_id}' has no explicit capability bindings. Runtime will fall back to its grounded base agent domain."
            )
        for binding in node.capability_bindings:
            if binding.required and not binding.configured:
                warnings.append(
                    f"Node '{node.node_id}' depends on {binding.label}, which is not fully configured."
                )

    execution_profile = _compute_execution_profile(topology, errors, warnings)
    valid = len(errors) == 0

    return TeamValidationResult(
        valid=valid,
        team_classification=execution_profile.team_classification,
        errors=errors,
        warnings=warnings,
        normalized_fields=[],
        execution_profile=execution_profile,
        topology_errors=errors,
        node_results=node_results,
    )


def _compute_execution_profile(
    topology: TeamTopology,
    errors: list[str],
    warnings: list[str],
) -> TeamExecutionProfile:
    ingestion_nodes = [n for n in topology.nodes if _is_ingestion_node(n) and n.enabled]
    non_ingestion_nodes = [n for n in topology.nodes if not _is_ingestion_node(n)]

    has_prompt_override = any(n.prompt_override is not None for n in topology.nodes)
    has_synthesis_nodes = any(
        n.node_family in ("synthesis", "debate", "gate") for n in topology.nodes
    )

    # Classification:
    # experimental_custom: any custom reasoning node with a system_prompt OR any prompt_override
    # validated_custom: only data-ingestion + structural nodes with no custom system_prompts
    # premade: set externally for catalog teams
    has_custom_reasoning = any(
        bool(n.system_prompt or (n.prompt_contract and n.prompt_contract.system_prompt_text))
        for n in non_ingestion_nodes
    )
    if has_prompt_override or has_custom_reasoning:
        classification = "experimental_custom"
    else:
        classification = "validated_custom"

    # Strict backtest: NEVER for experimental_custom; only validated_custom with eligible ingestion
    if classification == "experimental_custom":
        strict_eligible = False
    else:
        strict_eligible = bool(ingestion_nodes) and not has_prompt_override
        for node in ingestion_nodes:
            mode_eligibility = _compute_node_mode_eligibility(node)
            strict_eligible = strict_eligible and mode_eligibility.backtest_strict

    # Experimental backtest: not available with prompt_override; available otherwise
    if has_prompt_override:
        experimental_eligible = False
    else:
        experimental_eligible = bool(ingestion_nodes) and all(
            _compute_node_mode_eligibility(node).backtest_experimental for node in ingestion_nodes
        )

    ineligibility_reasons: list[str] = []
    if has_prompt_override:
        ineligibility_reasons.append(
            "Prompt overrides are present; strict and experimental backtesting are disabled."
        )
    elif classification == "experimental_custom":
        ineligibility_reasons.append(
            "Custom reasoning nodes with system prompts disable strict backtest "
            "(temporal faithfulness cannot be guaranteed for custom prompts)."
        )
    elif not strict_eligible and ingestion_nodes:
        ineligibility_reasons.append(
            "Some data-ingestion agents are not fully point-in-time faithful for strict historical replay."
        )

    return TeamExecutionProfile(
        team_classification=classification,
        has_prompt_override=has_prompt_override,
        has_synthesis_nodes=has_synthesis_nodes,
        backtest_strict_eligible=strict_eligible,
        backtest_experimental_eligible=experimental_eligible,
        paper_eligible=True,
        live_eligible=True,
        ineligibility_reasons=ineligibility_reasons,
        experimental_warnings=warnings,
    )


def _compute_node_mode_eligibility(node: TeamNode) -> NodeModeEligibility:
    reasons: list[str] = []
    strict_supported = True
    experimental_supported = True
    live_supported = True
    paper_supported = True

    if node.prompt_override is not None:
        strict_supported = False
        experimental_supported = False
        reasons.append("Manual prompt override disables historical replay for this node.")

    # Custom reasoning nodes (system_prompt set, not a data-ingestion node) are never strict-eligible
    if node.system_prompt and not _is_ingestion_node(node):
        strict_supported = False
        reasons.append("Custom reasoning node system_prompt disables strict backtest for this node.")

    for binding in node.capability_bindings:
        if binding.required and not binding.configured:
            strict_supported = False
            reasons.append(f"{binding.label} is not configured.")
        if not binding.strict_backtest_supported:
            strict_supported = False

    # Use data_domain (or agent_type as fallback) for historical support lookup
    effective_domain = node.data_domain or node.agent_type
    if _is_ingestion_node(node) and effective_domain and not node.capability_bindings:
        historical_support = _get_historical_support().get(effective_domain, {})
        if not historical_support.get("honored_in_strict", False):
            strict_supported = False

    return NodeModeEligibility(
        analyze=True,
        paper=paper_supported,
        live=live_supported,
        backtest_strict=strict_supported,
        backtest_experimental=experimental_supported,
        reasons=list(dict.fromkeys(reasons)),
    )


def _runtime_variant_id(agent_name: str, authored_variant_id: str | None) -> str:
    if not authored_variant_id:
        return "balanced"
    pack = PROMPT_PACKS_BY_AGENT.get(agent_name)
    if pack is None:
        return authored_variant_id
    valid_ids = {variant.variant_id for variant in pack.allowed_variants}
    if authored_variant_id in valid_ids:
        return authored_variant_id
    return "balanced"


# ── Compiler ──────────────────────────────────────────────────────────────────

def compile_topology_to_flat_team(
    draft: ArchitectureDraft,
    preferences: StrategyPreferences | None = None,
) -> CompiledTeam:
    """
    Main entry point: ArchitectureDraft → CompiledTeam.

    Validates the topology, compiles each analysis node into a CompiledAgentSpec,
    then assembles a CompiledTeam that is fully compatible with the existing
    orchestrator and backtest engine.
    """
    from backend.llm.strategy_builder import _compile_agent_spec  # local import to avoid circular

    topology = draft.topology
    intent = draft.intent
    prefs = preferences or intent.to_strategy_preferences()

    result = validate_topology(topology)
    if not result.valid:
        raise ValueError(
            f"Topology validation failed: {'; '.join(result.errors)}"
        )

    execution_profile = result.execution_profile

    # Build synthetic TeamDraft-like modifiers for _compile_agent_spec
    from backend.models.agent_team import TeamDraft  # local to avoid top-level circular

    # Build a synthetic TeamDraft for modifier resolution
    enabled_analysis = [
        (n.data_domain or n.agent_type)
        for n in topology.nodes
        if _is_ingestion_node(n) and (n.data_domain or n.agent_type) and n.enabled
    ]
    enabled_all = sorted(set(enabled_analysis) | REQUIRED_DECISION_AGENTS)

    weights: dict[str, int] = {}
    for node in topology.nodes:
        if _is_ingestion_node(node) and node.enabled:
            effective_domain = node.data_domain or node.agent_type
            if effective_domain:
                weights[node.display_name] = node.influence_weight
                weights[effective_domain] = max(weights.get(effective_domain, 0), node.influence_weight)

    # We need a TeamDraft for _compile_agent_spec; build minimal one
    risk_level = intent.risk_level or "moderate"
    time_horizon = intent.time_horizon or "medium"

    try:
        synthetic_draft = TeamDraft(
            name=draft.proposed_name or "Custom Team",
            description=draft.proposed_description or "",
            enabled_agents=enabled_all,
            agent_weights=weights,
            agent_modifiers={},
            risk_level=risk_level,
            time_horizon=time_horizon,
            asset_universe=intent.asset_universe,
            sector_exclusions=intent.sector_exclusions,
        )
    except Exception as exc:
        # Name validation failure — sanitize name
        import re
        safe_name = re.sub(r"[^a-zA-Z0-9\s\-_]", " ", draft.proposed_name or "Custom Team").strip()[:64] or "Custom Team"
        synthetic_draft = TeamDraft(
            name=safe_name,
            description=draft.proposed_description or "",
            enabled_agents=enabled_all,
            agent_weights=weights,
            agent_modifiers={},
            risk_level=risk_level,
            time_horizon=time_horizon,
            asset_universe=intent.asset_universe,
            sector_exclusions=intent.sector_exclusions,
        )

    # Compile each enabled data-ingestion node to a CompiledAgentSpec
    compiled_specs: dict[str, CompiledAgentSpec] = {}
    compiled_reasoning_specs: dict[str, CompiledReasoningSpec] = {}

    for node in topology.nodes:
        if not node.enabled:
            continue

        if _is_ingestion_node(node):
            # Data-ingestion path — use data_domain or agent_type for the fetcher
            agent_name = node.data_domain or node.agent_type
            if not agent_name or agent_name not in DATA_INGESTION_DOMAINS:
                continue
            synthetic_draft.agent_modifiers[agent_name] = {
                **synthetic_draft.agent_modifiers.get(agent_name, {}),
                **{
                    key: value
                    for key, value in node.modifiers.items()
                    if not str(key).startswith("__")
                },
                "variant_id": _runtime_variant_id(agent_name, node.variant_id),
            }
            spec = _compile_agent_spec(
                agent_name,
                node.influence_weight,
                prefs,
                synthetic_draft,
            )
            spec.modifiers["__role_label__"] = node.display_name
            spec.modifiers["__role_description__"] = node.role_description
            spec.modifiers["__capability_ids__"] = [binding.capability_id for binding in node.capability_bindings]
            spec.modifiers["__authored_variant__"] = node.variant_id
            # system_prompt takes precedence over prompt_contract
            effective_prompt = node.system_prompt or (
                node.prompt_contract.system_prompt_text if node.prompt_contract else ""
            )
            if effective_prompt:
                spec.modifiers["__custom_system_prompt__"] = effective_prompt
            if node.prompt_contract is not None:
                spec.modifiers["__allowed_evidence__"] = node.prompt_contract.allowed_evidence
                spec.modifiers["__forbidden_inference_rules__"] = node.prompt_contract.forbidden_inference_rules
                spec.modifiers["__required_output_schema__"] = node.prompt_contract.required_output_schema
                spec.modifiers["__operator_notes__"] = node.prompt_contract.operator_notes
            if node.prompt_override is not None:
                spec.modifiers["__prompt_override__"] = node.prompt_override.system_prompt_text
                spec.modifiers["__override_label__"] = node.prompt_override.label
                spec.modifiers["__custom_system_prompt__"] = node.prompt_override.system_prompt_text
            compiled_specs[node.node_id] = spec
            if agent_name not in compiled_specs:
                compiled_specs[agent_name] = spec

        else:
            # Custom reasoning / output / structural node
            input_node_ids = [
                e.source_node_id
                for e in topology.edges
                if e.target_node_id == node.node_id
            ]
            effective_prompt = node.system_prompt or (
                node.prompt_contract.system_prompt_text if node.prompt_contract else ""
            )
            if node.prompt_override is not None:
                effective_prompt = node.prompt_override.system_prompt_text
            output_schema = node.parameters.get("output_schema", "ReasoningOutput")
            # Backward compat: decision/risk family nodes default to PortfolioDecision output
            if node.node_family in ("decision", "risk") and not node.parameters.get("output_schema"):
                output_schema = "PortfolioDecision"
            compiled_reasoning_specs[node.node_id] = CompiledReasoningSpec(
                node_id=node.node_id,
                node_name=node.display_name,
                node_kind=node.node_kind or node.node_family,
                system_prompt=effective_prompt,
                parameters=dict(node.parameters),
                input_node_ids=input_node_ids,
                output_schema=output_schema,
                is_terminal=_is_terminal_node(node),
                is_data_ingestion=False,
                data_domain=None,
            )

    import re
    team_id_slug = re.sub(r"[^a-z0-9]+", "-", (draft.proposed_name or "custom-team").strip().lower()).strip("-")
    team_id = f"custom-{team_id_slug}"

    behavior_rules = draft.behavior_rules
    debate_enabled = behavior_rules.debate_enabled if behavior_rules else True
    min_conf = behavior_rules.min_confidence_threshold if behavior_rules else 0.55

    compiled = CompiledTeam(
        schema_version="compiled-team/v2-custom",
        team_id=team_id,
        version_number=0,
        name=synthetic_draft.name,
        description=synthetic_draft.description,
        enabled_agents=enabled_all,
        agent_weights=weights,
        compiled_agent_specs=compiled_specs,
        compiled_reasoning_specs=compiled_reasoning_specs,
        risk_level=risk_level,
        time_horizon=time_horizon,
        asset_universe=intent.asset_universe,
        sector_exclusions=intent.sector_exclusions,
        team_overrides={
            "enable_bull_bear_debate": debate_enabled,
            "min_confidence_threshold": min_conf,
        },
        team_classification=execution_profile.team_classification,
        topology=topology,
        behavior_rules=behavior_rules,
        execution_profile=execution_profile,
        validation_report=ValidationReport(
            valid=result.valid,
            warnings=result.warnings,
            normalized_fields=result.normalized_fields,
        ),
    )
    return compiled


# ── Topology hash ─────────────────────────────────────────────────────────────

def topology_hash(topology: TeamTopology) -> str:
    """sha256 of canonical JSON of topology nodes+edges, excluding visual_position."""
    nodes_payload = [
        {
            "node_id": n.node_id,
            "node_family": n.node_family,
            "agent_type": n.agent_type,
            "data_domain": n.data_domain,
            "enabled": n.enabled,
            "influence_weight": n.influence_weight,
            "variant_id": n.variant_id,
            "system_prompt": n.system_prompt,
            "parameters": n.parameters,
            "modifiers": n.modifiers,
            "has_prompt_override": n.prompt_override is not None,
        }
        for n in sorted(topology.nodes, key=lambda x: x.node_id)
    ]
    edges_payload = [
        {
            "edge_id": e.edge_id,
            "source_node_id": e.source_node_id,
            "target_node_id": e.target_node_id,
            "edge_type": e.edge_type,
        }
        for e in sorted(topology.edges, key=lambda x: x.edge_id)
    ]
    payload = {"nodes": nodes_payload, "edges": edges_payload}
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
