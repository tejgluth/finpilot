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
const FIT_VIEW_OPTIONS = { padding: 0.28, duration: 350, minZoom: 0.02 } as const;

interface Props {
  model: VisualizationModel;
  studioMode: StudioMode;
  selectedNodeId: string | null;
  /** When set, this node is the pending source for a click-to-connect operation */
  connectingFrom: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onConnect: (sourceNodeId: string, targetNodeId: string) => void;
  onEdgeDelete?: (edgeId: string) => void;
  onNodePositionChange?: (nodeId: string, x: number, y: number) => void;
  isVisible?: boolean;
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

function toRfEdges(
  model: VisualizationModel,
  isEditable: boolean,
  onEdgeDelete?: (edgeId: string) => void,
): Edge[] {
  return model.edges.map((vizEdge) => ({
    id: vizEdge.id,
    source: vizEdge.source,
    target: vizEdge.target,
    type: "influenceEdge",
    data: {
      strokeWidth: vizEdge.strokeWidth,
      style: vizEdge.style,
      diffHighlight: vizEdge.diffHighlight,
      isEditable,
      onDelete: onEdgeDelete,
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
  onEdgeDelete,
  isVisible = true,
}: Pick<
  Props,
  "model" | "studioMode" | "selectedNodeId" | "connectingFrom" | "onNodeSelect" | "onEdgeDelete" | "isVisible"
>) {
  const { setNodes, setEdges, fitView } = useReactFlow();
  const isEditable = studioMode === "edit" || studioMode === "expert";

  useEffect(() => {
    setNodes(toRfNodes(model, studioMode, selectedNodeId, connectingFrom, onNodeSelect));
    setEdges(toRfEdges(model, isEditable, onEdgeDelete));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model, studioMode, selectedNodeId, connectingFrom, setNodes, setEdges, onEdgeDelete]);

  useEffect(() => {
    if (!isVisible) {
      return undefined;
    }

    let frameOne = 0;
    let frameTwo = 0;
    frameOne = window.requestAnimationFrame(() => {
      frameTwo = window.requestAnimationFrame(() => {
        void fitView(FIT_VIEW_OPTIONS);
      });
    });

    return () => {
      window.cancelAnimationFrame(frameOne);
      window.cancelAnimationFrame(frameTwo);
    };
  }, [fitView, isVisible, model]);

  return null;
}

export default function StudioGraph({
  model,
  studioMode,
  selectedNodeId,
  connectingFrom,
  onNodeSelect,
  onConnect,
  onEdgeDelete,
  onNodePositionChange,
  isVisible = true,
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
        defaultEdges={toRfEdges(model, isEditable, onEdgeDelete)}
        defaultNodes={toRfNodes(model, studioMode, selectedNodeId, connectingFrom, onNodeSelect)}
        deleteKeyCode={null}
        edgeTypes={EDGE_TYPES}
        fitViewOptions={FIT_VIEW_OPTIONS}
        minZoom={0.02}
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
        <Controls aria-label="Graph controls" showFitView showInteractive={false} />
        <ModelSyncer
          connectingFrom={connectingFrom}
          isVisible={isVisible}
          model={model}
          onEdgeDelete={onEdgeDelete}
          onNodeSelect={onNodeSelect}
          selectedNodeId={selectedNodeId}
          studioMode={studioMode}
        />
      </ReactFlow>
    </div>
  );
}
