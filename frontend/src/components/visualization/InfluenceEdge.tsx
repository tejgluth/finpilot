import { BaseEdge, getSmoothStepPath } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import { useState } from "react";
import type { VisualizationEdge } from "../../lib/teamVisualization/types";

type InfluenceEdgeData = Pick<
  VisualizationEdge,
  "strokeWidth" | "style" | "diffHighlight"
> & {
  onDelete?: (edgeId: string) => void;
  isEditable?: boolean;
};

// Half-length of each × arm in px — scales with line weight
function crossHalfLen(strokeWidth: number): number {
  return strokeWidth * 3 + 3;
}

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
  const [hovered, setHovered] = useState(false);

  const strokeWidth = data?.strokeWidth ?? 2;
  const isDashed = data?.style === "dashed";
  const isHighlighted = data?.diffHighlight === true;
  const isEditable = data?.isEditable ?? false;
  const canDelete = isEditable && !!data?.onDelete;

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 12,
  });

  const stroke = isHighlighted ? "#b8923c" : "#14202b";
  const opacity = hovered && canDelete ? 0.35 : isHighlighted ? 0.7 : 0.18;
  const dashArray = isDashed ? "5,5" : isHighlighted ? "8,4" : undefined;

  const half = crossHalfLen(strokeWidth);
  // Click/hover target radius — generously larger than the × itself
  const hitRadius = half + strokeWidth + 4;

  return (
    <>
      {/* Invisible wide hit area along the full path */}
      {canDelete && (
        <path
          d={edgePath}
          fill="none"
          stroke="transparent"
          strokeWidth={hitRadius * 2}
          style={{ cursor: "crosshair" }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        />
      )}

      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke,
          strokeWidth,
          strokeOpacity: opacity,
          strokeDasharray: dashArray,
          transition: "stroke-opacity 0.15s",
          pointerEvents: "none",
        }}
      />

      {/* × rendered as SVG lines — same strokeWidth as the connector, red */}
      {canDelete && hovered && (
        <g
          style={{ cursor: "pointer" }}
          onClick={(e) => {
            e.stopPropagation();
            data!.onDelete!(id);
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {/* Transparent circle as generous click target */}
          <circle
            cx={labelX}
            cy={labelY}
            r={hitRadius}
            fill="transparent"
          />
          {/* Diagonal line \ */}
          <line
            x1={labelX - half}
            y1={labelY - half}
            x2={labelX + half}
            y2={labelY + half}
            stroke="#ef4444"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Diagonal line / */}
          <line
            x1={labelX + half}
            y1={labelY - half}
            x2={labelX - half}
            y2={labelY + half}
            stroke="#ef4444"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        </g>
      )}
    </>
  );
}
