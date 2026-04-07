import type { BacktestSettings } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "default_initial_cash", label: "Default initial cash", description: "Starting capital for new backtests.", type: "number", min: 0, step: 1000 },
  { key: "default_slippage_pct", label: "Default slippage %", description: "Execution friction applied in backtests.", type: "number", min: 0, step: 0.01 },
  { key: "default_commission_pct", label: "Default commission %", description: "Broker fee assumption in backtests.", type: "number", min: 0, step: 0.01 },
  { key: "default_max_position_pct", label: "Default max position %", description: "Sizing ceiling used in new backtests.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_min_position_pct", label: "Default min position %", description: "Smallest target allocation for selected names.", type: "number", min: 0, max: 100, step: 0.25 },
  { key: "default_cash_floor_pct", label: "Default cash floor %", description: "Minimum cash reserve when the opportunity set is strong.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_max_gross_exposure_pct", label: "Default max gross %", description: "Upper bound on deployed capital before any cash reserve.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_lookback_years", label: "Default lookback years", description: "Historical range used when starting a new test.", type: "number", min: 1, step: 1 },
  {
    key: "default_universe_id",
    label: "Default universe",
    description: "Base universe used for new backtests before any filters apply.",
    type: "select",
    options: [
      { label: "Current S&P 500", value: "current_sp500" },
      { label: "Single ticker", value: "single_ticker" },
    ],
  },
  { key: "default_min_price", label: "Min price", description: "Point-in-time price floor for the eligible universe.", type: "number", min: 0, step: 0.5 },
  { key: "default_min_avg_dollar_volume_millions", label: "Min ADV ($M)", description: "Liquidity filter applied before candidate ranking.", type: "number", min: 0, step: 1 },
  { key: "default_liquidity_lookback_days", label: "Liquidity lookback", description: "Trailing days used for average dollar volume.", type: "number", min: 5, step: 1 },
  { key: "default_min_history_days", label: "Min history days", description: "Minimum bar count required before a name enters the candidate pool.", type: "number", min: 30, step: 1 },
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
  { key: "default_candidate_pool_size", label: "Candidate pool size", description: "How many names the scout sends into full multi-agent analysis.", type: "number", min: 1, step: 1 },
  { key: "default_shortlist_size", label: "Legacy shortlist size", description: "Compatibility alias for older runs and saved requests.", type: "number", min: 1, step: 1 },
  { key: "default_top_n_holdings", label: "Top-N holdings", description: "Maximum holdings after rank-select-weight construction.", type: "number", min: 1, step: 1 },
  { key: "default_min_conviction_score", label: "Min conviction score", description: "Priority score threshold required to allocate capital.", type: "number", min: 0, max: 1, step: 0.01 },
  {
    key: "default_weighting_mode",
    label: "Weighting mode",
    description: "Default portfolio construction method for new runs.",
    type: "select",
    options: [
      { label: "Capped conviction", value: "capped_conviction" },
      { label: "Risk budgeted", value: "risk_budgeted" },
      { label: "Confidence weighted", value: "confidence_weighted" },
      { label: "Equal weight", value: "equal_weight" },
    ],
  },
  {
    key: "default_score_normalization_mode",
    label: "Score normalization",
    description: "Shape of the conviction-to-weight curve.",
    type: "select",
    options: [
      { label: "Power", value: "power" },
      { label: "Linear", value: "linear" },
    ],
  },
  { key: "default_score_exponent", label: "Score exponent", description: "Higher values make strong ideas more top-heavy.", type: "number", min: 1, max: 4, step: 0.05 },
  {
    key: "default_risk_adjustment_mode",
    label: "Risk adjustment",
    description: "Optional volatility-aware downweighting.",
    type: "select",
    options: [
      { label: "Mild inverse vol", value: "mild_inverse_vol" },
      { label: "Full inverse vol", value: "full_inverse_vol" },
      { label: "None", value: "none" },
    ],
  },
  { key: "default_selection_buffer_pct", label: "Selection buffer", description: "Extra rank room granted to incumbents before replacement.", type: "number", min: 0, max: 1, step: 0.05 },
  { key: "default_replacement_threshold", label: "Replacement threshold", description: "Minimum score gap required for a new name to displace an old one.", type: "number", min: 0, max: 1, step: 0.01 },
  { key: "default_hold_zone_pct", label: "Hold zone %", description: "No-trade band around current weights to reduce churn.", type: "number", min: 0, max: 100, step: 0.25 },
  { key: "default_turnover_buffer_pct", label: "Turnover buffer", description: "Fraction of continuing-weight changes intentionally left untraded.", type: "number", min: 0, max: 0.95, step: 0.05 },
  { key: "default_max_turnover_pct", label: "Max turnover %", description: "Per-rebalance turnover ceiling before changes are scaled back.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_sector_cap_pct", label: "Sector cap %", description: "Maximum weight allowed in any single sector.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "default_persistence_bonus", label: "Persistence bonus", description: "Extra rank support granted to current holdings.", type: "number", min: 0, max: 1, step: 0.01 },
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
