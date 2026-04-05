import type { CompiledTeam, TeamComparison } from "../../api/types";
import {
  AGENT_META,
  ANALYSIS_AGENT_IDS,
  DECISION_AGENT_IDS,
  agentLabel,
} from "./agentMeta";
import type {
  AgentDiffStatus,
  VisualizationEdge,
  VisualizationModel,
  VisualizationNode,
} from "./types";

function resolveDiffStatus(
  agentId: string,
  enabled: boolean,
  comparison: TeamComparison | null,
): AgentDiffStatus {
  if (!comparison) return enabled ? "unchanged" : "disabled";

  const added: string[] = (comparison.agent_diff["added"] as string[]) ?? [];
  const removed: string[] = (comparison.agent_diff["removed"] as string[]) ?? [];

  if (added.includes(agentId)) return "added";
  if (removed.includes(agentId)) return "removed";
  if (!enabled) return "disabled";

  const weightEntry = comparison.weight_diff[agentId];
  if (weightEntry) {
    return weightEntry.candidate > weightEntry.default ? "weight-up" : "weight-down";
  }
  return "unchanged";
}

function edgeStrokeWidth(weight: number): number {
  if (weight <= 0) return 1;
  return Math.round(1 + (weight / 100) * 4);
}

function buildSummary(team: CompiledTeam): string {
  const activeAgents = ANALYSIS_AGENT_IDS.filter((id) =>
    team.enabled_agents.includes(id),
  );
  const debateOn = team.team_overrides["enable_bull_bear_debate"] === true;

  let agentList: string;
  if (activeAgents.length === 0) {
    agentList = "no analysis agents";
  } else if (activeAgents.length <= 3) {
    agentList = activeAgents.map(agentLabel).join(", ");
  } else {
    agentList = `${activeAgents
      .slice(0, 3)
      .map(agentLabel)
      .join(", ")} + ${activeAgents.length - 3} more`;
  }

  const exclusionNote =
    team.sector_exclusions.length > 0
      ? ` Excluded sectors: ${team.sector_exclusions
          .map((s) => s.replace(/_/g, " "))
          .join(", ")}.`
      : "";

  const debateNote = debateOn ? " Bull/bear debate enabled." : "";

  const riskLabel =
    team.risk_level.charAt(0).toUpperCase() + team.risk_level.slice(1);
  const horizonLabel =
    team.time_horizon.charAt(0).toUpperCase() + team.time_horizon.slice(1);

  return `${riskLabel} risk, ${horizonLabel.toLowerCase()}-term horizon. Signals from: ${agentList}.${debateNote}${exclusionNote}`;
}

export function compiledTeamToVisualizationModel(
  team: CompiledTeam,
  comparison: TeamComparison | null = null,
): VisualizationModel {
  const nodes: VisualizationNode[] = [];
  const edges: VisualizationEdge[] = [];

  // ── Analysis nodes (all 7 always present; disabled ones are ghosted) ──────
  for (const id of ANALYSIS_AGENT_IDS) {
    const spec = team.compiled_agent_specs[id];
    const enabled = team.enabled_agents.includes(id);
    const weight = team.agent_weights[id] ?? 0;
    const meta = AGENT_META[id];

    nodes.push({
      id,
      label: agentLabel(id),
      role: "analysis",
      enabled,
      weight,
      variant: spec?.variant_id ?? "balanced",
      dataSources:
        spec?.owned_sources?.length
          ? spec.owned_sources
          : (meta?.defaultSources ?? []),
      freshnessMinutes: spec?.freshness_limit_minutes ?? 60,
      description: meta?.description ?? "",
      diffStatus: resolveDiffStatus(id, enabled, comparison),
      defaultWeight: comparison?.weight_diff[id]?.default ?? null,
      position: { x: 0, y: 0 },
    });
  }

  // ── Decision nodes (always present, unconditionally) ──────────────────────
  for (const id of DECISION_AGENT_IDS) {
    const meta = AGENT_META[id];
    nodes.push({
      id,
      label: agentLabel(id),
      role: "decision",
      enabled: true,
      weight: 100,
      variant: "core",
      dataSources: [],
      freshnessMinutes: 0,
      description: meta?.description ?? "",
      diffStatus: "unchanged",
      defaultWeight: null,
      position: { x: 0, y: 0 },
    });
  }

  // ── Edges: each analysis agent → risk_manager ─────────────────────────────
  for (const id of ANALYSIS_AGENT_IDS) {
    const node = nodes.find((n) => n.id === id)!;
    const isStructuralChange =
      node.diffStatus === "added" || node.diffStatus === "removed";

    edges.push({
      id: `${id}--risk_manager`,
      source: id,
      target: "risk_manager",
      strokeWidth: node.enabled ? edgeStrokeWidth(node.weight) : 1,
      style: node.enabled ? "solid" : "dashed",
      diffHighlight: isStructuralChange,
    });
  }

  // ── Edge: risk_manager → portfolio_manager ────────────────────────────────
  edges.push({
    id: "risk_manager--portfolio_manager",
    source: "risk_manager",
    target: "portfolio_manager",
    strokeWidth: 5,
    style: "solid",
    diffHighlight: false,
  });

  const debateModeActive =
    team.team_overrides["enable_bull_bear_debate"] === true;

  return {
    nodes,
    edges,
    debateModeActive,
    summary: buildSummary(team),
    riskLevel: team.risk_level,
    timeHorizon: team.time_horizon,
    sectorExclusions: team.sector_exclusions,
  };
}
