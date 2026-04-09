import type { BacktestLiveTeamUpdate } from "../../api/types";

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatStage(stage: string | null) {
  if (!stage) {
    return "Preparing backtest";
  }
  return stage
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function BacktestLivePanel({
  liveTeams,
  stage,
}: {
  liveTeams: BacktestLiveTeamUpdate[];
  stage: string | null;
}) {
  return (
    <div className="space-y-4 rounded-[24px] bg-white/85 px-4 py-4 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-xs font-mono uppercase tracking-[0.28em] text-ink/45">Live Replay</div>
          <div className="text-lg font-semibold text-ink">Portfolio values and recent trades update while the simulation runs.</div>
        </div>
        <div className="rounded-full bg-slate px-3 py-1 text-xs font-semibold text-ink/70">{formatStage(stage)}</div>
      </div>
      {liveTeams.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {liveTeams.map((team) => (
            <div className="rounded-[22px] bg-slate/75 px-4 py-4" key={`${team.team_id}:${team.version_number}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-base font-semibold text-ink">{team.team_name}</div>
                  <div className="text-xs text-ink/55">
                    {team.timestamp} · day {team.processed_days} / {team.total_days} · rebalance {team.processed_rebalances} / {team.total_rebalances}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-[0.22em] text-ink/45">Equity</div>
                  <div className="text-xl font-semibold text-ink">{formatUsd(team.strategy_equity)}</div>
                  <div className="text-xs text-ink/55">Benchmark {formatUsd(team.benchmark_equity)}</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-white/80 px-3 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-ink/45">Cash</div>
                  <div className="mt-1 text-sm font-semibold text-ink">{formatUsd(team.cash)}</div>
                </div>
                <div className="rounded-2xl bg-white/80 px-3 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-ink/45">Exposure</div>
                  <div className="mt-1 text-sm font-semibold text-ink">{team.gross_exposure_pct.toFixed(1)}%</div>
                </div>
                <div className="rounded-2xl bg-white/80 px-3 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-ink/45">Holdings</div>
                  <div className="mt-1 text-sm font-semibold text-ink">{team.holdings_count}</div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div>
                  <div className="mb-2 text-sm font-semibold text-ink">Top holdings</div>
                  {team.holdings.length ? (
                    <div className="space-y-2">
                      {team.holdings.map((holding) => (
                        <div className="flex items-center justify-between rounded-2xl bg-white/80 px-3 py-2 text-sm" key={holding.ticker}>
                          <div>
                            <div className="font-semibold text-ink">{holding.ticker}</div>
                            <div className="text-xs text-ink/55">{holding.shares.toFixed(2)} shares · {holding.weight_pct.toFixed(2)}%</div>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold text-ink">{formatUsd(holding.market_value)}</div>
                            <div className="text-xs text-ink/55">@ {holding.price.toFixed(2)}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-white/80 px-3 py-3 text-sm text-ink/60">No open positions yet.</div>
                  )}
                </div>
                <div>
                  <div className="mb-2 text-sm font-semibold text-ink">Recent trades</div>
                  {team.recent_trades.length ? (
                    <div className="space-y-2">
                      {[...team.recent_trades].reverse().map((trade, index) => (
                        <div className="rounded-2xl bg-white/80 px-3 py-2 text-sm" key={`${trade.timestamp}-${trade.ticker}-${index}`}>
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-semibold text-ink">
                              {trade.action} {trade.ticker}
                            </div>
                            <div className="text-xs text-ink/55">{trade.timestamp}</div>
                          </div>
                          <div className="mt-1 text-xs text-ink/65">
                            {formatUsd(trade.notional_usd)} at {trade.fill_price.toFixed(2)} · score {trade.score.toFixed(2)}
                          </div>
                          {trade.reason ? <div className="mt-1 text-xs text-ink/55">{trade.reason}</div> : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-white/80 px-3 py-3 text-sm text-ink/60">No trades have been generated yet.</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-[22px] bg-slate/75 px-4 py-4 text-sm text-ink/65">
          Loading benchmark data, resolving the universe, and warming up the first simulation snapshot.
        </div>
      )}
    </div>
  );
}
