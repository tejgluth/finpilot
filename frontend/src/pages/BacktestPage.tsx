import { useEffect } from "react";
import BacktestPanel from "../components/backtest/BacktestPanel";
import BullBearDebate from "../components/backtest/BullBearDebate";
import EquityCurve from "../components/backtest/EquityCurve";
import ArtifactBadge from "../components/backtest/ArtifactBadge";
import MetricsTable from "../components/backtest/MetricsTable";
import SignalTrace from "../components/backtest/SignalTrace";
import TradeLog from "../components/backtest/TradeLog";
import { useBacktestStream } from "../hooks/useBacktestStream";
import { useStrategyStore } from "../stores/strategyStore";

export default function BacktestPage() {
  const { result, loading, progress, runBacktest, error } = useBacktestStream();
  const hydrateStrategy = useStrategyStore((state) => state.hydrate);

  useEffect(() => {
    void hydrateStrategy();
  }, [hydrateStrategy]);

  return (
    <div className="space-y-6">
      <BacktestPanel loading={loading} onRun={(payload) => void runBacktest(payload)} />
      {loading ? (
        <div className="rounded-[24px] bg-white/80 px-4 py-3 text-sm text-ink/70">
          Backtest progress: {progress}%
        </div>
      ) : null}
      {error ? <div className="rounded-[24px] bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      {result ? (
        <>
          {result.warnings.length ? (
            <div className="rounded-[24px] bg-gold/10 px-4 py-3 text-sm text-gold">
              {result.warnings.join(" ")}
            </div>
          ) : null}
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-[24px] bg-white/80 px-4 py-4 text-sm text-ink/70">
              <div className="font-semibold text-ink">Historical diagnostics</div>
              <p className="mt-2">
                Mode: {result.fidelity_mode} · Cache: {result.cache_policy} · Universe source: {result.universe_resolution_report.source}
              </p>
              <p className="mt-2">
                Construction: {String(result.portfolio_construction.weighting_mode ?? "-")} · top {result.top_n_holdings} · candidate pool {String(result.portfolio_construction.candidate_pool_size ?? result.shortlist_size)}
              </p>
              {result.historical_gap_report.warnings.length ? (
                <p className="mt-2 text-ember">{result.historical_gap_report.warnings.join(" ")}</p>
              ) : null}
            </div>
            <div className="rounded-[24px] bg-white/80 px-4 py-4 text-sm text-ink/70">
              <div className="font-semibold text-ink">Why teams may look similar</div>
              <p className="mt-2">
                {result.team_equivalence_warnings.length
                  ? result.team_equivalence_warnings.join(" ")
                  : "No historical equivalence warning was triggered for this comparison."}
              </p>
            </div>
          </div>
          <EquityCurve teamRuns={result.team_runs} />
          <MetricsTable benchmark={result.benchmark_metrics} teamRuns={result.team_runs} />
          <SignalTrace decisionEvents={result.decision_events.filter((event) => event.selected_for_execution)} />
          <BullBearDebate decisionEvents={result.decision_events.filter((event) => event.selected_for_execution)} />
          <TradeLog runs={result.team_runs} />
          <ArtifactBadge artifact={result.artifact} />
        </>
      ) : null}
    </div>
  );
}
