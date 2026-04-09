import type { TradingStatusPayload } from "../../api/types";
import Panel from "../common/Panel";
import StatusBadge from "../common/StatusBadge";

function formatPermissionLevel(level: string): string {
  switch (level.toUpperCase()) {
    case "FULL_MANUAL": return "Manual approval";
    case "SEMI_AUTO": return "Semi-auto";
    case "FULL_AUTO": return "Full auto";
    default: return level.replace(/_/g, " ").toLowerCase().replace(/\b\w/, (c) => c.toUpperCase());
  }
}

export default function TradingStatus({ status }: { status: TradingStatusPayload }) {
  const isLive = status.alpaca_mode === "live";

  return (
    <Panel title="Trading status" eyebrow="Live controls">
      <div className="flex flex-wrap gap-2">
        <StatusBadge label={isLive ? "Live" : "Paper mode"} tone={isLive ? "danger" : "good"} />
        <StatusBadge label={formatPermissionLevel(status.permission_level)} tone="neutral" />
        <StatusBadge
          label={status.live_risk_acknowledged ? "Risks acknowledged" : "Review risks"}
          tone={status.live_risk_acknowledged ? "warn" : "neutral"}
        />
        <StatusBadge
          label={status.live_unlock.ready ? "Gates passed" : `${status.paper_trading_days_completed}/${status.live_unlock.minimum_paper_trading_days} paper days`}
          tone={status.live_unlock.ready ? "good" : "warn"}
        />
        <StatusBadge
          label={status.kill_switch.active ? "Kill switch on" : "Kill switch idle"}
          tone={status.kill_switch.active ? "danger" : "good"}
        />
      </div>
      <p className={`mt-4 text-sm ${isLive ? "text-ember" : "text-ink/70"}`}>{status.mode_notice}</p>
    </Panel>
  );
}
