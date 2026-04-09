import { useState } from "react";
import { api } from "../../api/client";
import Panel from "../common/Panel";
import StatusBadge from "../common/StatusBadge";
import ThinkingDots from "../common/ThinkingDots";

export const RISK_ACKNOWLEDGMENT_ITEMS = [
  { id: "not_advice", text: "I understand that FinPilot is a research tool, not investment advice, and is not regulated by any financial authority." },
  { id: "past_performance", text: "I understand that backtest results are historical only. Past performance does not predict future results." },
  { id: "ai_errors", text: "I understand that AI agents can make mistakes despite grounding safeguards. I will not blindly trust agent decisions." },
  { id: "real_money", text: "I understand that live trading uses real money and I can lose my entire investment." },
  { id: "guardrails_not_perfect", text: "I understand that guardrails reduce but do not eliminate risk. Extreme market conditions can cause losses beyond configured limits." },
  { id: "automation_risk", text: "I understand that Full Auto mode places trades without per-trade approval. I will start with Full Manual or Semi-Auto first." },
  { id: "my_responsibility", text: "I am legally and financially responsible for all trades executed by this system, even in automated modes." },
  { id: "keys_security", text: "I will keep my API keys secure and never commit my .env file to a public repository." },
  { id: "paper_first", text: "I understand paper trading and backtest review are strongly recommended before switching to live mode, but that decision is mine." },
];

export default function RiskAcknowledgment({
  canContinue,
  onComplete,
}: {
  canContinue: boolean;
  onComplete: () => void;
}) {
  const [accepted, setAccepted] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggle = (id: string) =>
    setAccepted((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      await api.acknowledgeRisks(accepted);
      setSaved(true);
      if (canContinue) {
        onComplete();
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to record acknowledgment.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel
      title="Trading risk acknowledgment"
      eyebrow="Step 4"
      action={<StatusBadge label={`${accepted.length}/9 checked`} tone={accepted.length === 9 ? "good" : "warn"} />}
    >
      <div className="space-y-3">
        {RISK_ACKNOWLEDGMENT_ITEMS.map((item) => (
          <label key={item.id} className="flex gap-3 rounded-2xl bg-slate px-4 py-3 text-sm">
            <input type="checkbox" checked={accepted.includes(item.id)} onChange={() => toggle(item.id)} />
            <span>{item.text}</span>
          </label>
        ))}
      </div>
      <button
        className="mt-4 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        disabled={accepted.length !== 9 || saving}
        onClick={() => void submit()}
      >
        {saving ? <ThinkingDots className="text-white" /> : "Record acknowledgment"}
      </button>
      {!canContinue ? (
        <p className="mt-3 text-sm text-ink/65">
          Save your AI provider first, then this step will move you straight into Strategy.
        </p>
      ) : null}
      {saved ? (
        <p className="mt-3 text-sm text-pine">
          Acknowledgment recorded locally. FinPilot will warn clearly about live mode, but the mode choice stays with you.
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-ember">{error}</p> : null}
    </Panel>
  );
}
