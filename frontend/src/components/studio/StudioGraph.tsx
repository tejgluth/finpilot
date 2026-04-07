import "@xyflow/react/dist/style.css";
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useEffect } from "react";
import type { StudioMode } from "../../api/types";
import type { VisualizationModel } from "../../lib/teamVisualization/types";
import InfluenceEdge from "../visualization/InfluenceEdge";
import StudioAgentNode, { type StudioAgentNodeData } from "./StudioAgentNode";

const NODE_TYPES = { studioAgentNode: StudioAgentNode } as const;
const EDGE_TYPES = { influenceEdge: InfluenceEdge } as const;

interface Props {
  model: VisualizationModel;
  studioMode: StudioMode;
  selectedNodeId: string | null;
  /** When set, this node is the pending source for a click-to-connect operation */
  connectingFrom: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onConnect: (sourceNodeId: string, targetNodeId: string) => void;
  onNodePositionChange?: (nodeId: string, x: number, y: number) => void;
}

function toRfNodes(
  model: VisualizationModel,
  studioMode: StudioMode,
  selectedNodeId: string | null,
  connectingFrom: string | null,
  onNodeSelect: Props["onNodeSelect"],
): Node[] {
  const isEditable = studioMode === "edit" || studioMode === "expert";
  return model.nodes.map((vizNode) => ({
    id: vizNode.id,
    type: "studioAgentNode",
    position: vizNode.position,
    data: {
      ...vizNode,
      studioMode,
      selected: selectedNodeId === (vizNode.nodeId ?? vizNode.id),
      isConnectSource: connectingFrom === (vizNode.nodeId ?? vizNode.id),
      onSelect: (id: string) => onNodeSelect(id),
      debateModeActive: model.debateModeActive,
    } satisfies StudioAgentNodeData as unknown as Record<string, unknown>,
    draggable: isEditable,
    selected: selectedNodeId === (vizNode.nodeId ?? vizNode.id),
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

function ModelSyncer({
  model,
  studioMode,
  selectedNodeId,
  connectingFrom,
  onNodeSelect,
}: Pick<Props, "model" | "studioMode" | "selectedNodeId" | "connectingFrom" | "onNodeSelect">) {
  const { setNodes, setEdges, fitView } = useReactFlow();

  useEffect(() => {
    setNodes(toRfNodes(model, studioMode, selectedNodeId, connectingFrom, onNodeSelect));
    setEdges(toRfEdges(model));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model, studioMode, selectedNodeId, connectingFrom, setNodes, setEdges]);

  // Only fit view on initial load (when model changes structurally, not just selection)
  useEffect(() => {
    void fitView({ padding: 0.14, duration: 350 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.nodes.length, fitView]);

  return null;
}

export default function StudioGraph({
  model,
  studioMode,
  selectedNodeId,
  connectingFrom,
  onNodeSelect,
  onConnect,
  onNodePositionChange,
}: Props) {
  const isEditable = studioMode === "edit" || studioMode === "expert";

  // Handle ReactFlow drag-to-connect (existing behavior)
  function handleConnect(connection: Connection) {
    if (connection.source && connection.target) {
      onConnect(connection.source, connection.target);
    }
  }

  function handleNodeDragStop(_: React.MouseEvent, node: Node) {
    if (onNodePositionChange) {
      const vizNode = model.nodes.find((n) => n.id === node.id);
      const topologyNodeId = vizNode?.nodeId ?? node.id;
      onNodePositionChange(topologyNodeId, node.position.x, node.position.y);
    }
  }

  function handleNodeClick(_: React.MouseEvent, node: Node) {
    const vizNode = model.nodes.find((n) => n.id === node.id);
    const topologyNodeId = vizNode?.nodeId ?? node.id;

    if (isEditable && connectingFrom !== null) {
      // In connect mode: if clicking a different node, create the edge
      if (connectingFrom !== topologyNodeId) {
        onConnect(connectingFrom, topologyNodeId);
      }
      // Whether same or different node, the click completes/cancels connect mode
      // by clearing selection (parent handles this via onNodeSelect)
      onNodeSelect(null);
    } else {
      onNodeSelect(topologyNodeId);
    }
  }

  return (
    <div
      className="relative w-full overflow-hidden rounded-[24px] border border-ink/8 bg-mist"
      style={{ height: 560 }}
    >
      <ReactFlow
        aria-label="Custom team topology editor"
        colorMode="light"
        defaultEdges={toRfEdges(model)}
        defaultNodes={toRfNodes(model, studioMode, selectedNodeId, connectingFrom, onNodeSelect)}
        deleteKeyCode={null}
        edgeTypes={EDGE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.14 }}
        nodesDraggable={isEditable}
        nodeTypes={NODE_TYPES}
        nodesConnectable={isEditable}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onNodeDragStop={handleNodeDragStop}
        onPaneClick={() => onNodeSelect(null)}
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
        <ModelSyncer
          connectingFrom={connectingFrom}
          model={model}
          onNodeSelect={onNodeSelect}
          selectedNodeId={selectedNodeId}
          studioMode={studioMode}
        />
      </ReactFlow>
    </div>
  );
}
