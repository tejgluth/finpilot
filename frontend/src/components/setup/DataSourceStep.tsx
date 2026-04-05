import type { DataSourceSettings } from "../../api/types";
import Panel from "../common/Panel";

const labels: Array<[keyof DataSourceSettings, string]> = [
  ["use_yfinance", "yfinance"],
  ["use_fred", "FRED"],
  ["use_edgar", "SEC EDGAR"],
  ["use_coingecko", "CoinGecko"],
  ["use_alpaca_data", "Alpaca Data"],
  ["use_finnhub", "Finnhub"],
  ["use_marketaux", "Marketaux"],
  ["use_fmp", "FMP"],
  ["use_reddit", "Reddit"],
  ["use_polygon", "Polygon"],
];

export default function DataSourceStep({ dataSources }: { dataSources: DataSourceSettings }) {
  return (
    <Panel title="Data source posture" eyebrow="Step 2">
      <div className="grid gap-3 md:grid-cols-2">
        {labels.map(([key, label]) => (
          <div key={String(key)} className="rounded-2xl bg-slate px-4 py-3">
            <div className="font-semibold">{label}</div>
            <div className="text-sm text-ink/60">{dataSources[key] ? "Enabled" : "Disabled"}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
