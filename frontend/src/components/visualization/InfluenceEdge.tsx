import { BaseEdge, getSmoothStepPath } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import type { VisualizationEdge } from "../../lib/teamVisualization/types";

type InfluenceEdgeData = Pick<
  VisualizationEdge,
  "strokeWidth" | "style" | "diffHighlight"
>;

/**
 * Custom ReactFlow edge for agent → decision signal flow.
 * Registered as edgeType "influenceEdge".
 *
 * Visual encoding:
 *  - Thickness = influence weight of the source agent
 *  - Dashed = source agent is disabled
 *  - Gold color + animated dash = agent was added/removed in compare mode
 */
export default function InfluenceEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps & { data?: InfluenceEdgeData }) {
  const strokeWidth = data?.strokeWidth ?? 2;
  const isDashed = data?.style === "dashed";
  const isHighlighted = data?.diffHighlight === true;

  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 12,
  });

  const stroke = isHighlighted ? "#b8923c" : "#14202b";
  const opacity = isHighlighted ? 0.7 : 0.18;
  const dashArray = isDashed ? "5,5" : isHighlighted ? "8,4" : undefined;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke,
          strokeWidth,
          strokeOpacity: opacity,
          strokeDasharray: dashArray,
        }}
      />
    </>
  );
}
