import type { VisualizationModel, VisualizationNode } from "./types";

// Card dimensions and spacing
const NODE_WIDTH = 270;
const NODE_HEIGHT = 160;
const NODE_GAP = 16;
const COLUMN_GAP = 90; // horizontal gap between columns (accommodates arrow heads)
const COLUMN_WIDTH = NODE_WIDTH + COLUMN_GAP;

/** Returns the y-coordinate for a node at index i out of total, centered on Y=0. */
function centeredY(index: number, total: number): number {
  const totalHeight = total * NODE_HEIGHT + (total - 1) * NODE_GAP;
  const startY = -(totalHeight / 2);
  return startY + index * (NODE_HEIGHT + NODE_GAP);
}

/**
 * Studio layout: 3 columns — data_ingestion | reasoning | output.
 *
 * - data_ingestion: nodes where nodeSubtype is undefined AND role === "analysis"
 *   (detected from data_domain in studioTransform)
 * - reasoning: nodes where nodeSubtype === "reasoning" (custom reasoning nodes)
 * - terminal/output: nodes where nodeSubtype === "terminal"
 *
 * Falls back to legacy 2-col layout if no reasoning column nodes exist
 * (for old premade teams using risk/decision fixed nodes).
 */
export function applyStudioLayout(model: VisualizationModel): VisualizationModel {
  const ingestionNodes = model.nodes.filter(
    (n) => n.role === "analysis" && !n.nodeSubtype,
  );
  const reasoningNodes = model.nodes.filter((n) => n.nodeSubtype === "reasoning");
  const terminalNodes = model.nodes.filter((n) => n.nodeSubtype === "terminal");

  // Legacy fallback: risk/decision node IDs for old premade teams
  const legacyRiskNodes = model.nodes.filter(
    (n) => n.id === "risk_manager" || n.nodeFamily === "risk",
  );
  const legacyDecisionNodes = model.nodes.filter(
    (n) => n.id === "portfolio_manager" || n.nodeFamily === "decision",
  );

  const hasReasoningColumn = reasoningNodes.length > 0 || terminalNodes.length > 0;
  const hasLegacyStructure = !hasReasoningColumn && (legacyRiskNodes.length > 0 || legacyDecisionNodes.length > 0);

  // Sort ingestion/analysis: enabled by descending weight, then disabled alphabetically
  const sortedIngestion: VisualizationNode[] = [
    ...ingestionNodes.filter((n) => n.enabled).sort((a, b) => b.weight - a.weight),
    ...ingestionNodes.filter((n) => !n.enabled).sort((a, b) => a.label.localeCompare(b.label)),
  ];

  const col0 = 0;               // ingestion / analysis
  const col1 = COLUMN_WIDTH;    // reasoning middle
  const col2 = COLUMN_WIDTH * 2; // terminal output

  // Layout ingestion/analysis column
  const layoutIngestion = sortedIngestion.map((node, idx) => ({
    ...node,
    position: { x: col0, y: centeredY(idx, sortedIngestion.length) },
  }));

  let extraNodes: VisualizationNode[] = [];

  if (hasReasoningColumn) {
    // New 3-column graph-spec layout
    const layoutReasoning = reasoningNodes.map((node, idx) => ({
      ...node,
      position: { x: col1, y: centeredY(idx, Math.max(reasoningNodes.length, 1)) },
    }));
    const layoutTerminal = terminalNodes.map((node, idx) => ({
      ...node,
      position: { x: col2, y: centeredY(idx, Math.max(terminalNodes.length, 1)) },
    }));
    extraNodes = [...layoutReasoning, ...layoutTerminal];
  } else if (hasLegacyStructure) {
    // Legacy 3-column: analysis | risk | decision
    const layoutRisk = legacyRiskNodes.map((node) => ({
      ...node,
      position: { x: col1, y: -(NODE_HEIGHT / 2) },
    }));
    const layoutDecision = legacyDecisionNodes.map((node) => ({
      ...node,
      position: { x: col2, y: -(NODE_HEIGHT / 2) },
    }));
    extraNodes = [...layoutRisk, ...layoutDecision];
  }

  // Any nodes not yet placed (e.g. synthesis, gate, debate in old topologies)
  const placedIds = new Set([
    ...layoutIngestion.map((n) => n.id),
    ...extraNodes.map((n) => n.id),
  ]);
  const unplaced = model.nodes.filter((n) => !placedIds.has(n.id));
  const layoutUnplaced = unplaced.map((node, idx) => ({
    ...node,
    position: { x: col1, y: centeredY(idx, Math.max(unplaced.length, 1)) },
  }));

  return {
    ...model,
    nodes: [...layoutIngestion, ...extraNodes, ...layoutUnplaced],
  };
}

/** Returns the approximate bounding box of the studio layout. */
export function studioModelBounds(model: VisualizationModel): {
  width: number;
  height: number;
} {
  const ingestionCount = model.nodes.filter(
    (n) => n.role === "analysis" && !n.nodeSubtype,
  ).length;
  const hasReasoning = model.nodes.some(
    (n) => n.nodeSubtype === "reasoning" || n.nodeSubtype === "terminal",
  );
  const columns = hasReasoning ? 3 : 2;

  return {
    width: COLUMN_WIDTH * (columns - 1) + NODE_WIDTH,
    height: Math.max(
      ingestionCount * (NODE_HEIGHT + NODE_GAP) + NODE_GAP,
      NODE_HEIGHT * 2,
    ),
  };
}
