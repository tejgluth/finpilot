import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import type { VisualizationNode } from "../../lib/teamVisualization/types";

interface Props {
  node: VisualizationNode | null;
  onClose: () => void;
}

const DIFF_EXPLANATION: Record<string, string> = {
  added: "This agent was added to your custom team — it is not in the default baseline.",
  removed: "This agent was removed from the default baseline in your custom team.",
  "weight-up": "This agent's influence is higher in your custom team than in the default baseline.",
  "weight-down": "This agent's influence is lower in your custom team than in the default baseline.",
  disabled: "This agent is present in the team catalog but has been turned off for this team.",
  unchanged: "",
};

/**
 * Slide-in detail drawer for a selected agent node.
 * Accessible: role=dialog, focus trap, Escape to close.
 */
export default function AgentDetailDrawer({ node, onClose }: Props) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  // Focus the close button when the drawer opens
  useEffect(() => {
    if (node) {
      closeRef.current?.focus();
    }
  }, [node]);

  // Close on Escape
  useEffect(() => {
    if (!node) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [node, onClose]);

  if (!node) return null;

  const diffNote = DIFF_EXPLANATION[node.diffStatus] ?? "";
  const showWeightDelta =
    (node.diffStatus === "weight-up" || node.diffStatus === "weight-down") &&
    node.defaultWeight != null;

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-30 bg-ink/10 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <aside
        aria-labelledby={titleId}
        aria-modal="true"
        className="fixed right-0 top-0 z-40 flex h-full w-[340px] flex-col bg-white shadow-soft overflow-y-auto"
        role="dialog"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-ink/8 p-5">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-ink/40">
              {node.role === "analysis" ? "Analysis Agent" : "Decision Agent"}
            </p>
            <h3 className="font-display text-2xl text-ink" id={titleId}>
              {node.label}
            </h3>
          </div>
          <button
            aria-label="Close agent detail"
            className="mt-1 rounded-full p-1.5 text-ink/40 hover:bg-slate hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-tide"
            onClick={onClose}
            ref={closeRef}
            type="button"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-5 p-5">
          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            <StatusBadge
              label={node.enabled ? "Enabled" : "Disabled"}
              variant={node.enabled ? "positive" : "muted"}
            />
            {node.role === "decision" && (
              <StatusBadge label="Required" variant="neutral" />
            )}
            {node.diffStatus === "added" && (
              <StatusBadge label="+ Added" variant="positive" />
            )}
            {node.diffStatus === "removed" && (
              <StatusBadge label="− Removed" variant="danger" />
            )}
          </div>

          {/* Description */}
          <Section title="What it does">
            <p className="text-sm leading-relaxed text-ink/70">{node.description}</p>
          </Section>

          {/* Influence / weight — analysis only */}
          {node.role === "analysis" && (
            <Section title="Influence weight">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-ink/60">This team</span>
                  <span className="font-mono text-sm font-semibold text-ink">
                    {node.weight}%
                  </span>
                </div>
                {showWeightDelta && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink/60">Default team</span>
                    <span className="font-mono text-sm text-ink/50">
                      {node.defaultWeight}%
                    </span>
                  </div>
                )}
                <div className="h-1.5 rounded-full bg-slate overflow-hidden">
                  <div
                    className="h-full rounded-full bg-tide"
                    style={{ width: `${Math.min(100, node.weight)}%` }}
                  />
                </div>
              </div>
            </Section>
          )}

          {/* Diff explanation */}
          {diffNote && (
            <Section title="Comparison note">
              <p className="text-sm leading-relaxed text-ink/70">{diffNote}</p>
            </Section>
          )}

          {/* Data sources */}
          {node.dataSources.length > 0 && (
            <Section title="Data sources">
              <div className="flex flex-wrap gap-1.5">
                {node.dataSources.map((src) => (
                  <span
                    className="rounded-full bg-slate px-2.5 py-1 font-mono text-[11px] text-ink/60"
                    key={src}
                  >
                    {src}
                  </span>
                ))}
              </div>
              {node.freshnessMinutes > 0 && (
                <p className="mt-2 text-xs text-ink/40">
                  Max data age: {node.freshnessMinutes} min
                </p>
              )}
            </Section>
          )}

          {/* Variant */}
          {node.variant && node.variant !== "balanced" && node.variant !== "core" && (
            <Section title="Prompt variant">
              <span className="rounded-full bg-mist px-3 py-1 font-mono text-xs text-ink/60">
                {node.variant.replace(/_/g, " ")}
              </span>
            </Section>
          )}
        </div>
      </aside>
    </>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <p className="font-mono text-[10px] uppercase tracking-widest text-ink/35">
        {title}
      </p>
      {children}
    </div>
  );
}

type BadgeVariant = "positive" | "danger" | "muted" | "neutral";
const BADGE_CLS: Record<BadgeVariant, string> = {
  positive: "bg-emerald-100 text-emerald-800",
  danger: "bg-ember/10 text-ember",
  muted: "bg-slate text-ink/50",
  neutral: "bg-ink/8 text-ink/70",
};

function StatusBadge({ label, variant }: { label: string; variant: BadgeVariant }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold ${BADGE_CLS[variant]}`}
    >
      {label}
    </span>
  );
}
