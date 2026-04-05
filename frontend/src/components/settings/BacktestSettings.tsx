import type { BacktestSettings } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "default_initial_cash", label: "Default initial cash", description: "Starting capital for new backtests.", type: "number", min: 0, step: 1000 },
  { key: "default_slippage_pct", label: "Default slippage %", description: "Execution friction applied in backtests.", type: "number", min: 0, step: 0.01 },
  { key: "default_commission_pct", label: "Default commission %", description: "Broker fee assumption in backtests.", type: "number", min: 0, step: 0.01 },
  { key: "default_max_position_pct", label: "Default max position %", description: "Sizing ceiling used in new backtests.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_lookback_years", label: "Default lookback years", description: "Historical range used when starting a new test.", type: "number", min: 1, step: 1 },
  {
    key: "default_fidelity_mode",
    label: "Default fidelity mode",
    description: "Choose between full paper-trade replay and a faster scout shortlist.",
    type: "select",
    options: [
      { label: "Full loop", value: "full_loop" },
      { label: "Hybrid shortlist", value: "hybrid_shortlist" },
    ],
  },
  {
    key: "default_cache_policy",
    label: "Default cache policy",
    description: "Reuse past historical analyses or force fresh evaluation.",
    type: "select",
    options: [
      { label: "Reuse cache", value: "reuse" },
      { label: "Fresh recompute", value: "fresh" },
    ],
  },
  { key: "default_shortlist_size", label: "Default shortlist size", description: "How many names hybrid mode sends into the full loop.", type: "number", min: 1, step: 1 },
  { key: "max_parallel_historical_evaluations", label: "Max parallel evaluations", description: "Concurrency limit for historical ticker analysis.", type: "number", min: 1, step: 1 },
  { key: "max_cost_per_backtest_usd", label: "Max LLM cost per backtest", description: "Dedicated historical replay budget.", type: "number", min: 0, step: 0.1 },
  { key: "max_tokens_per_backtest", label: "Max tokens per backtest", description: "Token ceiling for shared historical replay budget.", type: "number", min: 1000, step: 1000 },
  { key: "walk_forward_enabled", label: "Enable walk-forward by default", description: "Turn rolling validation on for new runs.", type: "boolean" },
  { key: "walk_forward_window_months", label: "Walk-forward window (months)", description: "Training window length for walk-forward tests.", type: "number", min: 1, step: 1 },
  { key: "show_transaction_costs_separately", label: "Show costs separately", description: "Keep transaction costs isolated in result summaries.", type: "boolean" },
];

export default function BacktestSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: BacktestSettings;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="These defaults shape new backtests, not historical results you already stored."
      onSave={onSave}
      saving={saving}
      sectionKey="backtest"
      title="Backtesting"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
