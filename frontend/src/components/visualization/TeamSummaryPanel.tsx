import type { TeamVersion } from "../../api/types";
import type { VisualizationModel } from "../../lib/teamVisualization/types";
import TeamSelectorDropdown, {
  type TeamSelectorExtraOption,
} from "../strategy/TeamSelectorDropdown";

interface Props {
  model: VisualizationModel;
  teamName?: string;
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

const RISK_COLOR: Record<string, string> = {
  conservative: "bg-emerald-100 text-emerald-800",
  moderate: "bg-sky-100 text-sky-800",
  aggressive: "bg-ember/10 text-ember",
};

const HORIZON_COLOR: Record<string, string> = {
  short: "bg-amber-100 text-amber-800",
  medium: "bg-blue-100 text-blue-800",
  long: "bg-indigo-100 text-indigo-800",
};

function Chip({
  label,
  cls,
}: {
  label: string;
  cls: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 font-mono text-[11px] font-semibold ${cls}`}
    >
      {label}
    </span>
  );
}

/**
 * Plain-English summary panel rendered above the ReactFlow graph.
 * Renders instantly without waiting for the graph to mount.
 */
export default function TeamSummaryPanel({ model, teamName, teamSelector }: Props) {
  const riskCls =
    RISK_COLOR[model.riskLevel] ?? "bg-slate text-ink/70";
  const horizonCls =
    HORIZON_COLOR[model.timeHorizon] ?? "bg-slate text-ink/70";

  const enabledCount = model.nodes.filter(
    (n) => n.role === "analysis" && n.enabled,
  ).length;
  const totalAnalysis = model.nodes.filter((n) => n.role === "analysis").length;

  return (
    <div className="space-y-3">
      {teamName ? (
        teamSelector ? (
          <TeamSelectorDropdown
            activeTeam={teamSelector.activeTeam}
            currentLabel={teamSelector.currentLabel ?? teamName}
            currentSubtitle={teamSelector.currentSubtitle}
            disabled={teamSelector.disabled}
            extraOptions={teamSelector.extraOptions}
            labelClassName="text-2xl"
            onSelectTeam={teamSelector.onSelectTeam}
            teams={teamSelector.teams}
          />
        ) : (
          <h2 className="font-display text-2xl text-ink">{teamName}</h2>
        )
      ) : null}

      {/* Chips row */}
      <div className="flex flex-wrap gap-2">
        <Chip
          cls={riskCls}
          label={`${model.riskLevel.charAt(0).toUpperCase()}${model.riskLevel.slice(1)} risk`}
        />
        <Chip
          cls={horizonCls}
          label={`${model.timeHorizon.charAt(0).toUpperCase()}${model.timeHorizon.slice(1)}-term`}
        />
        <Chip
          cls="bg-slate text-ink/70"
          label={`${enabledCount} / ${totalAnalysis} agents active`}
        />
        {model.debateModeActive && (
          <Chip cls="bg-gold/10 text-gold" label="Bull/Bear debate" />
        )}
        {model.sectorExclusions.map((sec) => (
          <Chip
            cls="bg-ember/10 text-ember"
            key={sec}
            label={`Excl. ${sec.replace(/_/g, " ")}`}
          />
        ))}
      </div>

      {/* Summary sentence */}
      <p className="text-sm leading-relaxed text-ink/65">{model.summary}</p>
    </div>
  );
}
