import type { VisualizationModel, VisualizationNode } from "./types";

// Column x-positions (px from left). Cards are 270px wide; 360px columns give
// 90px gutter between columns which accommodates the arrow heads.
const COLUMN_X = [0, 360, 720] as const;

const NODE_HEIGHT = 160; // estimated rendered card height in px
const NODE_GAP = 16;     // vertical gap between cards in the analysis column

/** Returns the y-coordinate for a node at index i out of total nodes, centered on Y=0. */
function centeredY(index: number, total: number): number {
  const totalHeight = total * NODE_HEIGHT + (total - 1) * NODE_GAP;
  const startY = -(totalHeight / 2);
  return startY + index * (NODE_HEIGHT + NODE_GAP);
}

/**
 * Assigns deterministic x/y positions to every node in the model.
 * Layout: analysis agents in column 0 (sorted by weight desc, then disabled alpha),
 * risk_manager in column 1, portfolio_manager in column 2.
 * Decision nodes are vertically centered on the analysis column midpoint.
 */
export function applyLayout(model: VisualizationModel): VisualizationModel {
  const analysis = model.nodes.filter((n) => n.role === "analysis");
  const riskManager = model.nodes.find((n) => n.id === "risk_manager")!;
  const portfolioManager = model.nodes.find((n) => n.id === "portfolio_manager")!;

  // Enabled agents sorted by descending weight; disabled agents sorted alphabetically after
  const sorted: VisualizationNode[] = [
    ...analysis
      .filter((n) => n.enabled)
      .sort((a, b) => b.weight - a.weight),
    ...analysis
      .filter((n) => !n.enabled)
      .sort((a, b) => a.label.localeCompare(b.label)),
  ];

  const total = sorted.length;

  const updatedAnalysis: VisualizationNode[] = sorted.map((node, idx) => ({
    ...node,
    position: {
      x: COLUMN_X[0],
      y: centeredY(idx, total),
    },
  }));

  // Decision nodes: vertically centered relative to the analysis column
  const decisionY = -(NODE_HEIGHT / 2);

  const updatedRisk: VisualizationNode = {
    ...riskManager,
    position: { x: COLUMN_X[1], y: decisionY },
  };

  const updatedPM: VisualizationNode = {
    ...portfolioManager,
    position: { x: COLUMN_X[2], y: decisionY },
  };

  return {
    ...model,
    nodes: [...updatedAnalysis, updatedRisk, updatedPM],
  };
}

/** Returns the approximate bounding box of the laid-out model (useful for container sizing). */
export function modelBounds(model: VisualizationModel): { width: number; height: number } {
  const analysisCount = model.nodes.filter((n) => n.role === "analysis").length;
  return {
    width: COLUMN_X[2] + 280,
    height: Math.max(
      analysisCount * (NODE_HEIGHT + NODE_GAP) + NODE_GAP,
      NODE_HEIGHT * 2,
    ),
  };
}
