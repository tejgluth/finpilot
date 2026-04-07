import { useRef, useState } from "react";

interface Props {
  nodeId: string;
  nodeLabel: string;
  existingPrompt?: string;
  onSave: (nodeId: string, promptText: string, label: string) => void;
  onClear: (nodeId: string) => void;
  onClose: () => void;
}

export default function PromptOverrideModal({
  nodeId,
  nodeLabel,
  existingPrompt,
  onSave,
  onClear,
  onClose,
}: Props) {
  const [promptText, setPromptText] = useState(existingPrompt ?? "");
  const [overrideLabel, setOverrideLabel] = useState(
    `Custom ${nodeLabel} Prompt`,
  );
  const overlayRef = useRef<HTMLDivElement>(null);

  function handleSave() {
    if (!promptText.trim()) return;
    onSave(nodeId, promptText.trim(), overrideLabel.trim() || `Custom ${nodeLabel} Prompt`);
    onClose();
  }

  function handleClear() {
    onClear(nodeId);
    onClose();
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose();
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm"
      onClick={handleOverlayClick}
    >
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        {/* Warning header */}
        <div className="rounded-t-2xl bg-amber-50 px-6 py-4 border-b border-amber-200">
          <div className="flex items-start gap-3">
            <span className="text-amber-500 text-xl mt-0.5">⚠</span>
            <div>
              <p className="font-semibold text-amber-800 text-sm">Expert mode — Prompt override</p>
              <p className="text-[12px] text-amber-700 mt-1 leading-relaxed">
                Overriding system prompts marks this team as{" "}
                <strong>experimental_custom</strong> and disables strict
                backtest eligibility. The override text is stored in your local
                audit log. Agent behavior is no longer governed by the standard
                prompt packs.
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="space-y-4 p-6">
          <div>
            <label className="block mb-1.5 text-[12px] font-medium text-ink/70">
              Override label
            </label>
            <input
              className="w-full rounded-xl border border-ink/15 px-3 py-2 text-sm text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              onChange={(e) => setOverrideLabel(e.target.value)}
              placeholder={`Custom ${nodeLabel} Prompt`}
              type="text"
              value={overrideLabel}
            />
          </div>

          <div>
            <label className="block mb-1.5 text-[12px] font-medium text-ink/70">
              System prompt text
            </label>
            <textarea
              className="w-full h-36 resize-none rounded-xl border border-ink/15 px-3 py-2 text-sm text-ink font-mono leading-relaxed focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              onChange={(e) => setPromptText(e.target.value)}
              placeholder="Enter system prompt instructions…"
              value={promptText}
            />
            <p className="mt-1 text-[11px] text-ink/40">
              {promptText.length} characters
            </p>
          </div>

          <div className="flex items-center justify-between pt-2">
            {existingPrompt && (
              <button
                className="text-[12px] text-ember hover:underline"
                onClick={handleClear}
                type="button"
              >
                Clear override
              </button>
            )}
            {!existingPrompt && <span />}
            <div className="flex gap-3">
              <button
                className="rounded-xl border border-ink/15 px-4 py-2 text-sm text-ink/70 hover:bg-slate"
                onClick={onClose}
                type="button"
              >
                Cancel
              </button>
              <button
                className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40"
                disabled={!promptText.trim()}
                onClick={handleSave}
                type="button"
              >
                Apply override
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
