import "@xyflow/react/dist/style.css";
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  useReactFlow,
} from "@xyflow/react";
import type { Edge, Node } from "@xyflow/react";
import { useEffect } from "react";
import type { VisualizationModel } from "../../lib/teamVisualization/types";
import AgentNode, { type AgentNodeData } from "./AgentNode";
import GraphLegend from "./GraphLegend";
import InfluenceEdge from "./InfluenceEdge";

const NODE_TYPES = { agentNode: AgentNode } as const;
const EDGE_TYPES = { influenceEdge: InfluenceEdge } as const;

interface Props {
  model: VisualizationModel;
  onNodeSelect: (id: string | null) => void;
}

function toRfNodes(model: VisualizationModel, onNodeSelect: Props["onNodeSelect"]): Node[] {
  return model.nodes.map((vizNode) => ({
    id: vizNode.id,
    type: "agentNode",
    position: vizNode.position,
    data: {
      ...vizNode,
      onSelect: onNodeSelect,
      debateModeActive: model.debateModeActive,
    } satisfies AgentNodeData as unknown as Record<string, unknown>,
    draggable: false,
  }));
}

function toRfEdges(model: VisualizationModel): Edge[] {
  return model.edges.map((vizEdge) => ({
    id: vizEdge.id,
    source: vizEdge.source,
    target: vizEdge.target,
    type: "influenceEdge",
    data: {
      strokeWidth: vizEdge.strokeWidth,
      style: vizEdge.style,
      diffHighlight: vizEdge.diffHighlight,
    },
    focusable: false,
  }));
}

/**
 * Child component that calls useReactFlow() to sync model changes.
 * Must be rendered inside a <ReactFlow> tree (which provides the context).
 */
function ModelSyncer({ model, onNodeSelect }: Props) {
  const { setNodes, setEdges, fitView } = useReactFlow();

  useEffect(() => {
    setNodes(toRfNodes(model, onNodeSelect));
    setEdges(toRfEdges(model));
    void fitView({ padding: 0.14, duration: 350 });
    // onNodeSelect is stable per render of TeamVisualizationView, exclude from deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model, setNodes, setEdges, fitView]);

  return null;
}

/**
 * ReactFlow graph for the agent team topology.
 * Read-only in v1; architecture supports future editable mode.
 */
export default function TeamVisualizationGraph({ model, onNodeSelect }: Props) {
  return (
    <div
      className="relative w-full overflow-hidden rounded-[24px] border border-ink/8 bg-mist"
      style={{ height: 560 }}
    >
      <ReactFlow
        aria-label="Agent team topology"
        colorMode="light"
        defaultEdges={toRfEdges(model)}
        defaultNodes={toRfNodes(model, onNodeSelect)}
        edgeTypes={EDGE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.14 }}
        nodesDraggable={false}
        nodeTypes={NODE_TYPES}
        nodesConnectable={false}
        onNodeClick={(_, node) => onNodeSelect(node.id)}
        panOnDrag
        zoomOnPinch
        zoomOnScroll
      >
        <Background
          color="#14202b"
          gap={28}
          style={{ opacity: 0.04 }}
          variant={BackgroundVariant.Dots}
        />
        <Controls aria-label="Graph controls" showInteractive={false} />
        <GraphLegend />
        {/* Syncs node/edge state whenever the model changes after initial mount */}
        <ModelSyncer model={model} onNodeSelect={onNodeSelect} />
      </ReactFlow>
    </div>
  );
}
