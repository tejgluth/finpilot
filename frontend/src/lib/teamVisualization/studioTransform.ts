import type {
  StudioMode,
  TeamEdge,
  TeamNode,
  TeamTopology,
  TeamValidationResult,
} from "../../api/types";
import { AGENT_META, agentLabel } from "./agentMeta";
import type {
  VisualizationEdge,
  VisualizationModel,
  VisualizationNode,
} from "./types";

/** Derive a stable visualization id from a topology node.
 *  In the studio we always use node_id so multiple custom roles can share the
 *  same grounded analysis agent without collapsing into one node. */
function nodeVizId(node: TeamNode): string {
  return node.node_id;
}

function edgeStrokeWidth(weight: number): number {
  if (weight <= 0) return 1;
  return Math.round(1 + (weight / 100) * 4);
}

function isIngestionNode(node: TeamNode): boolean {
  return Boolean(node.data_domain) || node.node_family === "analysis" || node.node_family === "data_ingestion";
}

function isTerminalNode(node: TeamNode): boolean {
  return Boolean(node.parameters?.is_terminal) || node.node_family === "decision" || node.node_family === "output";
}

function nodeDescription(node: TeamNode): string {
  if (node.role_description) return node.role_description;
  if (node.system_prompt) return node.system_prompt.slice(0, 120);
  const domain = node.data_domain ?? (isIngestionNode(node) ? node.agent_type : null);
  if (domain) return AGENT_META[domain]?.description ?? "";
  if (node.node_family === "risk" || node.node_family === "risk_manager") return AGENT_META["risk_manager"]?.description ?? "";
  if (node.node_family === "decision" || node.node_family === "portfolio_manager") return AGENT_META["portfolio_manager"]?.description ?? "";
  return "";
}

function nodeDataSources(node: TeamNode): string[] {
  if (node.owned_sources?.length) return node.owned_sources;
  const domain = node.data_domain ?? (isIngestionNode(node) ? node.agent_type : null);
  if (domain) return AGENT_META[domain]?.defaultSources ?? [];
  return [];
}

function perNodeMessages(
  node: TeamNode,
  validationResult: TeamValidationResult | null,
): string[] {
  if (!validationResult?.node_results) return node.validation_errors ?? [];
  // node_results is Record<string, string[]> — a flat list of messages per node
  return validationResult.node_results[node.node_id] ?? node.validation_errors ?? [];
}

function perNodeWarnings(
  node: TeamNode,
): string[] {
  return node.validation_warnings ?? [];
}

/** Map an AgentRole string from the node family */
function nodeRole(node: TeamNode): "analysis" | "decision" {
  if (isIngestionNode(node)) return "analysis";
  if (isTerminalNode(node)) return "decision";
  // Reasoning / middle nodes — treat as "analysis" for visual style
  return "analysis";
}

/**
 * Convert a TeamTopology (from ArchitectureDraft or CompiledTeam) into a
 * VisualizationModel usable by the studio graph.
 *
 * Unlike `compiledTeamToVisualizationModel` (which always shows all 7 analysis
 * agents), this only renders nodes that actually exist in the topology.
 */
export function topologyToVisualizationModel(
  topology: TeamTopology,
  validationResult: TeamValidationResult | null = null,
  _studioMode: StudioMode = "view",
): VisualizationModel {
  const nodes: VisualizationNode[] = [];
  const edges: VisualizationEdge[] = [];

  // Build a map from node_id → vizId for edge translation
  const nodeVizIdMap = new Map<string, string>();
  for (const node of topology.nodes) {
    nodeVizIdMap.set(node.node_id, nodeVizId(node));
  }

  // ── Nodes ────────────────────────────────────────────────────────────────
  for (const node of topology.nodes) {
    if (!node.enabled && node.node_family !== "analysis") {
      // Only analysis nodes can be disabled; others are structural
      // Still include them so graph stays complete
    }

    const vizId = nodeVizId(node);
    const nodeIsIngestion = isIngestionNode(node);
    const nodeIsTerminal = isTerminalNode(node);
    // nodeSubtype drives column placement in studioLayout
    const nodeSubtype = nodeIsTerminal
      ? "terminal"
      : nodeIsIngestion
        ? undefined
        : "reasoning";

    const vizNode: VisualizationNode = {
      id: vizId,
      label: node.display_name || agentLabel(vizId),
      role: nodeRole(node),
      enabled: node.enabled ?? true,
      weight: node.influence_weight ?? 60,
      variant: node.variant_id ?? "balanced",
      dataSources: nodeDataSources(node),
      freshnessMinutes: node.freshness_limit_minutes ?? 120,
      description: nodeDescription(node),
      diffStatus: "unchanged",
      defaultWeight: null,
      position: node.visual_position
        ? { x: node.visual_position.x, y: node.visual_position.y }
        : { x: 0, y: 0 },
      nodeSubtype,
      nodeId: node.node_id,
      nodeFamily: node.node_family,
      validationErrors: perNodeMessages(node, validationResult),
      validationWarnings: perNodeWarnings(node),
      hasPromptOverride: node.prompt_override != null,
    };

    nodes.push(vizNode);
  }

  // ── Edges ────────────────────────────────────────────────────────────────
  for (const edge of topology.edges) {
    const sourceVizId = nodeVizIdMap.get(edge.source_node_id);
    const targetVizId = nodeVizIdMap.get(edge.target_node_id);
    if (!sourceVizId || !targetVizId) continue;

    const sourceNode = nodes.find((n) => n.id === sourceVizId);
    const isSynthesisEdge = edge.edge_type === "synthesis";

    edges.push({
      id: edge.edge_id ?? `${sourceVizId}--${targetVizId}`,
      source: sourceVizId,
      target: targetVizId,
      strokeWidth: sourceNode?.enabled
        ? edgeStrokeWidth(sourceNode.weight)
        : 1,
      style: sourceNode?.enabled ? "solid" : "dashed",
      diffHighlight: isSynthesisEdge,
    });
  }

  const hasSynthesisNodes = topology.nodes.some(
    (n) => n.node_family === "synthesis",
  );
  const debateModeActive = false; // set from behavior_rules if present

  return {
    nodes,
    edges,
    debateModeActive,
    summary: "",
    riskLevel: "moderate",
    timeHorizon: "medium",
    sectorExclusions: [],
  };
}
