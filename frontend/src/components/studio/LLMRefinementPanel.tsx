import { useState } from "react";
import clsx from "clsx";
import type { ArchitecturePatch } from "../../api/types";

interface Props {
  pendingPatch: ArchitecturePatch | null;
  patchLoading: boolean;
  onRequestPatch: (instruction: string) => void;
  onConfirmPatch: () => void;
  onDiscardPatch: () => void;
}

export default function LLMRefinementPanel({
  pendingPatch,
  patchLoading,
  onRequestPatch,
  onConfirmPatch,
  onDiscardPatch,
}: Props) {
  const [instruction, setInstruction] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = instruction.trim();
    if (!trimmed || patchLoading) return;
    onRequestPatch(trimmed);
    setInstruction("");
  }

  return (
    <div className="flex h-full flex-col">
      <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-ink/40">
        AI Refinement
      </p>

      {/* Pending patch diff */}
      {pendingPatch && (
        <div className="mb-4 rounded-xl border border-tide/30 bg-tide/5 p-3 space-y-2">
          <p className="text-[12px] font-semibold text-ink">
            Proposed change
          </p>
          <p className="text-[12px] text-ink/70 leading-relaxed">
            {pendingPatch.patch_description}
          </p>

          {pendingPatch.node_changes && pendingPatch.node_changes.length > 0 && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wide text-ink/40 mb-1">
                Node changes
              </p>
              {pendingPatch.node_changes.map((nc, i) => {
                const action = String(nc["action"] ?? "");
                const nodeId = String(nc["node_id"] ?? "");
                const fields = nc["fields"] as Record<string, unknown> | undefined;
                return (
                  <div key={i} className="text-[11px] text-ink/70 font-mono">
                    {action} {nodeId}
                    {fields && Object.keys(fields).length > 0 && (
                      <span className="text-ink/40"> — {Object.keys(fields).join(", ")}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {pendingPatch.edge_changes && pendingPatch.edge_changes.length > 0 && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wide text-ink/40 mb-1">
                Edge changes
              </p>
              {pendingPatch.edge_changes.map((ec, i) => (
                <div key={i} className="text-[11px] text-ink/70 font-mono">
                  {String(ec["action"] ?? "")} {String(ec["source_node_id"] ?? "")} → {String(ec["target_node_id"] ?? "")}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              className="flex-1 rounded-xl bg-tide px-3 py-2 text-[12px] font-medium text-white hover:bg-tide/90"
              onClick={onConfirmPatch}
              type="button"
            >
              Apply
            </button>
            <button
              className="flex-1 rounded-xl border border-ink/15 px-3 py-2 text-[12px] text-ink/70 hover:bg-slate"
              onClick={onDiscardPatch}
              type="button"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* Instruction form */}
      <form className="flex flex-col gap-2 mt-auto" onSubmit={handleSubmit}>
        <textarea
          className="h-24 resize-none rounded-xl border border-ink/15 px-3 py-2.5 text-[12px] text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
          disabled={patchLoading}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder={'Describe a change… e.g. "Increase the weight of Technicals to 80 and disable Sentiment"'}
          value={instruction}
        />
        <button
          className={clsx(
            "w-full rounded-xl py-2 text-[12px] font-medium transition-colors",
            patchLoading || !instruction.trim()
              ? "bg-ink/10 text-ink/30 cursor-not-allowed"
              : "bg-tide text-white hover:bg-tide/90",
          )}
          disabled={patchLoading || !instruction.trim()}
          type="submit"
        >
          {patchLoading ? "Generating…" : "Suggest change"}
        </button>
        <p className="text-center text-[10px] text-ink/30">
          AI-suggested changes require your confirmation before applying.
        </p>
      </form>
    </div>
  );
}
