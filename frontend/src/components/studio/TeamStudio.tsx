import { useMemo, useState } from "react";
import clsx from "clsx";
import type { StudioMode } from "../../api/types";
import { useCustomTeamStore } from "../../stores/customTeamStore";
import { topologyToVisualizationModel } from "../../lib/teamVisualization/studioTransform";
import { applyStudioLayout } from "../../lib/teamVisualization/studioLayout";
import BacktestEligibilityPanel from "./BacktestEligibilityPanel";
import InlineTeamNameEditor from "./InlineTeamNameEditor";
import LLMRefinementPanel from "./LLMRefinementPanel";
import NodeDetailPanel from "./NodeDetailPanel";
import NodePalette from "./NodePalette";
import StudioGraph from "./StudioGraph";
import TeamClassificationBadge from "./TeamClassificationBadge";
import ValidationBanner from "./ValidationBanner";

const MODE_TABS: { id: StudioMode; label: string }[] = [
  { id: "view", label: "View" },
  { id: "edit", label: "Edit" },
  { id: "expert", label: "Expert" },
];

export default function TeamStudio() {
  const {
    draft,
    compiledTeam,
    validationResult,
    studioMode,
    selectedNodeId,
    pendingPatch,
    patchLoading,
    showRefinementPanel,
    setStudioMode,
    selectNode,
    setShowRefinementPanel,
    addNode,
    removeNode,
    addEdge,
    updateNodeWeight,
    updateNodeVariant,
    updateNodeEnabled,
    updateNodeRoleDescription,
    updateNodeDisplayName,
    updateNodeSystemPrompt,
    updateNodeDataDomain,
    updateNodeParameters,
    updateNodeKind,
    updateTeamName,
    setNodePromptOverride,
    clearNodePromptOverride,
    updateNodePosition,
    requestNLPatch,
    confirmPatch,
    discardPatch,
    recompile,
  } = useCustomTeamStore();

  // Connect mode: first click sets connectingFrom, second click creates the edge
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);

  const topology = draft?.topology;

  const model = useMemo(() => {
    if (!topology) return null;
    const raw = topologyToVisualizationModel(topology, validationResult, studioMode);
    return applyStudioLayout(raw);
  }, [topology, validationResult, studioMode]);

  // Find the selected topology node
  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !topology) return null;
    return topology.nodes.find((n) => n.node_id === selectedNodeId) ?? null;
  }, [selectedNodeId, topology]);

  const isEditable = studioMode === "edit" || studioMode === "expert";
  const classification = compiledTeam?.team_classification ?? draft?.validation_result?.team_classification;
  const executionProfile = compiledTeam?.execution_profile ?? validationResult?.execution_profile;
  const hasTerminalNode = Boolean(
    topology?.nodes.some((n) => n.parameters?.is_terminal || n.node_family === "decision"),
  );

  // When mode changes away from edit, cancel connect mode
  function handleSetStudioMode(mode: StudioMode) {
    setConnectingFrom(null);
    setStudioMode(mode);
  }

  // Node selection with connect mode awareness
  function handleNodeSelect(nodeId: string | null) {
    if (!isEditable) {
      selectNode(nodeId);
      setConnectingFrom(null);
      return;
    }

    if (connectingFrom !== null) {
      // Second click in connect mode
      if (nodeId && nodeId !== connectingFrom) {
        addEdge(connectingFrom, nodeId);
      }
      setConnectingFrom(null);
      selectNode(null);
    } else if (nodeId) {
      // First click: enter connect mode AND select node
      setConnectingFrom(nodeId);
      selectNode(nodeId);
    } else {
      // Click on pane: cancel connect mode
      setConnectingFrom(null);
      selectNode(null);
    }
  }

  // Direct drag-to-connect from ReactFlow handles (also supported)
  function handleConnect(src: string, tgt: string) {
    addEdge(src, tgt);
    setConnectingFrom(null);
    selectNode(null);
  }

  if (!topology || !model) {
    return (
      <div className="flex h-64 items-center justify-center text-ink/40 text-sm">
        No topology to display.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <InlineTeamNameEditor
            name={draft?.proposed_name ?? compiledTeam?.name ?? "Custom Team"}
            onSave={updateTeamName}
          />
          <TeamClassificationBadge classification={classification} size="md" />
        </div>

        <div className="flex items-center gap-2">
          {/* Mode tabs */}
          <div className="flex rounded-xl border border-ink/10 bg-slate p-0.5">
            {MODE_TABS.map((tab) => (
              <button
                key={tab.id}
                className={clsx(
                  "rounded-lg px-3 py-1.5 text-[12px] font-medium transition-colors",
                  studioMode === tab.id
                    ? "bg-white text-ink shadow-sm"
                    : "text-ink/50 hover:text-ink",
                )}
                onClick={() => handleSetStudioMode(tab.id)}
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* AI refine toggle */}
          {compiledTeam && (
            <button
              className={clsx(
                "rounded-xl border px-3 py-1.5 text-[12px] font-medium transition-colors",
                showRefinementPanel
                  ? "border-tide/40 bg-tide/10 text-tide"
                  : "border-ink/10 bg-white text-ink/60 hover:border-ink/20",
              )}
              onClick={() => setShowRefinementPanel(!showRefinementPanel)}
              type="button"
            >
              AI Refine
            </button>
          )}

          {/* Recompile */}
          {isEditable && (
            <button
              className="rounded-xl bg-tide px-4 py-1.5 text-[12px] font-medium text-white hover:bg-tide/90"
              onClick={recompile}
              type="button"
            >
              Compile
            </button>
          )}
        </div>
      </div>

      {/* Connect mode banner */}
      {connectingFrom && isEditable && (
        <div className="flex items-center justify-between rounded-xl border border-gold/30 bg-gold/8 px-4 py-2">
          <p className="text-[12px] font-medium text-ink">
            <span className="font-semibold text-gold">Connect mode:</span>{" "}
            click any other node to draw a connection from{" "}
            <span className="font-semibold">
              {topology.nodes.find((n) => n.node_id === connectingFrom)?.display_name ?? connectingFrom}
            </span>
          </p>
          <button
            className="text-[11px] text-ink/50 hover:text-ink"
            onClick={() => { setConnectingFrom(null); selectNode(null); }}
            type="button"
          >
            Cancel (Esc)
          </button>
        </div>
      )}

      {/* Validation banner */}
      <ValidationBanner validationResult={validationResult} />

      {/* Main 3-column layout */}
      <div className="grid gap-4" style={{ gridTemplateColumns: isEditable ? "200px 1fr 280px" : "1fr 280px" }}>
        {/* Left: Node palette (edit/expert only) */}
        {isEditable && (
          <div className="rounded-[20px] border border-ink/8 bg-white p-4">
            <NodePalette
              hasTerminalNode={hasTerminalNode}
              onAdd={(family, agentType, dataDomain) => addNode(family, agentType, dataDomain)}
            />
          </div>
        )}

        {/* Center: Studio graph */}
        <div>
          <StudioGraph
            connectingFrom={connectingFrom}
            model={model}
            onConnect={handleConnect}
            onNodePositionChange={updateNodePosition}
            onNodeSelect={handleNodeSelect}
            selectedNodeId={selectedNodeId}
            studioMode={studioMode}
          />
          {isEditable && !connectingFrom && (
            <p className="mt-2 text-center text-[11px] text-ink/35">
              Click a node to start connecting · drag handles to connect · drag nodes to reposition
            </p>
          )}
        </div>

        {/* Right: Detail / Refinement panel */}
        <div className="rounded-[20px] border border-ink/8 bg-white p-4">
          {showRefinementPanel && compiledTeam ? (
            <LLMRefinementPanel
              onConfirmPatch={confirmPatch}
              onDiscardPatch={discardPatch}
              onRequestPatch={requestNLPatch}
              patchLoading={patchLoading}
              pendingPatch={pendingPatch}
            />
          ) : selectedNode ? (
            <NodeDetailPanel
              node={selectedNode}
              onClearPromptOverride={clearNodePromptOverride}
              onRemoveNode={removeNode}
              onSetPromptOverride={setNodePromptOverride}
              onUpdateDataDomain={updateNodeDataDomain}
              onUpdateDisplayName={updateNodeDisplayName}
              onUpdateEnabled={updateNodeEnabled}
              onUpdateNodeKind={updateNodeKind}
              onUpdateParameters={updateNodeParameters}
              onUpdateRoleDescription={updateNodeRoleDescription}
              onUpdateSystemPrompt={updateNodeSystemPrompt}
              onUpdateVariant={updateNodeVariant}
              onUpdateWeight={updateNodeWeight}
              studioMode={studioMode}
            />
          ) : (
            <div className="flex h-full flex-col">
              <BacktestEligibilityPanel profile={executionProfile} />
              {!isEditable && (
                <p className="mt-6 text-center text-[12px] text-ink/40">
                  Click a node to inspect it. Switch to Edit mode to make changes.
                </p>
              )}
              {isEditable && (
                <p className="mt-6 text-center text-[12px] text-ink/40">
                  Click a node to start connecting it to another node.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
