import type { TeamBacktestRun } from "../../api/types";
import Panel from "../common/Panel";

export default function TradeLog({ runs }: { runs: TeamBacktestRun[] }) {
  const latestHoldings = (run: TeamBacktestRun) =>
    run.top_holdings_over_time.length
      ? run.top_holdings_over_time[run.top_holdings_over_time.length - 1]?.holdings ?? []
      : [];

  if (!runs.some((run) => run.trades.length)) {
    return (
      <Panel title="Trade log" eyebrow="Execution trace">
        <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
          This run did not place any rebalances or all target weights resolved to cash.
        </div>
      </Panel>
    );
  }

  return (
    <Panel title="Trade log" eyebrow="Execution trace">
      <div className="space-y-4">
        {runs.map((run) => (
          <div key={`${run.team_id}:${run.version_number}`} className="overflow-hidden rounded-2xl border border-ink/10">
            <div className="bg-slate px-4 py-3 text-sm font-semibold text-ink">
              {run.team_name} v{run.version_number}
            </div>
            <div className="grid gap-2 border-b border-ink/10 bg-white px-4 py-3 text-xs text-ink/65 md:grid-cols-3">
              <div>Executed: {run.supported_agents.length ? run.supported_agents.join(", ") : "None"}</div>
              <div>
                Degraded but used: {run.degraded_agents.length ? run.degraded_agents.map((agent) => agent.agent_name).join(", ") : "None"}
              </div>
              <div>
                Cache: {run.cache_usage.hits} hits / {run.cache_usage.misses} misses / {run.cache_usage.writes} writes
              </div>
            </div>
            {run.effective_signature?.summary ? (
              <div className="border-b border-ink/10 bg-white px-4 py-3 text-sm text-ink/70">
                {run.effective_signature.summary}
              </div>
            ) : null}
            {run.trades.length ? (
              <table className="w-full text-sm">
                <thead className="bg-slate/60 text-left">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Ticker</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Notional</th>
                    <th className="px-4 py-3">Fill</th>
                    <th className="px-4 py-3">Cost</th>
                    <th className="px-4 py-3">Prev</th>
                    <th className="px-4 py-3">Weight</th>
                    <th className="px-4 py-3">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {run.trades.map((trade, index) => (
                    <tr key={`${run.team_id}:${run.version_number}:${String(trade.timestamp ?? index)}-${String(trade.ticker ?? index)}`} className="border-t border-ink/10">
                      <td className="px-4 py-3">{String(trade.timestamp ?? "-")}</td>
                      <td className="px-4 py-3">{String(trade.ticker ?? "-")}</td>
                      <td className="px-4 py-3">{String(trade.action ?? "-")}</td>
                      <td className="px-4 py-3">${Number(trade.notional_usd ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3">${Number(trade.fill_price ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3">${Number(trade.cost_usd ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3">{Number(trade.previous_weight_pct ?? 0).toFixed(2)}%</td>
                      <td className="px-4 py-3">{Number(trade.weight_pct ?? 0).toFixed(2)}%</td>
                      <td className="px-4 py-3 text-ink/60">{String(trade.reason ?? "-")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="px-4 py-4 text-sm text-ink/65">
                This team stayed in cash or did not trigger any rebalance trades.
              </div>
            )}
            {run.top_holdings_over_time.length ? (
              <div className="border-t border-ink/10 bg-white px-4 py-4 text-sm text-ink/70">
                <div className="font-semibold text-ink">Latest holdings snapshot</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {latestHoldings(run).map((holding) => (
                    <span key={`${run.team_id}:${run.version_number}:${holding.ticker}`} className="rounded-full bg-slate px-3 py-1 text-xs">
                      {holding.ticker} {holding.weight_pct.toFixed(2)}%
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </Panel>
  );
}
