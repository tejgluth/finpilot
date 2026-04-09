import { Handle, Position } from "@xyflow/react";
import clsx from "clsx";
import type { KeyboardEvent } from "react";
import type { VisualizationNode } from "../../lib/teamVisualization/types";

// Role-based left-border accent
const ROLE_ACCENT: Record<string, string> = {
  analysis: "border-l-tide",
  decision: "border-l-pine",
  synthesis: "border-l-gold",
};

// Role-based subtle background tint
const ROLE_BG: Record<string, string> = {
  analysis: "bg-white",
  decision: "bg-pine/[0.02]",
  synthesis: "bg-gold/[0.03]",
};

type DiffBadgeProps = {
  status: VisualizationNode["diffStatus"];
  defaultWeight?: number | null;
  weight?: number;
};

function DiffBadge({ status, defaultWeight, weight }: DiffBadgeProps) {
  if (status === "unchanged" || status === "disabled") return null;

  let text = "";
  let cls = "";

  if (status === "added") {
    text = "+ Added";
    cls = "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200";
  } else if (status === "removed") {
    text = "− Removed";
    cls = "bg-ember/8 text-ember ring-1 ring-ember/20";
  } else if (status === "weight-up" && defaultWeight != null && weight != null) {
    const delta = weight - defaultWeight;
    text = `↑ +${delta}%`;
    cls = "bg-gold/8 text-gold ring-1 ring-gold/20";
  } else if (status === "weight-down" && defaultWeight != null && weight != null) {
    const delta = defaultWeight - weight;
    text = `↓ −${delta}%`;
    cls = "bg-gold/8 text-gold ring-1 ring-gold/20";
  }

  if (!text) return null;

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-1.5 py-0.5 font-mono text-[9px] font-semibold tracking-wide",
        cls,
      )}
    >
      {text}
    </span>
  );
}

function SourceChip({ source }: { source: string }) {
  return (
    <span className="rounded-full bg-slate px-1.5 py-0.5 font-mono text-[9px] text-ink/50 leading-none">
      {source}
    </span>
  );
}

export type AgentNodeData = VisualizationNode & {
  onSelect: (id: string) => void;
  debateModeActive?: boolean;
};

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

  const isSynthesis = data.nodeSubtype === "synthesis";
  const accentCls = isSynthesis
    ? "border-l-gold"
    : (ROLE_ACCENT[role] ?? "border-l-ink/20");
  const bgCls = isSynthesis
    ? "bg-gold/[0.03]"
    : (ROLE_BG[role] ?? "bg-white");

  const isDisabled = !enabled;
  const isDecision = role === "decision";

  const roleLabel = isSynthesis
    ? "Synthesis"
    : role === "analysis"
    ? "Analysis"
    : "Decision";

  const ariaLabel = [
    label,
    `${roleLabel} agent`,
    isDecision ? "" : `weight ${weight}%`,
    isDisabled ? "disabled" : "enabled",
    diffStatus !== "unchanged" && diffStatus !== "disabled"
      ? `status: ${diffStatus}`
      : "",
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
        "w-[240px] cursor-pointer select-none rounded-[18px]",
        "border border-ink/[0.09] border-l-4 shadow-sm transition-all duration-150",
        "hover:shadow-md hover:border-ink/[0.14]",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-tide",
        accentCls,
        bgCls,
        isDisabled && "opacity-45",
      )}
      onClick={() => onSelect(id)}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      {/* Handles */}
      {role === "analysis" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Right}
          style={{ width: 6, height: 6 }}
          type="source"
        />
      )}
      {role === "decision" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Left}
          style={{ width: 6, height: 6 }}
          type="target"
        />
      )}
      {id === "risk_manager" && (
        <Handle
          className="!border-none !bg-transparent"
          position={Position.Right}
          style={{ width: 6, height: 6 }}
          type="source"
        />
      )}

      <div className="space-y-2 p-3.5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p
              className={clsx(
                "font-display text-[15px] font-semibold leading-tight text-ink",
                diffStatus === "removed" && "line-through opacity-50",
              )}
            >
              {label}
            </p>
            <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-ink/35">
              {roleLabel}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <DiffBadge defaultWeight={defaultWeight} status={diffStatus} weight={weight} />
            {id === "risk_manager" && debateModeActive && (
              <span className="inline-flex items-center rounded-full bg-gold/8 px-1.5 py-0.5 font-mono text-[9px] font-semibold text-gold ring-1 ring-gold/20">
                Bull/Bear
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="line-clamp-2 text-[11px] leading-relaxed text-ink/55">
          {description}
        </p>

        {/* Weight bar — analysis only */}
        {role === "analysis" && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9px] text-ink/35">Influence</span>
              <span className="font-mono text-[10px] font-semibold text-ink">
                {weight}%
              </span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-slate">
              <div
                className="h-full rounded-full bg-tide transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, weight))}%` }}
              />
            </div>
          </div>
        )}

        {/* Tags */}
        {(variant && variant !== "balanced" && variant !== "core") ||
        dataSources.length > 0 ? (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {variant && variant !== "balanced" && variant !== "core" && (
              <span className="rounded-full bg-mist px-1.5 py-0.5 font-mono text-[9px] text-ink/45">
                {variant.replace(/_/g, " ")}
              </span>
            )}
            {dataSources.slice(0, 3).map((src) => (
              <SourceChip key={src} source={src} />
            ))}
            {dataSources.length > 3 && (
              <span className="rounded-full bg-slate px-1.5 py-0.5 font-mono text-[9px] text-ink/35">
                +{dataSources.length - 3}
              </span>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
