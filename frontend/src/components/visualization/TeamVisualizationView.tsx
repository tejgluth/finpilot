import { useMemo, useState } from "react";
import type { CompiledTeam, TeamComparison, TeamVersion } from "../../api/types";
import { applyLayout } from "../../lib/teamVisualization/layout";
import { compiledTeamToVisualizationModel } from "../../lib/teamVisualization/transform";
import type { VisualizationNode } from "../../lib/teamVisualization/types";
import type { TeamSelectorExtraOption } from "../strategy/TeamSelectorDropdown";
import AgentDetailDrawer from "./AgentDetailDrawer";
import TeamSummaryPanel from "./TeamSummaryPanel";
import TeamVisualizationGraph from "./TeamVisualizationGraph";

interface Props {
  team: CompiledTeam;
  comparison: TeamComparison | null;
  /** When true, comparison diff overlays are visible on nodes/edges */
  showComparison: boolean;
  teamSelector?: {
    teams: TeamVersion[];
    activeTeam: TeamVersion | null;
    onSelectTeam: (teamId: string, versionNumber: number) => void | Promise<void>;
    currentLabel?: string;
    currentSubtitle?: string;
    extraOptions?: TeamSelectorExtraOption[];
    disabled?: boolean;
  };
}

/**
 * Page-level view for the Visualize and Compare tabs.
 * Composes the summary panel, the ReactFlow graph, and the detail drawer.
 */
export default function TeamVisualizationView({
  team,
  comparison,
  showComparison,
  teamSelector,
}: Props) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Build the visualization model — memoized so it only recomputes when inputs change
  const model = useMemo(() => {
    const raw = compiledTeamToVisualizationModel(
      team,
      showComparison ? comparison : null,
    );
    return applyLayout(raw);
  }, [team, comparison, showComparison]);

  const selectedNode: VisualizationNode | null =
    selectedNodeId != null
      ? (model.nodes.find((n) => n.id === selectedNodeId) ?? null)
      : null;

  return (
    <div className="space-y-4">
      {/* Plain-English summary above the graph */}
      <TeamSummaryPanel model={model} teamName={team.name} teamSelector={teamSelector} />

      {/* Hint bar */}
      <p className="text-xs text-ink/45">
        This map shows how your team analyzes and routes signals — click any agent to
        learn more.
      </p>

      {/* Graph */}
      <TeamVisualizationGraph
        model={model}
        onNodeSelect={(id) => setSelectedNodeId(id === selectedNodeId ? null : id)}
      />

      {/* Comparison diff context when in compare mode */}
      {showComparison && comparison && (
        <div className="rounded-2xl border border-gold/20 bg-gold/5 px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-gold/70">
            Compare mode
          </p>
          <p className="mt-1 text-xs text-ink/60">{comparison.summary}</p>
        </div>
      )}

      {/* Detail drawer — slides in from the right */}
      <AgentDetailDrawer
        node={selectedNode}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}
