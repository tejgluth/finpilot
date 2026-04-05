import type { GuardrailConfig } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "max_position_pct", label: "Max position %", description: "Largest single position allowed.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "max_sector_pct", label: "Max sector %", description: "Largest sector concentration allowed.", type: "number", min: 0, max: 100, step: 0.5 },
  { key: "max_open_positions", label: "Max open positions", description: "Maximum number of concurrent holdings.", type: "number", min: 1, step: 1 },
  { key: "max_daily_loss_pct", label: "Max daily loss %", description: "Daily loss breaker threshold.", type: "number", min: 0, max: 100, step: 0.1 },
  { key: "max_weekly_drawdown_pct", label: "Max weekly drawdown %", description: "Weekly drawdown breaker threshold.", type: "number", min: 0, max: 100, step: 0.1 },
  { key: "max_total_drawdown_pct", label: "Max total drawdown %", description: "Portfolio-level drawdown breaker threshold.", type: "number", min: 0, max: 100, step: 0.1 },
  { key: "auto_confirm_max_usd", label: "Auto-confirm max USD", description: "Semi-auto orders below this can execute automatically.", type: "number", min: 0, step: 10 },
  { key: "max_trades_per_day", label: "Max trades per day", description: "Daily trade-count limiter.", type: "number", min: 1, step: 1 },
  { key: "trading_hours_only", label: "Trading hours only", description: "Restrict execution to regular market hours.", type: "boolean" },
  { key: "max_data_age_minutes", label: "Max data age (minutes)", description: "If inputs are older than this, execution confidence is penalized.", type: "number", min: 1, step: 1 },
];

export default function GuardrailSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: GuardrailConfig;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="Guardrails are still clamped server-side, so unsafe values will not persist even if you try to raise them too high."
      onSave={onSave}
      saving={saving}
      sectionKey="guardrails"
      title="Guardrails"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
