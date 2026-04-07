import { Handle, Position } from "@xyflow/react";
import clsx from "clsx";
import type { VisualizationNode } from "../../lib/teamVisualization/types";
import type { StudioMode } from "../../api/types";

const FAMILY_ACCENT: Record<string, string> = {
  // New graph-spec families
  data_ingestion: "border-l-tide",
  reasoning: "border-l-gold",
  output: "border-l-pine",
  // Legacy families (backward compat)
  analysis: "border-l-tide",
  synthesis: "border-l-gold",
  risk: "border-l-pine",
  decision: "border-l-pine",
};

const FAMILY_LABEL: Record<string, string> = {
  data_ingestion: "Data",
  reasoning: "Reasoning",
  output: "Output",
  analysis: "Analysis",
  synthesis: "Synthesis",
  risk: "Risk",
  decision: "Decision",
};

export type StudioAgentNodeData = VisualizationNode & {
  studioMode: StudioMode;
  selected: boolean;
  onSelect: (nodeId: string) => void;
  onToggleEnabled?: (nodeId: string, enabled: boolean) => void;
  debateModeActive?: boolean;
  /** Set when this node is the pending "connect from" source in connect mode */
  isConnectSource?: boolean;
};

export default function StudioAgentNode({ data }: { data: StudioAgentNodeData }) {
  const {
    id,
    label,
    role,
    enabled,
    weight,
    variant,
    description,
    studioMode,
    selected,
    onSelect,
    onToggleEnabled,
    nodeFamily,
    nodeSubtype,
    validationErrors = [],
    validationWarnings = [],
    hasPromptOverride,
    nodeId,
    isConnectSource,
  } = data;

  const isIngestion = nodeSubtype === undefined && (nodeFamily === "data_ingestion" || nodeFamily === "analysis");
  const isReasoning = nodeSubtype === "reasoning" || nodeFamily === "reasoning" || nodeFamily === "synthesis";
  const isTerminal = nodeSubtype === "terminal" || nodeFamily === "output" || nodeFamily === "decision";

  const family = nodeFamily ?? (isTerminal ? "output" : isReasoning ? "reasoning" : "data_ingestion");
  const accentCls = FAMILY_ACCENT[family] ?? "border-l-ink/20";
  const isEditable = studioMode === "edit" || studioMode === "expert";
  const hasErrors = validationErrors.length > 0;
  const hasWarnings = validationWarnings.length > 0;

  // The viz id used as the ReactFlow node id
  const selectId = nodeId ?? id;

  // Handle visibility: show as small colored dots in edit mode, invisible in view
  const handleCls = isEditable
    ? "!bg-tide/60 !border-tide !w-3 !h-3 !rounded-full hover:!bg-tide transition-colors"
    : "!border-none !bg-transparent !w-2 !h-2";

  return (
    <div
      className={clsx(
        "w-[270px] select-none rounded-[20px] bg-white shadow-soft",
        "border border-ink/10 border-l-4 transition-all",
        accentCls,
        !enabled && "opacity-50",
        isConnectSource && "ring-2 ring-gold ring-offset-2 shadow-md",
        !isConnectSource && selected && "ring-2 ring-tide ring-offset-1",
        !isConnectSource && hasErrors && !selected && "ring-2 ring-ember ring-offset-1",
        !selected && !hasErrors && !isConnectSource && "hover:shadow-md",
        isEditable ? "cursor-pointer" : "cursor-default",
      )}
      onClick={() => onSelect(selectId)}
    >
      {/* Connection handles — all node types get both source and target handles
          so any connection direction is possible. The compiler enforces DAG rules. */}
      <Handle
        className={clsx(handleCls, isEditable && "!left-[-6px]")}
        position={Position.Left}
        style={{ left: -6 }}
        type="target"
      />
      <Handle
        className={clsx(handleCls, isEditable && "!right-[-6px]")}
        position={Position.Right}
        style={{ right: -6 }}
        type="source"
      />

      <div className="space-y-2 p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-display text-base font-semibold leading-tight text-ink truncate">
              {label}
            </p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-ink/40">
              {FAMILY_LABEL[family] ?? family}
              {isConnectSource && (
                <span className="ml-1 text-gold"> · connecting from…</span>
              )}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {hasErrors && (
              <span className="rounded-full bg-ember/10 px-2 py-0.5 font-mono text-[9px] font-semibold text-ember ring-1 ring-ember/30">
                Error
              </span>
            )}
            {hasWarnings && !hasErrors && (
              <span className="rounded-full bg-gold/10 px-2 py-0.5 font-mono text-[9px] font-semibold text-gold ring-1 ring-gold/30">
                Warning
              </span>
            )}
            {hasPromptOverride && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 font-mono text-[9px] font-semibold text-amber-700 ring-1 ring-amber-300">
                Override
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="line-clamp-2 text-[11px] leading-relaxed text-ink/60">
          {description}
        </p>

        {/* Weight bar — data ingestion nodes only */}
        {isIngestion && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-ink/40">Influence</span>
              <span className="font-mono text-[10px] font-semibold text-ink">
                {weight}%
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate">
              <div
                className="h-full rounded-full bg-tide transition-all"
                style={{ width: `${Math.min(100, Math.max(0, weight))}%` }}
              />
            </div>
          </div>
        )}

        {/* Variant pill */}
        {variant && variant !== "balanced" && variant !== "core" && (
          <span className="inline-block rounded-full bg-mist px-2 py-0.5 font-mono text-[9px] text-ink/50">
            {variant.replace(/_/g, " ")}
          </span>
        )}

        {/* Enable/disable toggle in edit mode for data ingestion nodes */}
        {isEditable && isIngestion && onToggleEnabled && (
          <button
            className={clsx(
              "w-full rounded-lg py-1 text-[11px] font-medium transition-colors",
              enabled
                ? "bg-slate text-ink/60 hover:bg-ember/10 hover:text-ember"
                : "bg-tide/10 text-tide hover:bg-tide/20",
            )}
            onClick={(e) => {
              e.stopPropagation();
              onToggleEnabled(selectId, !enabled);
            }}
            type="button"
          >
            {enabled ? "Disable" : "Enable"}
          </button>
        )}

        {/* Validation errors */}
        {hasErrors && (
          <div className="rounded-lg bg-ember/5 px-2 py-1">
            {validationErrors.map((e, i) => (
              <p key={i} className="text-[10px] text-ember">
                • {e}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
