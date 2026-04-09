"""
Custom Team Builder — conversation-driven custom team architecture flow.

Parallel to strategy_builder.py for the premade/standard path.
Handles: conversation lifecycle, architecture intent extraction,
heuristic + LLM-assisted ArchitectureDraft generation, and compilation.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
import re
import json

from backend.agents.registry import (
    EXECUTABLE_ANALYSIS_AGENTS,
)
from backend.database import load_state, save_state
from backend.llm.capability_catalog import build_capability_catalog, build_capability_gaps, bindings_for_agent
from backend.llm.provider import get_llm_client
from backend.llm.strategy_builder import (
    extract_preferences,
    _raw_user_messages,
)
from backend.llm.topology_compiler import compile_topology_to_flat_team, validate_topology
from backend.models.agent_team import (
    ArchitectureConversationTurn,
    ArchitectureDraft,
    ArchitectureIntent,
    CapabilityGap,
    CompiledTeam,
    ConversationRequirement,
    CustomConversation,
    NodeModeEligibility,
    NodePromptContract,
    StrategyMessage,
    TeamBehaviorRules,
    TeamEdge,
    TeamNode,
    TeamTopology,
    TeamValidationResult,
    VisualPosition,
)
from backend.security.input_sanitizer import ContentSource, sanitize
from backend.security.output_validator import parse_llm_json
from backend.settings.user_settings import UserSettings, default_user_settings

CUSTOM_CONVERSATIONS_KEY = "custom_team_conversations_v1"
CUSTOM_BUILDER_TIMEOUT = 60.0  # Custom topology responses are large; 8s (strategy default) is too short

# Default weights for agents when building heuristic topology
_DEFAULT_WEIGHTS: dict[str, int] = {
    "fundamentals": 75,
    "technicals": 55,
    "sentiment": 35,
    "macro": 65,
    "value": 70,
    "momentum": 60,
    "growth": 65,
}

# Agent priority groups for intent-based selection
_AGENT_FACTOR_MAP: dict[str, list[str]] = {
    "quality": ["fundamentals", "value"],
    "value": ["value", "fundamentals"],
    "growth": ["growth", "fundamentals"],
    "momentum": ["momentum", "technicals"],
    "sentiment": ["sentiment"],
    "macro": ["macro"],
    "income": ["value"],
    "defensive": ["fundamentals", "macro", "value"],
}


def _now_iso_local() -> str:
    return datetime.now(UTC).isoformat()


# ── Storage helpers ───────────────────────────────────────────────────────────

async def _load_custom_conversations() -> dict[str, dict[str, Any]]:
    return await load_state(CUSTOM_CONVERSATIONS_KEY, {})


async def _save_custom_conversations(data: dict[str, dict[str, Any]]) -> None:
    await save_state(CUSTOM_CONVERSATIONS_KEY, data)


# ── Conversation lifecycle ────────────────────────────────────────────────────

async def create_custom_conversation(
    user_settings: UserSettings,
    seed_prompt: str | None = None,
) -> CustomConversation:
    conv = CustomConversation(created_at=_now_iso_local(), updated_at=_now_iso_local())
    raw = await _load_custom_conversations()

    if seed_prompt:
        raw[conv.conversation_id] = conv.model_dump(mode="json")
        await _save_custom_conversations(raw)
        conv, _, _, _ = await process_custom_message(
            conv.conversation_id, seed_prompt, request_compile=False, user_settings=user_settings
        )
    else:
        raw[conv.conversation_id] = conv.model_dump(mode="json")
        await _save_custom_conversations(raw)

    return conv


async def get_custom_conversation(conversation_id: str) -> CustomConversation | None:
    raw = await _load_custom_conversations()
    payload = raw.get(conversation_id)
    return CustomConversation.model_validate(payload) if payload else None


async def list_custom_conversations() -> list[CustomConversation]:
    raw = await _load_custom_conversations()
    convs = [CustomConversation.model_validate(v) for v in raw.values()]
    return sorted(convs, key=lambda c: c.updated_at, reverse=True)


# ── Intent extraction ─────────────────────────────────────────────────────────

def extract_architecture_intent(messages: list[StrategyMessage]) -> ArchitectureIntent:
    """Extract ArchitectureIntent from conversation messages."""
    # First use the existing preference extractor
    base_prefs = extract_preferences(messages)
    user_text = _raw_user_messages(messages).lower()
    normalized = re.sub(r"[^a-z0-9.\s%-]+", " ", user_text)

    intent = ArchitectureIntent(
        goal_summary=base_prefs.goal_summary,
        risk_level=base_prefs.risk_level,
        time_horizon=base_prefs.time_horizon,
        asset_universe=base_prefs.asset_universe,
        sector_exclusions=base_prefs.sector_exclusions,
        preferred_factors=base_prefs.preferred_factors,
        deemphasized_factors=base_prefs.deemphasized_factors,
        disabled_agents=base_prefs.disabled_agents,
        source_preferences=base_prefs.source_preferences,
        style_tags=base_prefs.style_tags,
        agent_modifier_preferences=base_prefs.agent_modifier_preferences,
        backtest_mode_default=base_prefs.backtest_mode_default,
        unresolved_items=base_prefs.unresolved_items,
    )

    # Topology intent extraction
    # Complexity
    if any(tok in normalized for tok in ["simple", "minimal", "lean", "lightweight"]):
        intent.desired_complexity = "simple"
    elif any(tok in normalized for tok in ["complex", "advanced", "comprehensive", "sophisticated"]):
        intent.desired_complexity = "complex"

    # Node count
    count_match = re.search(
        r"(\d+)\s*(?:analysis\s*)?agents?|(\d+)\s*(?:different\s*)?factors?", normalized
    )
    if count_match:
        raw_count = int(count_match.group(1) or count_match.group(2))
        if 1 <= raw_count <= 7:
            intent.desired_analysis_node_count = raw_count

    # Synthesis / debate
    if any(tok in normalized for tok in ["synthesis", "synthesize", "aggregat", "combine"]):
        intent.wants_synthesis_stage = True
    if any(tok in normalized for tok in ["no debate", "skip debate", "no bull bear", "without debate"]):
        intent.wants_debate_stage = False
    elif any(tok in normalized for tok in ["debate", "bull bear", "bullish bearish"]):
        intent.wants_debate_stage = True

    # Consensus rules (natural language capture)
    consensus_patterns = [
        r"require\s+(?:agreement|consensus)\s+(?:between|among)\s+(.+?)(?:\.|$)",
        r"must\s+agree(?:\s+between\s+(.+?))?(?:\.|$)",
        r"consensus\s+(?:from|of)\s+(.+?)(?:\.|$)",
    ]
    for pattern in consensus_patterns:
        m = re.search(pattern, normalized)
        if m and m.group(1):
            intent.consensus_rules_natural_language.append(m.group(1).strip()[:100])

    # Manual control level
    if any(tok in normalized for tok in ["full control", "manual", "hands on", "i want to configure"]):
        intent.manual_control_level = "high"
    elif any(tok in normalized for tok in ["automatic", "hands off", "let the system"]):
        intent.manual_control_level = "low"

    # Prompt editing
    if any(tok in normalized for tok in ["edit prompt", "custom prompt", "prompt override", "advanced prompt"]):
        intent.wants_prompt_editing = True

    # Custom name / description
    name_match = re.search(r'(?:call it|name it|named?)\s+"?([a-z0-9 _-]{3,40})"?', normalized)
    if name_match:
        intent.custom_team_name = name_match.group(1).strip().title()

    return intent


# ── Heuristic draft ───────────────────────────────────────────────────────────

def _heuristic_architecture_draft(
    intent: ArchitectureIntent,
    user_settings: UserSettings | None = None,
) -> ArchitectureDraft:
    """Build a deterministic ArchitectureDraft from ArchitectureIntent."""
    from uuid import uuid4

    settings = user_settings or default_user_settings()
    weights = dict(_DEFAULT_WEIGHTS)
    enabled_agents: list[str] = list(EXECUTABLE_ANALYSIS_AGENTS)

    # Apply factor preferences
    for factor in intent.preferred_factors:
        for agent in _AGENT_FACTOR_MAP.get(factor, []):
            if agent in weights:
                weights[agent] = min(100, weights[agent] + 15)
    for factor in intent.deemphasized_factors:
        for agent in _AGENT_FACTOR_MAP.get(factor, []):
            if agent in weights:
                weights[agent] = max(0, weights[agent] - 20)
    for agent in intent.disabled_agents:
        if agent in enabled_agents:
            enabled_agents.remove(agent)
        weights[agent] = 0

    # Risk adjustments
    risk_level = intent.risk_level or "moderate"
    if risk_level == "conservative":
        for a in ("fundamentals", "value", "macro"):
            weights[a] = min(100, weights[a] + 10)
        for a in ("sentiment", "momentum"):
            weights[a] = max(10, weights[a] - 10)
    elif risk_level == "aggressive":
        for a in ("growth", "momentum", "technicals", "sentiment"):
            weights[a] = min(100, weights[a] + 10)
        weights["macro"] = max(20, weights["macro"] - 10)

    # Horizon adjustments
    horizon = intent.time_horizon or "medium"
    if horizon == "short":
        for a in ("technicals", "momentum", "sentiment"):
            weights[a] = min(100, weights[a] + 12)
        for a in ("value", "macro"):
            weights[a] = max(10, weights[a] - 10)
    elif horizon == "long":
        for a in ("fundamentals", "value", "growth", "macro"):
            weights[a] = min(100, weights[a] + 10)
        weights["sentiment"] = max(10, weights["sentiment"] - 10)

    # Complexity → node count
    max_agents = 7
    if intent.desired_complexity == "simple":
        max_agents = 3
    elif intent.desired_complexity == "moderate":
        max_agents = 5

    if intent.desired_analysis_node_count is not None:
        max_agents = min(7, max(1, intent.desired_analysis_node_count))

    # Select top agents by weight
    sorted_agents = sorted(
        [a for a in enabled_agents if weights.get(a, 0) > 0],
        key=lambda a: -weights.get(a, 0),
    )
    selected = sorted_agents[:max_agents]

    # Build nodes
    nodes: list[TeamNode] = []
    node_ids: dict[str, str] = {}  # agent_name → node_id

    # Analysis nodes (laid out left column)
    x_analysis = 100.0
    y_step = 120.0
    y_start = 60.0
    mid_y = y_start + (max(len(selected) - 1, 0) / 2) * y_step

    for i, agent in enumerate(selected):
        nid = f"node-{agent}-{uuid4().hex[:6]}"
        node_ids[agent] = nid
        bindings = bindings_for_agent(agent, settings)
        nodes.append(TeamNode(
            node_id=nid,
            display_name=f"{agent.replace('_', ' ').title()} Analyst",
            node_family="data_ingestion",
            agent_type=agent,
            data_domain=agent,
            system_prompt=(
                f"You are the {agent.replace('_', ' ')} specialist inside a custom investment team. "
                "Analyze only the data provided to you. Cite every data point you use. "
                "State uncertainty explicitly when data is missing or stale. "
                "Produce a grounded AgentSignal as output."
            ),
            role_description=f"Fetches and interprets {agent.replace('_', ' ')} data to produce an evidence-backed signal.",
            enabled=True,
            visual_position=VisualPosition(x=x_analysis, y=y_start + i * y_step),
            influence_weight=weights.get(agent, 50),
            variant_id=intent.agent_modifier_preferences.get(agent, {}).get("variant_id", "balanced"),
            capability_bindings=bindings,
            prompt_contract=NodePromptContract(
                system_prompt_text=(
                    f"You are the {agent.replace('_', ' ')} specialist inside a custom investment architecture. "
                    "Stick to bound capabilities only, cite what you use, and state uncertainty explicitly."
                ),
                allowed_evidence=[binding.capability_id for binding in bindings],
                forbidden_inference_rules=[
                    "Do not cite or imply capabilities that are not bound to this node.",
                    "Do not infer unavailable geopolitical facts, earnings figures, or macro data from memory.",
                ],
                required_output_schema="AgentSignal",
            ),
        ))

    # Optional synthesis reasoning node
    synthesis_id: str | None = None
    if intent.wants_synthesis_stage or len(selected) > 3:
        synthesis_id = f"node-synthesis-{uuid4().hex[:6]}"
        nodes.append(TeamNode(
            node_id=synthesis_id,
            display_name="Signal Aggregator",
            node_family="reasoning",
            node_kind="aggregator",
            agent_type=None,
            data_domain=None,
            system_prompt=(
                "You receive multiple upstream agent signals as JSON. "
                "Synthesize them into a single directional view. "
                "Compute a weighted confidence score across BUY/SELL/HOLD signals. "
                "Identify points of agreement and disagreement. "
                "Output a ReasoningOutput with your recommendation, confidence, and reasoning."
            ),
            parameters={
                "output_schema": "ReasoningOutput",
                "temperature": 0.3,
                "max_tokens": 600,
                "input_merge": "concatenate",
                "is_terminal": False,
            },
            role_description="Aggregates upstream signals into a unified directional view.",
            enabled=True,
            visual_position=VisualPosition(x=380.0, y=mid_y),
            influence_weight=100,
        ))

    # Terminal output node
    terminal_id = f"node-output-{uuid4().hex[:6]}"
    x_terminal = 560.0 if synthesis_id else 420.0
    nodes.append(TeamNode(
        node_id=terminal_id,
        display_name="Portfolio Decision",
        node_family="output",
        node_kind="terminal",
        agent_type=None,
        data_domain=None,
        system_prompt=(
            "You are the final decision node in this investment team. "
            "You receive all upstream agent signals and reasoning outputs as JSON. "
            "Based on the combined evidence, produce a final portfolio decision: BUY, SELL, or HOLD. "
            "Set a confidence between 0 and 1. Provide a clear, concise rationale citing the key signals that drove your decision. "
            "Output must be valid JSON matching the PortfolioDecision schema."
        ),
        parameters={
            "output_schema": "PortfolioDecision",
            "temperature": 0.2,
            "max_tokens": 800,
            "input_merge": "concatenate",
            "is_terminal": True,
        },
        role_description="Aggregates all upstream evidence into the final BUY/SELL/HOLD decision.",
        enabled=True,
        visual_position=VisualPosition(x=x_terminal, y=mid_y),
        influence_weight=100,
    ))

    # Build edges
    edges: list[TeamEdge] = []
    intermediate = synthesis_id or terminal_id

    for agent in selected:
        nid = node_ids[agent]
        edges.append(TeamEdge(
            source_node_id=nid,
            target_node_id=intermediate,
            edge_type="signal",
        ))

    if synthesis_id:
        edges.append(TeamEdge(
            source_node_id=synthesis_id,
            target_node_id=terminal_id,
            edge_type="reasoning",
        ))

    topology = TeamTopology(nodes=nodes, edges=edges)

    behavior_rules = TeamBehaviorRules(
        debate_enabled=intent.wants_debate_stage,
        min_confidence_threshold=0.55 if risk_level != "aggressive" else 0.50,
    )

    # Build name
    name_parts = []
    if intent.custom_team_name:
        proposed_name = intent.custom_team_name[:64]
    else:
        if risk_level:
            name_parts.append(risk_level.capitalize())
        if intent.preferred_factors:
            name_parts.extend(f.capitalize() for f in intent.preferred_factors[:2])
        elif intent.style_tags:
            name_parts.append(intent.style_tags[0].capitalize())
        else:
            name_parts.append("Custom")
        name_parts.append("Team")
        proposed_name = " ".join(dict.fromkeys(name_parts))

    description = (
        f"{horizon.capitalize()}-horizon custom team with "
        f"{len(selected)} analysis agents."
    )

    # Build follow-up question if intent is unresolved
    follow_up: str | None = None
    if not intent.risk_level and not intent.time_horizon:
        follow_up = "What risk level (conservative/moderate/aggressive) and time horizon (short/medium/long) should this team use?"
    elif not intent.risk_level:
        follow_up = "What risk level should this team target: conservative, moderate, or aggressive?"
    elif not intent.time_horizon:
        follow_up = "What time horizon: short, medium, or long?"
    elif not intent.preferred_factors and not intent.style_tags and intent.desired_analysis_node_count is None:
        follow_up = "Which factor areas matter most to you — fundamentals, value, growth, momentum, macro, or sentiment?"

    return ArchitectureDraft(
        conversation_id="",  # set by caller
        intent=intent,
        topology=topology,
        behavior_rules=behavior_rules,
        rationale=(
            "Deterministic heuristic draft based on your stated preferences. "
            "The architect LLM can replace every role label, prompt contract, and edge pattern when available."
        ),
        follow_up_question=follow_up,
        unresolved_items=intent.unresolved_items,
        proposed_name=proposed_name,
        proposed_description=description,
    )


# ── LLM-assisted draft ────────────────────────────────────────────────────────

def _requirement_question(requirement_id: str) -> str:
    return {
        "risk_level": "What risk level should this team target: conservative, moderate, or aggressive?",
        "time_horizon": "What time horizon should this team target: short, medium, or long?",
        "primary_factors": "Which evidence lanes matter most here: fundamentals, macro, sentiment, technicals, value, momentum, or growth?",
    }.get(requirement_id, "What else should the architect lock down before compiling this team?")


def _build_requirement_state(intent: ArchitectureIntent) -> tuple[list[ConversationRequirement], list[ConversationRequirement]]:
    resolved: list[ConversationRequirement] = []
    open_items: list[ConversationRequirement] = []
    if intent.risk_level:
        resolved.append(ConversationRequirement(
            requirement_id="risk_level",
            label="Risk Level",
            value=intent.risk_level,
            status="resolved",
            source="user",
        ))
    else:
        open_items.append(ConversationRequirement(
            requirement_id="risk_level",
            label="Risk Level",
            question=_requirement_question("risk_level"),
            status="open",
            source="system",
        ))
    if intent.time_horizon:
        resolved.append(ConversationRequirement(
            requirement_id="time_horizon",
            label="Time Horizon",
            value=intent.time_horizon,
            status="resolved",
            source="user",
        ))
    else:
        open_items.append(ConversationRequirement(
            requirement_id="time_horizon",
            label="Time Horizon",
            question=_requirement_question("time_horizon"),
            status="open",
            source="system",
        ))
    if intent.preferred_factors:
        resolved.append(ConversationRequirement(
            requirement_id="primary_factors",
            label="Primary Evidence Lanes",
            value=", ".join(intent.preferred_factors),
            status="resolved",
            source="user",
        ))
    else:
        open_items.append(ConversationRequirement(
            requirement_id="primary_factors",
            label="Primary Evidence Lanes",
            question=_requirement_question("primary_factors"),
            status="open",
            source="system",
        ))
    return resolved, open_items


def _mode_compatibility_from_validation(result: TeamValidationResult) -> NodeModeEligibility:
    profile = result.execution_profile
    return NodeModeEligibility(
        analyze=True,
        paper=profile.paper_eligible,
        live=profile.live_eligible,
        backtest_strict=profile.backtest_strict_eligible,
        backtest_experimental=profile.backtest_experimental_eligible,
        reasons=[*profile.ineligibility_reasons, *profile.experimental_warnings],
    )


def _summarize_graph_changes(
    previous_draft: ArchitectureDraft | None,
    next_draft: ArchitectureDraft,
) -> list[str]:
    if previous_draft is None:
        analysis_count = sum(1 for node in next_draft.topology.nodes if node.data_domain or node.node_family == "analysis")
        return [f"Created an initial graph with {analysis_count} data ingestion node{'s' if analysis_count != 1 else ''}."]
    previous_nodes = {node.node_id: node for node in previous_draft.topology.nodes}
    next_nodes = {node.node_id: node for node in next_draft.topology.nodes}
    changes: list[str] = []
    added = [node.display_name for node_id, node in next_nodes.items() if node_id not in previous_nodes]
    removed = [node.display_name for node_id, node in previous_nodes.items() if node_id not in next_nodes]
    renamed = [
        f"{previous_nodes[node_id].display_name} -> {node.display_name}"
        for node_id, node in next_nodes.items()
        if node_id in previous_nodes and previous_nodes[node_id].display_name != node.display_name
    ]
    if added:
        changes.append("Added nodes: " + ", ".join(added[:4]) + ".")
    if removed:
        changes.append("Removed nodes: " + ", ".join(removed[:4]) + ".")
    if renamed:
        changes.append("Renamed roles: " + ", ".join(renamed[:4]) + ".")
    edge_delta = len(next_draft.topology.edges) - len(previous_draft.topology.edges)
    if edge_delta > 0:
        changes.append(f"Added {edge_delta} routing connection{'s' if edge_delta != 1 else ''}.")
    elif edge_delta < 0:
        changes.append(f"Removed {abs(edge_delta)} routing connection{'s' if edge_delta != -1 else ''}.")
    return changes or ["Kept the current graph skeleton and refined role prompts or routing emphasis."]


class ArchitectConversationResponse(ArchitectureDraft):
    assistant_message: str = ""
    resolved_requirements: list[ConversationRequirement] = []
    open_questions: list[ConversationRequirement] = []
    graph_change_summary: list[str] = []
    capability_gaps: list[CapabilityGap] = []


def _build_fallback_turn(
    *,
    intent: ArchitectureIntent,
    draft: ArchitectureDraft,
    previous_draft: ArchitectureDraft | None,
    user_settings: UserSettings,
    fallback_reason: str | None = None,
) -> ArchitectureConversationTurn:
    validation = validate_topology(draft.topology)
    draft.validation_result = validation
    resolved_requirements, open_questions = _build_requirement_state(intent)
    seen_gap_ids: set[str] = set()
    capability_gaps: list[CapabilityGap] = []
    for node in draft.topology.nodes:
        domain = node.data_domain or (node.agent_type if node.node_family == "analysis" else None)
        if not domain:
            continue
        for gap in build_capability_gaps(domain, user_settings):
            if gap.capability_id in seen_gap_ids:
                continue
            seen_gap_ids.add(gap.capability_id)
            capability_gaps.append(gap)
    ingestion_count = sum(1 for node in draft.topology.nodes if node.data_domain or node.node_family == "analysis")
    assistant_parts = [
        f"I designed {draft.proposed_name} as a custom graph with {ingestion_count} data ingestion node{'s' if ingestion_count != 1 else ''}.",
    ]
    if fallback_reason:
        assistant_parts.insert(0, fallback_reason.strip())
    if capability_gaps:
        assistant_parts.append(
            "Some richer role ideas still depend on data that is not configured yet, so this version keeps a grounded degraded path available with the current sources."
        )
    assistant_parts.append(open_questions[0].question if open_questions else "The graph is coherent enough to compile and inspect now.")
    return ArchitectureConversationTurn(
        assistant_message=" ".join(assistant_parts),
        resolved_requirements=resolved_requirements,
        open_questions=open_questions[:2],
        graph_change_summary=_summarize_graph_changes(previous_draft, draft),
        capability_gaps=capability_gaps,
        mode_compatibility=_mode_compatibility_from_validation(validation),
        validation_state=validation,
    )


async def _model_architecture_draft(
    intent: ArchitectureIntent,
    user_settings: UserSettings,
    fallback: ArchitectureDraft,
    previous_draft: ArchitectureDraft | None = None,
) -> tuple[ArchitectureDraft, ArchitectureConversationTurn]:
    """Ask the architect LLM to author the next custom-team conversation turn."""
    client = get_llm_client(user_settings.llm)
    if not client.available:
        return fallback, _build_fallback_turn(
            intent=intent,
            draft=fallback,
            previous_draft=previous_draft,
            user_settings=user_settings,
            fallback_reason="The live architect model is unavailable right now, so this turn is using a deterministic fallback scaffold.",
        )

    from backend.llm.budget import BudgetTracker

    budget = BudgetTracker(
        max_cost_usd=user_settings.llm.max_cost_per_session_usd,
        max_tokens=user_settings.llm.max_tokens_per_request,
    )

    system = (
        "You are FinPilot's custom investment team architect. "
        "Your job is to author a complete investment team as a directed acyclic graph (DAG). "
        "Return JSON matching ArchitectConversationResponse.\n\n"

        "## Graph structure\n"
        "The graph has two layers:\n\n"

        "### Layer 1 — Data Ingestion (BOUNDED)\n"
        "These nodes fetch real market data. They are identified by having `data_domain` set.\n"
        "`data_domain` MUST be one of exactly these 7 strings: fundamentals, technicals, sentiment, macro, value, momentum, growth.\n"
        "You may create multiple data-ingestion nodes with different domains.\n"
        "For data-ingestion nodes: set `node_family` to 'data_ingestion', set `data_domain`, set `agent_type` to the same value as data_domain.\n"
        "Every data-ingestion node needs a `system_prompt` describing what focus/angle it should take on the data it receives.\n"
        "Every data-ingestion node needs `capability_bindings` matching the provided capability catalog for its data_domain.\n\n"

        "### Layer 2 — Custom Reasoning (UNBOUNDED)\n"
        "These nodes have NO `data_domain` (leave it null/absent). You invent everything about them.\n"
        "Set `node_family` to any descriptive string you choose (e.g. 'reasoning', 'filter', 'aggregator', 'output').\n"
        "Set a meaningful `system_prompt` that defines exactly what this node does with its upstream inputs.\n"
        "Set `parameters` dict with at minimum: `output_schema` (one of: 'ReasoningOutput', 'PortfolioDecision', 'AgentSignal'), "
        "`temperature` (float 0.0-1.0), `max_tokens` (int 100-1500), `input_merge` ('concatenate' or 'first_only').\n"
        "You may create as many or as few reasoning nodes as the strategy requires. Examples (not required): "
        "ranking layers, consensus filters, alpha selectors, risk reviewers, scenario analyzers, sector screens, conviction aggregators.\n\n"

        "### Terminal output node (REQUIRED)\n"
        "Exactly ONE node must be the final output node. On that node:\n"
        "- Set `parameters.is_terminal` to `true`\n"
        "- Set `parameters.output_schema` to `'PortfolioDecision'`\n"
        "- Write a `system_prompt` that instructs the node to synthesize all upstream inputs and produce a final BUY/SELL/HOLD decision with confidence and reasoning.\n\n"

        "## Graph rules\n"
        "- The topology must be a valid DAG (no cycles).\n"
        "- Every non-source node must have at least one incoming edge.\n"
        "- Source nodes (no incoming edges) must ALL be data-ingestion nodes.\n"
        "- There must be a directed path from at least one data-ingestion node to the terminal node.\n"
        "- Exactly one terminal node (parameters.is_terminal=true).\n\n"

        "## What you must NOT do\n"
        "- Do NOT impose any fixed downstream architecture. Do not require a risk node, debate node, synthesis node, or portfolio_manager. Invent the architecture that fits the strategy.\n"
        "- Do NOT set data_domain to anything outside the 7 known domains.\n"
        "- Do NOT use agent_type for non-ingestion nodes.\n\n"

        "## Output contract\n"
        "Return ArchitectConversationResponse JSON with: proposed_name, proposed_description, topology (nodes[], edges[]), "
        "assistant_message (natural language reply to the user), open_questions[] (ConversationRequirement items, max 2), "
        "graph_change_summary[] (list of strings), capability_gaps[].\n\n"
        "Do not repeat a question that is already resolved. Ask at most two open questions per turn. "
        "If a requested capability depends on data not configured, explain the degraded architecture and include capability_gaps. "
        "Design the architecture specifically for the user's strategy thesis — avoid copying the fallback scaffold unless it genuinely fits."
    )
    user_payload = json.dumps({
        "intent": intent.model_dump(mode="json"),
        "capability_catalog": build_capability_catalog(user_settings),
        "minimum_valid_fallback": fallback.model_dump(mode="json"),
        "previous_draft": previous_draft.model_dump(mode="json") if previous_draft else None,
        "resolved_requirements": [item.model_dump(mode="json") for item in _build_requirement_state(intent)[0]],
    }, indent=2)

    try:
        async with asyncio.timeout(CUSTOM_BUILDER_TIMEOUT):
            raw = await client.chat(
                system=system,
                messages=[{"role": "user", "content": user_payload}],
                max_tokens=min(2500, user_settings.llm.max_tokens_per_request),
                temperature=user_settings.llm.temperature_strategy,
                budget=budget,
            )
        parsed = parse_llm_json(raw, ArchitectConversationResponse)
        draft = ArchitectureDraft.model_validate(parsed.model_dump(exclude={
            "assistant_message",
            "resolved_requirements",
            "open_questions",
            "graph_change_summary",
            "capability_gaps",
        }))
        result = validate_topology(draft.topology)
        if not result.valid:
            fallback_turn = _build_fallback_turn(
                intent=intent,
                draft=fallback,
                previous_draft=previous_draft,
                user_settings=user_settings,
                fallback_reason="The architect proposed an invalid graph, so I fell back to a minimal valid scaffold for this turn.",
            )
            if parsed.assistant_message.strip():
                fallback_turn.assistant_message = parsed.assistant_message.strip()
            return fallback, fallback_turn
        draft.validation_result = result
        resolved_requirements = parsed.resolved_requirements or _build_requirement_state(draft.intent)[0]
        open_questions = [item for item in (parsed.open_questions or _build_requirement_state(draft.intent)[1]) if item.status == "open"][:2]
        seen_gap_ids: set[str] = set()
        capability_gaps: list[CapabilityGap] = []
        for gap in parsed.capability_gaps:
            if gap.capability_id in seen_gap_ids:
                continue
            seen_gap_ids.add(gap.capability_id)
            capability_gaps.append(gap)
        for node in draft.topology.nodes:
            domain = node.data_domain or (node.agent_type if node.node_family == "analysis" else None)
            if not domain:
                continue
            for gap in build_capability_gaps(domain, user_settings):
                if gap.capability_id in seen_gap_ids:
                    continue
                seen_gap_ids.add(gap.capability_id)
                capability_gaps.append(gap)
        draft.follow_up_question = open_questions[0].question if open_questions else None
        draft.unresolved_items = [item.requirement_id for item in open_questions]
        turn = ArchitectureConversationTurn(
            assistant_message=parsed.assistant_message.strip() or _build_fallback_turn(
                intent=draft.intent,
                draft=draft,
                previous_draft=previous_draft,
                user_settings=user_settings,
            ).assistant_message,
            resolved_requirements=resolved_requirements,
            open_questions=open_questions,
            graph_change_summary=parsed.graph_change_summary or _summarize_graph_changes(previous_draft, draft),
            capability_gaps=capability_gaps,
            mode_compatibility=_mode_compatibility_from_validation(result),
            validation_state=result,
        )
        return draft, turn
    except TimeoutError:
        return fallback, _build_fallback_turn(
            intent=intent,
            draft=fallback,
            previous_draft=previous_draft,
            user_settings=user_settings,
            fallback_reason="The architect model timed out before producing a response. Using a heuristic scaffold — try again or simplify the request.",
        )
    except Exception:
        return fallback, _build_fallback_turn(
            intent=intent,
            draft=fallback,
            previous_draft=previous_draft,
            user_settings=user_settings,
            fallback_reason="The architect model could not produce a valid response for this turn. Using a heuristic scaffold.",
        )


# ── Message processor ─────────────────────────────────────────────────────────

async def process_custom_message(
    conversation_id: str,
    content: str,
    request_compile: bool,
    user_settings: UserSettings,
) -> tuple[CustomConversation, ArchitectureDraft, CompiledTeam | None, bool]:
    """Process a user message in a custom conversation."""
    conv = await get_custom_conversation(conversation_id)
    if conv is None:
        raise ValueError(f"Unknown custom conversation: {conversation_id}")

    sanitized = sanitize(content, ContentSource.USER_STRATEGY_INPUT)
    conv.messages.append(StrategyMessage(
        role="user",
        content=content,
        sanitized_content=sanitized.sanitized_text,
        timestamp=_now_iso_local(),
        message_type="input",
    ))
    conv.updated_at = _now_iso_local()

    intent = extract_architecture_intent(conv.messages)
    conv.intent = intent

    previous_draft = conv.latest_draft
    heuristic = _heuristic_architecture_draft(intent, user_settings)
    heuristic.conversation_id = conversation_id

    model_draft, turn = await _model_architecture_draft(intent, user_settings, heuristic, previous_draft)
    model_draft.conversation_id = conversation_id

    # Determine follow-up
    needs_follow_up = bool(turn.open_questions)
    if not model_draft.follow_up_question and turn.open_questions:
        model_draft.follow_up_question = turn.open_questions[0].question

    conv.latest_draft = model_draft
    conv.latest_turn = turn
    conv.status = "draft_ready" if not needs_follow_up else "collecting_requirements"

    # Assistant reply
    assistant_text = turn.assistant_message
    msg_type = "follow_up" if needs_follow_up else "draft"
    conv.messages.append(StrategyMessage(
        role="assistant",
        content=assistant_text,
        sanitized_content=assistant_text,
        timestamp=_now_iso_local(),
        message_type=msg_type,
    ))

    # Compile if requested and prefs resolved
    compiled: CompiledTeam | None = None
    if request_compile or not needs_follow_up:
        try:
            compiled = compile_topology_to_flat_team(model_draft, intent.to_strategy_preferences())
            conv.status = "compiled"
        except Exception:
            pass

    # Persist
    raw = await _load_custom_conversations()
    raw[conversation_id] = conv.model_dump(mode="json")
    await _save_custom_conversations(raw)

    return conv, model_draft, compiled, needs_follow_up


async def compile_custom_conversation(
    conversation_id: str,
    user_settings: UserSettings,
) -> tuple[CustomConversation, ArchitectureDraft, CompiledTeam]:
    """Force compile a custom conversation into a CompiledTeam."""
    conv = await get_custom_conversation(conversation_id)
    if conv is None:
        raise ValueError(f"Unknown custom conversation: {conversation_id}")

    intent = extract_architecture_intent(conv.messages)
    conv.intent = intent
    previous_draft = conv.latest_draft
    heuristic = _heuristic_architecture_draft(intent, user_settings)
    heuristic.conversation_id = conversation_id
    model_draft, turn = await _model_architecture_draft(intent, user_settings, heuristic, previous_draft)
    model_draft.conversation_id = conversation_id

    prefs = intent.to_strategy_preferences()
    compiled = compile_topology_to_flat_team(model_draft, prefs)

    model_draft.validation_result = validate_topology(model_draft.topology)
    conv.latest_draft = model_draft
    turn.validation_state = model_draft.validation_result
    turn.mode_compatibility = _mode_compatibility_from_validation(model_draft.validation_result)
    conv.latest_turn = turn
    conv.status = "compiled"

    raw = await _load_custom_conversations()
    raw[conversation_id] = conv.model_dump(mode="json")
    await _save_custom_conversations(raw)

    return conv, model_draft, compiled
