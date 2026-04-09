import { useState } from "react";
import { api } from "../../api/client";
import type { TradeOrderPreview } from "../../api/types";
import { useStrategyStore } from "../../stores/strategyStore";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";
import OrderConfirm from "./OrderConfirm";

export default function TradeTicket({ onSubmitted }: { onSubmitted?: () => void }) {
  const activeTeam = useStrategyStore((state) => state.activeTeam);
  const [ticker, setTicker] = useState("AAPL");
  const [action, setAction] = useState<"BUY" | "SELL">("BUY");
  const [notionalUsd, setNotionalUsd] = useState(250);
  const [preview, setPreview] = useState<TradeOrderPreview | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (confirm = false) => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const response = await api.submitOrder({
        ticker,
        action,
        notional_usd: notionalUsd,
        confirm,
        team_id: activeTeam?.team_id ?? null,
      });
      setPreview(response.preview);
      if (response.requires_confirmation) {
        setConfirmOpen(true);
        return;
      }
      setConfirmOpen(false);
      setSuccess(`Submitted ${action} ${ticker.toUpperCase()} for $${notionalUsd.toFixed(2)}.`);
      await onSubmitted?.();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit the trade.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title="Order ticket" eyebrow="Paper or broker execution">
      <div className="grid gap-3 md:grid-cols-3">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Ticker</span>
          <input className="rounded-2xl bg-slate px-4 py-3" value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Action</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={action} onChange={(event) => setAction(event.target.value as "BUY" | "SELL")}>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Notional USD</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} value={notionalUsd} onChange={(event) => setNotionalUsd(Number(event.target.value))} />
        </label>
      </div>
      {preview ? (
        <div className="mt-4 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/70">
          Estimated {String(preview.action ?? action)} {String(preview.ticker ?? ticker)} at about $
          {Number(preview.estimated_price ?? 0).toFixed(2)} for approximately {Number(preview.estimated_quantity ?? 0).toFixed(6)} shares.
        </div>
      ) : null}
      {error ? <div className="mt-4 rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      {success ? <div className="mt-4 rounded-2xl bg-pine/10 px-4 py-3 text-sm text-pine">{success}</div> : null}
      <button className="mt-4 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" disabled={saving} onClick={() => void submit(false)}>
        {saving ? <ThinkingDots className="text-white" /> : "Preview or submit"}
      </button>

      <OrderConfirm
        open={confirmOpen}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void submit(true)}
        title="Confirm order submission"
      >
        <div className="text-sm text-ink/75">
          Submit {String(preview?.action ?? action)} {String(preview?.ticker ?? ticker)} for ${notionalUsd.toFixed(2)}?
        </div>
      </OrderConfirm>
    </Panel>
  );
}
