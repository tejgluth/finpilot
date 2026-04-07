export type AgentRole = "analysis" | "decision";

export type AgentDiffStatus =
  | "unchanged"
  | "added"        // present in candidate, absent in default
  | "removed"      // absent in candidate, present in default
  | "weight-up"    // same agent, weight increased vs default
  | "weight-down"  // same agent, weight decreased vs default
  | "disabled";    // agent exists but enabled === false

export interface VisualizationNode {
  /** Stable ID — same as agent_name (e.g. "fundamentals", "risk_manager") */
  id: string;
  /** Human-readable label e.g. "Fundamentals" */
  label: string;
  role: AgentRole;
  enabled: boolean;
  /** 0–100, used for edge thickness and weight bar display */
  weight: number;
  variant: string;
  dataSources: string[];
  freshnessMinutes: number;
  description: string;
  diffStatus: AgentDiffStatus;
  /** Weight in the default/reference team — null outside compare mode */
  defaultWeight: number | null;
  /** Assigned by layout.ts; starts as { x: 0, y: 0 } from transform.ts */
  position: { x: number; y: number };
  /** Studio-only: column placement hint for the studio layout */
  nodeSubtype?: "synthesis" | "reasoning" | "terminal";
  /** Studio-only: raw topology node_id (differs from id for custom nodes) */
  nodeId?: string;
  /** Studio-only: topology node family */
  nodeFamily?: string;
  /** Studio-only: per-node validation errors from TeamValidationResult */
  validationErrors?: string[];
  /** Studio-only: per-node validation warnings */
  validationWarnings?: string[];
  /** Studio-only: true when a prompt override is set on this node */
  hasPromptOverride?: boolean;
}

export type EdgeStyle = "solid" | "dashed";

export interface VisualizationEdge {
  id: string;
  source: string;
  target: string;
  /** Stroke width 1–5 derived from source agent weight */
  strokeWidth: number;
  /** Dashed when source agent is disabled */
  style: EdgeStyle;
  /** True when the source agent was added or removed in compare mode */
  diffHighlight: boolean;
}

export interface VisualizationModel {
  nodes: VisualizationNode[];
  edges: VisualizationEdge[];
  /** True when team_overrides.enable_bull_bear_debate === true */
  debateModeActive: boolean;
  /** Plain-English summary for the TeamSummaryPanel */
  summary: string;
  riskLevel: string;
  timeHorizon: string;
  sectorExclusions: string[];
}
