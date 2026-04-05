import type { GuardrailConfig } from "../../api/types";
import Panel from "../common/Panel";

export default function GuardrailSettings({ guardrails }: { guardrails: GuardrailConfig }) {
  const rows: Array<[string, number | boolean]> = [
    ["Max position %", guardrails.max_position_pct],
    ["Max sector %", guardrails.max_sector_pct],
    ["Max open positions", guardrails.max_open_positions],
    ["Max daily loss %", guardrails.max_daily_loss_pct],
    ["Max weekly drawdown %", guardrails.max_weekly_drawdown_pct],
    ["Max total drawdown %", guardrails.max_total_drawdown_pct],
    ["Auto-confirm USD", guardrails.auto_confirm_max_usd],
    ["Max trades/day", guardrails.max_trades_per_day],
    ["Trading hours only", guardrails.trading_hours_only],
  ];
  return (
    <Panel title="Guardrail settings" eyebrow="Server-clamped">
      <div className="grid gap-3 md:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-slate px-4 py-3">
            <div className="font-mono text-xs uppercase text-ink/50">{label}</div>
            <div className="text-lg font-semibold">{String(value)}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
