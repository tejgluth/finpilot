import { useState } from "react";
import { api } from "../../api/client";
import type { TradingStatusPayload } from "../../api/types";
import Panel from "../common/Panel";
import StatusBadge from "../common/StatusBadge";

export default function LiveUnlockGate({
  status,
  onChanged,
}: {
  status: TradingStatusPayload;
  onChanged?: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggle = async () => {
    setError("");
    setSaving(true);
    try {
      await api.setLiveTradingEnabled(!status.live_trading_enabled);
      await onChanged?.();
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "Unable to change the live trading gate.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title="Live unlock gate" eyebrow="Four-step unlock">
      <div className="space-y-3">
        {status.live_unlock.gates.map((gate) => (
          <div key={gate.id} className="rounded-2xl bg-slate px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={gate.passed ? "passed" : "pending"} tone={gate.passed ? "good" : "warn"} />
              <span className="font-semibold text-ink">{gate.label}</span>
            </div>
            <p className="mt-2 text-sm text-ink/65">{gate.detail}</p>
          </div>
        ))}
      </div>
      {error ? <div className="mt-4 rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <button
        className="mt-4 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white"
        disabled={saving}
        onClick={() => void toggle()}
      >
        {saving ? "Updating…" : status.live_trading_enabled ? "Disable live gate" : "Enable live gate"}
      </button>
    </Panel>
  );
}
