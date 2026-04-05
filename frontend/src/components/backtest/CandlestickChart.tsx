import type { EquityPoint } from "../../api/types";
import Panel from "../common/Panel";

export default function CandlestickChart({ points }: { points: EquityPoint[] }) {
  const latest = points.length ? points[points.length - 1] : undefined;
  return (
    <Panel title="Price view" eyebrow="Baseline chart">
      <div className="rounded-[24px] bg-slate p-5">
        <p className="text-sm text-ink/70">
          This baseline scaffold keeps the chart area reserved for OHLCV overlays. The latest strategy equity is{" "}
          <span className="font-semibold text-ink">
            {latest ? latest.strategy_equity.toFixed(2) : "n/a"}
          </span>
          .
        </p>
      </div>
    </Panel>
  );
}
