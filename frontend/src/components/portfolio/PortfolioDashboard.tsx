import type { PortfolioPayload } from "../../api/types";
import Panel from "../common/Panel";
import PositionRow from "./PositionRow";

export default function PortfolioDashboard({ portfolio }: { portfolio: PortfolioPayload }) {
  return (
    <Panel title="Portfolio" eyebrow="Current snapshot">
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-5">
        {[
          { label: "Cash", value: `$${portfolio.cash.toFixed(0)}`, color: "" },
          { label: "Equity", value: `$${portfolio.equity.toFixed(0)}`, color: "" },
          {
            label: "Daily P&L",
            value: `${portfolio.daily_pnl >= 0 ? "+" : ""}$${portfolio.daily_pnl.toFixed(0)}`,
            color: portfolio.daily_pnl >= 0 ? "text-pine" : "text-ember",
          },
          { label: "Trades", value: String(portfolio.trade_count), color: "" },
          { label: "Backtests", value: String(portfolio.backtest_count), color: "" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-[18px] border border-ink/[0.06] bg-slate/70 px-4 py-3.5">
            <div className="mb-1 font-mono text-[9px] font-semibold uppercase tracking-[0.2em] text-ink/40">
              {label}
            </div>
            <div className={`font-display text-2xl font-semibold leading-none ${color || "text-ink"}`}>
              {value}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 space-y-3">
        {portfolio.positions.length ? (
          portfolio.positions.map((position) => (
            <PositionRow
              key={position.ticker}
              ticker={position.ticker}
              quantity={position.quantity}
              marketValue={position.market_value}
              unrealizedPnl={position.unrealized_pnl}
            />
          ))
        ) : (
          <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
            No open positions are recorded yet.
          </div>
        )}
      </div>
    </Panel>
  );
}
