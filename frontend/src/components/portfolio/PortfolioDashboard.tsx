import type { PortfolioPayload } from "../../api/types";
import Panel from "../common/Panel";
import PositionRow from "./PositionRow";

export default function PortfolioDashboard({ portfolio }: { portfolio: PortfolioPayload }) {
  return (
    <Panel title="Portfolio snapshot" eyebrow="Local analytics">
      <div className="grid gap-3 md:grid-cols-5">
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Cash</div>
          <div className="font-display text-3xl">${portfolio.cash.toFixed(0)}</div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Equity</div>
          <div className="font-display text-3xl">${portfolio.equity.toFixed(0)}</div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Daily P&L</div>
          <div className={`font-display text-3xl ${portfolio.daily_pnl >= 0 ? "text-pine" : "text-ember"}`}>
            ${portfolio.daily_pnl.toFixed(0)}
          </div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Trades</div>
          <div className="font-display text-3xl">{portfolio.trade_count}</div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Backtests</div>
          <div className="font-display text-3xl">{portfolio.backtest_count}</div>
        </div>
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
