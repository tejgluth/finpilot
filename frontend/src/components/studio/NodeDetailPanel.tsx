import { useState } from "react";
import clsx from "clsx";
import type { StudioMode, TeamNode } from "../../api/types";
import PromptOverrideModal from "./PromptOverrideModal";

const DATA_DOMAINS = [
  "fundamentals",
  "technicals",
  "sentiment",
  "macro",
  "value",
  "momentum",
  "growth",
] as const;

const OUTPUT_SCHEMAS = ["ReasoningOutput", "PortfolioDecision", "AgentSignal"] as const;

interface Props {
  node: TeamNode;
  studioMode: StudioMode;
  onUpdateWeight: (nodeId: string, weight: number) => void;
  onUpdateVariant: (nodeId: string, variantId: string) => void;
  onUpdateEnabled: (nodeId: string, enabled: boolean) => void;
  onUpdateRoleDescription: (nodeId: string, description: string) => void;
  onUpdateDisplayName: (nodeId: string, name: string) => void;
  onUpdateSystemPrompt: (nodeId: string, prompt: string) => void;
  onUpdateDataDomain: (nodeId: string, domain: string) => void;
  onUpdateParameters: (nodeId: string, params: Record<string, unknown>) => void;
  onUpdateNodeKind: (nodeId: string, kind: string) => void;
  onRemoveNode: (nodeId: string) => void;
  onSetPromptOverride: (nodeId: string, promptText: string, label: string) => void;
  onClearPromptOverride: (nodeId: string) => void;
}

export default function NodeDetailPanel({
  node,
  studioMode,
  onUpdateWeight,
  onUpdateVariant,
  onUpdateEnabled,
  onUpdateRoleDescription,
  onUpdateDisplayName,
  onUpdateSystemPrompt,
  onUpdateDataDomain,
  onUpdateParameters,
  onUpdateNodeKind,
  onRemoveNode,
  onSetPromptOverride,
  onClearPromptOverride,
}: Props) {
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [localWeight, setLocalWeight] = useState(String(node.influence_weight ?? 60));
  const [localDescription, setLocalDescription] = useState(node.role_description ?? "");
  const [localDisplayName, setLocalDisplayName] = useState(node.display_name ?? "");
  const [localSystemPrompt, setLocalSystemPrompt] = useState(node.system_prompt ?? "");
  const [localNodeKind, setLocalNodeKind] = useState(node.node_kind ?? "");

  const isEditable = studioMode === "edit" || studioMode === "expert";
  const isExpert = studioMode === "expert";

  // Node type detection
  const isIngestion = Boolean(node.data_domain);
  const isTerminal = Boolean(node.parameters?.is_terminal);
  const isCustomReasoning = !isIngestion;

  const modeBadges = [
    { label: "Analyze", supported: node.mode_eligibility.analyze },
    { label: "Paper", supported: node.mode_eligibility.paper },
    { label: "Live", supported: node.mode_eligibility.live },
    { label: "Strict BT", supported: node.mode_eligibility.backtest_strict },
    { label: "Exp BT", supported: node.mode_eligibility.backtest_experimental },
  ];

  function handleWeightBlur() {
    const v = parseInt(localWeight, 10);
    if (!isNaN(v)) {
      const clamped = Math.max(0, Math.min(100, v));
      onUpdateWeight(node.node_id, clamped);
      setLocalWeight(String(clamped));
    }
  }

  function handleDescriptionBlur() {
    if (localDescription !== (node.role_description ?? "")) {
      onUpdateRoleDescription(node.node_id, localDescription);
    }
  }

  function handleDisplayNameBlur() {
    const trimmed = localDisplayName.trim();
    if (trimmed && trimmed !== node.display_name) {
      onUpdateDisplayName(node.node_id, trimmed);
    }
  }

  function handleSystemPromptBlur() {
    if (localSystemPrompt !== (node.system_prompt ?? "")) {
      onUpdateSystemPrompt(node.node_id, localSystemPrompt);
    }
  }

  function handleNodeKindBlur() {
    if (localNodeKind !== (node.node_kind ?? "")) {
      onUpdateNodeKind(node.node_id, localNodeKind);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Header */}
      <div className="mb-4">
        {isEditable ? (
          <input
            className="w-full rounded-xl border border-ink/15 px-2 py-1 font-display text-base font-semibold text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
            onBlur={handleDisplayNameBlur}
            onChange={(e) => setLocalDisplayName(e.target.value)}
            value={localDisplayName}
          />
        ) : (
          <h3 className="font-display text-base font-semibold text-ink">
            {node.display_name}
          </h3>
        )}
        <div className="mt-1 flex items-center gap-2">
          <p className="font-mono text-[10px] uppercase tracking-widest text-ink/40">
            {isIngestion ? `data · ${node.data_domain}` : isTerminal ? "output · terminal" : `reasoning${node.node_kind ? ` · ${node.node_kind}` : ""}`}
          </p>
          {isTerminal && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
              Terminal
            </span>
          )}
        </div>
      </div>

      {/* Validation errors/warnings */}
      {(node.validation_errors ?? []).length > 0 && (
        <div className="mb-3 rounded-xl bg-ember/5 px-3 py-2.5">
          {node.validation_errors!.map((e, i) => (
            <p key={i} className="text-[11px] text-ember">• {e}</p>
          ))}
        </div>
      )}
      {(node.validation_warnings ?? []).length > 0 && (
        <div className="mb-3 rounded-xl bg-gold/5 px-3 py-2.5">
          {node.validation_warnings!.map((w, i) => (
            <p key={i} className="text-[11px] text-gold">⚠ {w}</p>
          ))}
        </div>
      )}

      <div className="space-y-4">
        {/* Enable toggle */}
        {isEditable && (
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-medium text-ink">Enabled</span>
            <button
              className={clsx(
                "relative inline-flex h-5 w-9 rounded-full transition-colors",
                node.enabled ? "bg-tide" : "bg-ink/20",
              )}
              onClick={() => onUpdateEnabled(node.node_id, !node.enabled)}
              type="button"
            >
              <span
                className={clsx(
                  "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform mt-0.5",
                  node.enabled ? "translate-x-4 ml-0.5" : "translate-x-0.5",
                )}
              />
            </button>
          </div>
        )}

        {/* ── Data-ingestion specific ── */}
        {isIngestion && (
          <>
            {/* Data domain selector */}
            {isEditable && (
              <div>
                <p className="mb-1.5 text-[12px] font-medium text-ink">Data Domain</p>
                <select
                  className="w-full rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink focus:border-tide focus:outline-none"
                  onChange={(e) => onUpdateDataDomain(node.node_id, e.target.value)}
                  value={node.data_domain ?? ""}
                >
                  {DATA_DOMAINS.map((d) => (
                    <option key={d} value={d}>
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Influence weight */}
            {isEditable && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[12px] font-medium text-ink">Influence Weight</label>
                  <input
                    className="w-14 rounded-lg border border-ink/15 px-2 py-0.5 text-right font-mono text-[12px] text-ink focus:border-tide focus:outline-none"
                    onBlur={handleWeightBlur}
                    onChange={(e) => setLocalWeight(e.target.value)}
                    type="number"
                    value={localWeight}
                  />
                </div>
                <input
                  className="w-full accent-tide"
                  max={100}
                  min={0}
                  onChange={(e) => {
                    setLocalWeight(e.target.value);
                    onUpdateWeight(node.node_id, parseInt(e.target.value, 10));
                  }}
                  type="range"
                  value={node.influence_weight ?? 60}
                />
              </div>
            )}

            {/* Capability bindings */}
            {node.capability_bindings.length > 0 && (
              <div>
                <p className="mb-1.5 text-[12px] font-medium text-ink">Capability Bindings</p>
                <div className="space-y-1.5">
                  {node.capability_bindings.map((binding) => (
                    <div
                      key={binding.capability_id}
                      className="rounded-xl border border-ink/8 bg-slate/40 px-3 py-2"
                    >
                      <p className="text-[12px] font-medium text-ink">{binding.label}</p>
                      <p className="text-[11px] text-ink/60">{binding.detail || binding.description}</p>
                      <p className="mt-1 font-mono text-[10px] uppercase tracking-wide text-ink/35">
                        {binding.configured ? "Configured" : "Needs data"}
                        {binding.source_ids.length > 0 ? ` · ${binding.source_ids.join(", ")}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Custom reasoning / output specific ── */}
        {isCustomReasoning && isEditable && (
          <>
            {/* Node kind */}
            <div>
              <p className="mb-1.5 text-[12px] font-medium text-ink">Node Kind</p>
              <input
                className="w-full rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink placeholder-ink/30 focus:border-tide focus:outline-none"
                onBlur={handleNodeKindBlur}
                onChange={(e) => setLocalNodeKind(e.target.value)}
                placeholder="e.g. ranking_layer, consensus_filter…"
                value={localNodeKind}
              />
            </div>

            {/* Output schema */}
            {!isTerminal && (
              <div>
                <p className="mb-1.5 text-[12px] font-medium text-ink">Output Schema</p>
                <select
                  className="w-full rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink focus:border-tide focus:outline-none"
                  onChange={(e) =>
                    onUpdateParameters(node.node_id, { output_schema: e.target.value })
                  }
                  value={String(node.parameters?.output_schema ?? "ReasoningOutput")}
                >
                  {OUTPUT_SCHEMAS.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Temperature + max_tokens */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="mb-1 text-[12px] font-medium text-ink">Temperature</p>
                <input
                  className="w-full rounded-xl border border-ink/15 px-2 py-1.5 text-[12px] text-ink focus:border-tide focus:outline-none"
                  max={1}
                  min={0}
                  onBlur={(e) =>
                    onUpdateParameters(node.node_id, { temperature: parseFloat(e.target.value) })
                  }
                  step={0.05}
                  type="number"
                  defaultValue={String(node.parameters?.temperature ?? 0.3)}
                />
              </div>
              <div>
                <p className="mb-1 text-[12px] font-medium text-ink">Max Tokens</p>
                <input
                  className="w-full rounded-xl border border-ink/15 px-2 py-1.5 text-[12px] text-ink focus:border-tide focus:outline-none"
                  max={2000}
                  min={100}
                  onBlur={(e) =>
                    onUpdateParameters(node.node_id, { max_tokens: parseInt(e.target.value, 10) })
                  }
                  step={100}
                  type="number"
                  defaultValue={String(node.parameters?.max_tokens ?? 600)}
                />
              </div>
            </div>
          </>
        )}

        {/* System prompt (editable for all node types in edit mode) */}
        {isEditable && (
          <div>
            <p className="mb-1.5 text-[12px] font-medium text-ink">
              System Prompt
              {isTerminal && (
                <span className="ml-2 text-[10px] font-normal text-ink/50">
                  (defines final decision logic)
                </span>
              )}
            </p>
            {!localSystemPrompt && !isIngestion && (
              <p className="mb-1 text-[11px] text-amber-600">
                ⚠ No system prompt — this node will not execute custom logic.
              </p>
            )}
            <textarea
              className="h-32 w-full resize-none rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              onBlur={handleSystemPromptBlur}
              onChange={(e) => setLocalSystemPrompt(e.target.value)}
              placeholder="Define what this node does with its upstream inputs…"
              value={localSystemPrompt}
            />
          </div>
        )}

        {/* System prompt read-only */}
        {!isEditable && node.system_prompt && (
          <div>
            <p className="mb-1 text-[11px] font-medium text-ink/50">System Prompt</p>
            <p className="text-[12px] text-ink whitespace-pre-wrap leading-relaxed">
              {node.system_prompt}
            </p>
          </div>
        )}

        {/* Role description (all nodes) */}
        {isEditable && (
          <div>
            <p className="mb-1.5 text-[12px] font-medium text-ink">Role Description</p>
            <textarea
              className="h-16 w-full resize-none rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              onBlur={handleDescriptionBlur}
              onChange={(e) => setLocalDescription(e.target.value)}
              placeholder="Optional description of this node's role…"
              value={localDescription}
            />
          </div>
        )}

        {!isEditable && node.role_description && (
          <div>
            <p className="mb-1 text-[11px] font-medium text-ink/50">Role</p>
            <p className="text-[12px] text-ink">{node.role_description}</p>
          </div>
        )}

        {/* Mode support */}
        <div>
          <p className="mb-1.5 text-[12px] font-medium text-ink">Mode Support</p>
          <div className="grid grid-cols-2 gap-1.5">
            {modeBadges.map(({ label, supported }) => (
              <div
                key={label}
                className={clsx(
                  "rounded-xl border px-2 py-1.5 text-center text-[11px] font-medium",
                  supported
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border-ember/20 bg-ember/5 text-ember",
                )}
              >
                {label}
              </div>
            ))}
          </div>
          {node.mode_eligibility.reasons.length > 0 && (
            <div className="mt-2 rounded-xl bg-gold/5 px-3 py-2">
              {node.mode_eligibility.reasons.map((reason, index) => (
                <p key={index} className="text-[11px] text-gold">• {reason}</p>
              ))}
            </div>
          )}
        </div>

        {/* Expert: prompt override (still expert-only) */}
        {isExpert && isIngestion && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
            <p className="mb-2 text-[11px] font-semibold text-amber-800">
              Expert — Full Prompt Override
            </p>
            <p className="mb-2 text-[10px] text-amber-700">
              Bypasses all prompt contracts. Marks team as experimental_custom.
            </p>
            {node.prompt_override ? (
              <div>
                <p className="text-[11px] text-amber-700 mb-2">
                  Override active: "{node.prompt_override.label ?? "Custom"}"
                </p>
                <button
                  className="w-full rounded-lg bg-amber-500 px-3 py-1.5 text-[12px] font-medium text-white hover:bg-amber-600"
                  onClick={() => setShowPromptModal(true)}
                  type="button"
                >
                  Edit override
                </button>
              </div>
            ) : (
              <button
                className="w-full rounded-lg border border-amber-300 px-3 py-1.5 text-[12px] font-medium text-amber-700 hover:bg-amber-100"
                onClick={() => setShowPromptModal(true)}
                type="button"
              >
                Set prompt override
              </button>
            )}
          </div>
        )}

        {/* Remove node (not for terminal nodes) */}
        {isEditable && !isTerminal && (
          <button
            className="w-full rounded-xl border border-ember/20 py-2 text-[12px] font-medium text-ember hover:bg-ember/5"
            onClick={() => onRemoveNode(node.node_id)}
            type="button"
          >
            Remove node
          </button>
        )}
      </div>

      {showPromptModal && (
        <PromptOverrideModal
          existingPrompt={node.prompt_override?.system_prompt_text}
          nodeId={node.node_id}
          nodeLabel={node.display_name}
          onClear={onClearPromptOverride}
          onClose={() => setShowPromptModal(false)}
          onSave={onSetPromptOverride}
        />
      )}
    </div>
  );
}
