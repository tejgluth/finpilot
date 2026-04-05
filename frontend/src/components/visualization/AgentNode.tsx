import { Handle, Position } from "@xyflow/react";
import clsx from "clsx";
import type { KeyboardEvent } from "react";
import type { VisualizationNode } from "../../lib/teamVisualization/types";

// Role-based left-border color
const ROLE_ACCENT: Record<string, string> = {
  analysis: "border-l-tide",
  decision: "border-l-pine",
};

// Diff status label and styling
type DiffBadgeProps = { status: VisualizationNode["diffStatus"]; defaultWeight?: number | null; weight?: number };
function DiffBadge({ status, defaultWeight, weight }: DiffBadgeProps) {
  if (status === "unchanged" || status === "disabled") return null;

  let text = "";
  let cls = "";

  if (status === "added") {
    text = "+ Added";
    cls = "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300";
  } else if (status === "removed") {
    text = "− Removed";
    cls = "bg-ember/10 text-ember ring-1 ring-ember/30";
  } else if (status === "weight-up" && defaultWeight != null && weight != null) {
    const delta = weight - defaultWeight;
    text = `↑ +${delta}%`;
    cls = "bg-gold/10 text-gold ring-1 ring-gold/30";
  } else if (status === "weight-down" && defaultWeight != null && weight != null) {
    const delta = defaultWeight - weight;
    text = `↓ −${delta}%`;
    cls = "bg-gold/10 text-gold ring-1 ring-gold/30";
  }

  if (!text) return null;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide",
        cls,
      )}
    >
      {text}
    </span>
  );
}

function SourceChip({ source }: { source: string }) {
  return (
    <span className="rounded-full bg-slate px-2 py-0.5 font-mono text-[9px] text-ink/60">
      {source}
    </span>
  );
}

export type AgentNodeData = VisualizationNode & {
  onSelect: (id: string) => void;
  debateModeActive?: boolean;
};

/**
 * Custom ReactFlow node component for both analysis and decision agents.
 * Registered as nodeType "agentNode".
 */
export default function AgentNode({ data }: { data: AgentNodeData }) {
  const {
    id,
    label,
    role,
    enabled,
    weight,
    variant,
    dataSources,
    description,
    diffStatus,
    defaultWeight,
    onSelect,
    debateModeActive,
  } = data;

  const accentCls = ROLE_ACCENT[role] ?? "border-l-ink/20";
  const isDisabled = !enabled;
  const isDecision = role === "decision";

  const ariaLabel = [
    `${label}`,
    role === "analysis" ? "analysis agent" : "decision agent",
    isDecision ? "" : `weight ${weight}%`,
    isDisabled ? "disabled" : "enabled",
    diffStatus !== "unchanged" && diffStatus !== "disabled" ? `status: ${diffStatus}` : "",
  ]
    .filter(Boolean)
    .join(", ");

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(id);
    }
  }

  return (
    <div
      aria-label={ariaLabel}
      className={clsx(
        "w-[270px] cursor-pointer select-none rounded-[20px] bg-white shadow-soft",
        "border border-ink/10 border-l-4 transition-opacity hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-tide",
        accentCls,
        isDisabled && "opacity-50",
      )}
      onClick={() => onSelect(id)}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      {/* Source handle — left side for analysis agents */}
      {role === "analysis" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Right}
          style={{ width: 8, height: 8 }}
          type="source"
        />
      )}
      {/* Target handle — right side for decision agents */}
      {role === "decision" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Left}
          style={{ width: 8, height: 8 }}
          type="target"
        />
      )}
      {/* For decision agents that also have outputs */}
      {id === "risk_manager" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Right}
          style={{ width: 8, height: 8 }}
          type="source"
        />
      )}

      <div className="space-y-2.5 p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p
              className={clsx(
                "font-display text-base font-semibold leading-tight text-ink",
                diffStatus === "removed" && "line-through opacity-60",
              )}
            >
              {label}
            </p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-ink/40">
              {role === "analysis" ? "Analysis" : "Decision"}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <DiffBadge
              defaultWeight={defaultWeight}
              status={diffStatus}
              weight={weight}
            />
            {/* Debate badge on risk_manager */}
            {id === "risk_manager" && debateModeActive && (
              <span className="inline-flex items-center rounded-full bg-gold/10 px-2 py-0.5 font-mono text-[9px] font-semibold text-gold ring-1 ring-gold/30">
                Bull/Bear
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="line-clamp-2 text-[11px] leading-relaxed text-ink/60">
          {description}
        </p>

        {/* Weight bar — analysis agents only */}
        {role === "analysis" && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-ink/40">Influence</span>
              <span className="font-mono text-[10px] font-semibold text-ink">
                {weight}%
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-slate overflow-hidden">
              <div
                className="h-full rounded-full bg-tide transition-all"
                style={{ width: `${Math.min(100, Math.max(0, weight))}%` }}
              />
            </div>
          </div>
        )}

        {/* Variant pill + data sources */}
        <div className="flex flex-wrap gap-1">
          {variant && variant !== "balanced" && variant !== "core" && (
            <span className="rounded-full bg-mist px-2 py-0.5 font-mono text-[9px] text-ink/50">
              {variant.replace(/_/g, " ")}
            </span>
          )}
          {dataSources.slice(0, 3).map((src) => (
            <SourceChip key={src} source={src} />
          ))}
          {dataSources.length > 3 && (
            <span className="rounded-full bg-slate px-2 py-0.5 font-mono text-[9px] text-ink/40">
              +{dataSources.length - 3}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
