import { useEffect } from "react";
import BacktestPanel from "../components/backtest/BacktestPanel";
import BullBearDebate from "../components/backtest/BullBearDebate";
import EquityCurve from "../components/backtest/EquityCurve";
import ArtifactBadge from "../components/backtest/ArtifactBadge";
import BacktestLivePanel from "../components/backtest/BacktestLivePanel";
import MetricsTable from "../components/backtest/MetricsTable";
import SignalTrace from "../components/backtest/SignalTrace";
import TradeLog from "../components/backtest/TradeLog";
import { useBacktestStream } from "../hooks/useBacktestStream";
import { useStrategyStore } from "../stores/strategyStore";

export default function BacktestPage() {
  const { result, loading, stage, liveTeams, runBacktest, error } = useBacktestStream();
  const hydrateStrategy = useStrategyStore((state) => state.hydrate);

  useEffect(() => {
    void hydrateStrategy();
  }, [hydrateStrategy]);

  return (
    <div className="space-y-6">
      <BacktestPanel loading={loading} onRun={(payload) => void runBacktest(payload)} />
      {loading ? (
        <BacktestLivePanel liveTeams={liveTeams} stage={stage} />
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
            <div className="rounded-[24px] border border-ink/[0.07] bg-white/80 px-5 py-4 text-sm text-ink/70">
              <div className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-[0.25em] text-ink/35">
                Run configuration
              </div>
              <div className="font-semibold text-ink mb-2">Historical diagnostics</div>
              <p className="text-[12px] leading-relaxed">
                Mode: <span className="text-ink font-medium">{result.fidelity_mode}</span> · Cache: <span className="text-ink font-medium">{result.cache_policy}</span> · Universe: <span className="text-ink font-medium">{result.universe_resolution_report.source}</span>
              </p>
              <p className="mt-1.5 text-[12px] leading-relaxed">
                Weighting: <span className="text-ink font-medium">{String(result.portfolio_construction.weighting_mode ?? "—")}</span> · Top {result.top_n_holdings} holdings · Pool of {String(result.portfolio_construction.candidate_pool_size ?? result.shortlist_size)}
              </p>
              {result.historical_gap_report.warnings.length ? (
                <p className="mt-2 text-[12px] text-ember">{result.historical_gap_report.warnings.join(" ")}</p>
              ) : null}
            </div>
            <div className="rounded-[24px] border border-ink/[0.07] bg-white/80 px-5 py-4 text-sm text-ink/70">
              <div className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-[0.25em] text-ink/35">
                Equivalence check
              </div>
              <div className="font-semibold text-ink mb-2">Team signal overlap</div>
              <p className="text-[12px] leading-relaxed">
                {result.team_equivalence_warnings.length
                  ? result.team_equivalence_warnings.join(" ")
                  : "No significant overlap detected between the teams in this run."}
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
