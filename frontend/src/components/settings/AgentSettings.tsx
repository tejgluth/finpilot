import type { AgentSettings as AgentSettingsType } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "enable_fundamentals", label: "Fundamentals agent", description: "Balance sheet and earnings context.", type: "boolean" },
  { key: "enable_technicals", label: "Technicals agent", description: "Indicator-driven market structure.", type: "boolean" },
  { key: "enable_sentiment", label: "Sentiment agent", description: "News, options, and Reddit sentiment.", type: "boolean" },
  { key: "enable_macro", label: "Macro agent", description: "Rates, inflation, and regime analysis.", type: "boolean" },
  { key: "enable_value", label: "Value agent", description: "Valuation and filing-based value lens.", type: "boolean" },
  { key: "enable_momentum", label: "Momentum agent", description: "Relative strength and trend persistence.", type: "boolean" },
  { key: "enable_growth", label: "Growth agent", description: "Growth quality and earnings surprise lens.", type: "boolean" },
  { key: "enable_bull_bear_debate", label: "Bull/bear debate", description: "Cross-check analysis before decisions.", type: "boolean" },
  { key: "default_weight_fundamentals", label: "Fundamentals weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_technicals", label: "Technicals weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_sentiment", label: "Sentiment weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_macro", label: "Macro weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_value", label: "Value weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_momentum", label: "Momentum weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "default_weight_growth", label: "Growth weight", description: "Default weight inside signal aggregation.", type: "number", min: 0, max: 100, step: 1 },
  { key: "min_confidence_threshold", label: "Minimum confidence threshold", description: "Below this, the risk manager can block action.", type: "number", min: 0, max: 1, step: 0.05 },
  { key: "reddit_lookback_hours", label: "Reddit lookback (hours)", description: "How far back the sentiment agent scans Reddit.", type: "number", min: 1, step: 1 },
  { key: "news_lookback_days", label: "News lookback (days)", description: "How much recent news the sentiment agent considers.", type: "number", min: 1, step: 1 },
];

export default function AgentSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: AgentSettingsType;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="These defaults shape new strategy builds and how the research team weighs signals before the portfolio decision."
      onSave={onSave}
      saving={saving}
      sectionKey="agents"
      title="Agents"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
