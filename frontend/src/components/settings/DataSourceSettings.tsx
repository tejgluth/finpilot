import type { DataSourceSettings as DataSourceSettingsType } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "use_yfinance", label: "Use yfinance", description: "Core free market data.", type: "boolean" },
  { key: "use_fred", label: "Use FRED", description: "Macro series and rates data.", type: "boolean" },
  { key: "use_edgar", label: "Use SEC EDGAR", description: "Filing text and reporting history.", type: "boolean" },
  { key: "use_sec_companyfacts", label: "Use SEC CompanyFacts", description: "Free point-in-time XBRL fundamentals from SEC filings.", type: "boolean" },
  { key: "use_gdelt", label: "Use GDELT", description: "Free historical news archive for replay-safe sentiment.", type: "boolean" },
  { key: "use_coingecko", label: "Use CoinGecko", description: "Crypto pricing coverage.", type: "boolean" },
  { key: "use_alpaca_data", label: "Use Alpaca market data", description: "Requires Alpaca credentials.", type: "boolean" },
  { key: "use_finnhub", label: "Use Finnhub", description: "News and sentiment coverage.", type: "boolean" },
  { key: "use_marketaux", label: "Use Marketaux", description: "Entity-aware market news.", type: "boolean" },
  { key: "use_fmp", label: "Use FMP", description: "Earnings surprises and analyst context.", type: "boolean" },
  { key: "use_reddit", label: "Use Reddit", description: "Reddit mention and sentiment sampling.", type: "boolean" },
  { key: "use_polygon", label: "Use Polygon", description: "Premium market data.", type: "boolean" },
  { key: "cache_ttl_prices", label: "Price cache TTL (minutes)", description: "How long to reuse price snapshots locally.", type: "number", min: 1, step: 1 },
  { key: "cache_ttl_fundamentals", label: "Fundamentals cache TTL (minutes)", description: "How long fundamentals stay fresh locally.", type: "number", min: 1, step: 1 },
  { key: "cache_ttl_news", label: "News cache TTL (minutes)", description: "Shorter values refresh sentiment faster.", type: "number", min: 1, step: 1 },
  { key: "cache_ttl_macro", label: "Macro cache TTL (minutes)", description: "Longer values are usually fine for macro data.", type: "number", min: 1, step: 1 },
  { key: "max_data_age_minutes", label: "Max acceptable data age (minutes)", description: "Signals older than this get penalized.", type: "number", min: 1, step: 1 },
  { key: "min_data_coverage_pct", label: "Min data coverage", description: "Coverage floor before signals become unreliable.", type: "number", min: 0, max: 1, step: 0.05 },
  {
    key: "alpaca_plan_override",
    label: "Alpaca plan override",
    description: "Use auto unless you intentionally want to override detected plan limits.",
    type: "select",
    options: [
      { label: "Auto detect", value: "auto" },
      { label: "Free", value: "free" },
      { label: "Algo Trader Plus", value: "algo_trader" },
      { label: "Unlimited", value: "unlimited" },
    ],
  },
];

export default function DataSourceSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: DataSourceSettingsType;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="Turn on only the providers you actually want FinPilot to use. Missing API keys will still prevent those providers from working."
      onSave={onSave}
      saving={saving}
      sectionKey="data_sources"
      title="Data sources"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
