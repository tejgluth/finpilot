import { useState } from "react";
import { useStrategyStore } from "../../stores/strategyStore";
import Panel from "../common/Panel";
import type { ComparisonTarget } from "../../api/types";

export default function BacktestPanel({
  onRun,
  loading,
}: {
  onRun: (payload: Record<string, unknown>) => void;
  loading: boolean;
}) {
  const [universeMode, setUniverseMode] = useState<"single_ticker" | "current_sp500" | "csv_snapshot">("single_ticker");
  const [ticker, setTicker] = useState("AAPL");
  const [customUniverseCsv, setCustomUniverseCsv] = useState("");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [initialCash, setInitialCash] = useState(100000);
  const [backtestMode, setBacktestMode] = useState<"backtest_strict" | "backtest_experimental">("backtest_strict");
  const [rebalanceFrequency, setRebalanceFrequency] = useState<"weekly" | "biweekly" | "monthly">("monthly");
  const [selectionCount, setSelectionCount] = useState(10);
  const [maxPositions, setMaxPositions] = useState(10);
  const [weightingMethod, setWeightingMethod] = useState<"equal_weight" | "confidence_weighted">("equal_weight");
  const [fidelityMode, setFidelityMode] = useState<"full_loop" | "hybrid_shortlist">("full_loop");
  const [cachePolicy, setCachePolicy] = useState<"reuse" | "fresh">("reuse");
  const [shortlistSize, setShortlistSize] = useState(40);
  const activeTeam = useStrategyStore((state) => state.activeTeam);
  const teams = useStrategyStore((state) => state.teams);
  const [comparisonTargets, setComparisonTargets] = useState<ComparisonTarget[]>([]);
  const asOfDatetime = `${endDate}T16:00:00+00:00`;

  const availableComparisonTeams = teams.filter(
    (team) => !(team.team_id === activeTeam?.team_id && team.version_number === activeTeam?.version_number),
  );

  const toggleComparison = (target: ComparisonTarget) => {
    const key = `${target.team_id}:${target.version_number ?? "latest"}`;
    setComparisonTargets((current) => {
      const exists = current.some(
        (item) => `${item.team_id}:${item.version_number ?? "latest"}` === key,
      );
      if (exists) {
        return current.filter(
          (item) => `${item.team_id}:${item.version_number ?? "latest"}` !== key,
        );
      }
      return [...current, target].slice(0, 3);
    });
  };

  return (
    <Panel title="Backtest controls" eyebrow="Run">
      <div className="mb-4 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/70">
        Active team: {activeTeam ? `${activeTeam.compiled_team.name} v${activeTeam.version_number}` : "default team"}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Universe mode</span>
          <select
            className="rounded-2xl bg-slate px-4 py-3"
            onChange={(event) => setUniverseMode(event.target.value as "single_ticker" | "current_sp500" | "csv_snapshot")}
            value={universeMode}
          >
            <option value="single_ticker">Single ticker</option>
            <option value="current_sp500">Current S&amp;P 500 (experimental)</option>
            <option value="csv_snapshot">CSV snapshot (strict-safe)</option>
          </select>
        </label>
        {universeMode === "single_ticker" ? (
          <label className="grid gap-2 text-sm">
            <span className="font-semibold text-ink">Ticker</span>
            <input
              className="rounded-2xl bg-slate px-4 py-3"
              value={ticker}
              onChange={(event) => setTicker(event.target.value.toUpperCase())}
            />
          </label>
        ) : null}
        {universeMode === "csv_snapshot" ? (
          <label className="grid gap-2 text-sm md:col-span-2">
            <span className="font-semibold text-ink">Snapshot CSV path</span>
            <input
              className="rounded-2xl bg-slate px-4 py-3"
              placeholder="/absolute/path/to/sp500-2024-03-15.csv"
              value={customUniverseCsv}
              onChange={(event) => setCustomUniverseCsv(event.target.value)}
            />
          </label>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Start date</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">End date</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Initial cash</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" value={initialCash} onChange={(e) => setInitialCash(Number(e.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Mode</span>
          <select className="rounded-2xl bg-slate px-4 py-3" onChange={(e) => setBacktestMode(e.target.value as "backtest_strict" | "backtest_experimental")} value={backtestMode}>
            <option value="backtest_strict">Strict</option>
            <option value="backtest_experimental">Experimental</option>
          </select>
        </label>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Rebalance</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={rebalanceFrequency} onChange={(event) => setRebalanceFrequency(event.target.value as "weekly" | "biweekly" | "monthly")}>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every 2 weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Selection count</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} max={100} value={selectionCount} onChange={(event) => setSelectionCount(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Max positions</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} max={100} value={maxPositions} onChange={(event) => setMaxPositions(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Weighting</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={weightingMethod} onChange={(event) => setWeightingMethod(event.target.value as "equal_weight" | "confidence_weighted")}>
            <option value="equal_weight">Equal weight</option>
            <option value="confidence_weighted">Confidence weighted</option>
          </select>
        </label>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Fidelity mode</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={fidelityMode} onChange={(event) => setFidelityMode(event.target.value as "full_loop" | "hybrid_shortlist")}>
            <option value="full_loop">Full loop</option>
            <option value="hybrid_shortlist">Hybrid shortlist</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Cache policy</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={cachePolicy} onChange={(event) => setCachePolicy(event.target.value as "reuse" | "fresh")}>
            <option value="reuse">Reuse cached decisions</option>
            <option value="fresh">Recompute everything</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Shortlist size</span>
          <input
            className="rounded-2xl bg-slate px-4 py-3"
            type="number"
            min={1}
            max={250}
            disabled={fidelityMode !== "hybrid_shortlist"}
            value={shortlistSize}
            onChange={(event) => setShortlistSize(Number(event.target.value))}
          />
        </label>
      </div>
      <div className="mt-4 space-y-3">
        <div className="text-sm font-semibold text-ink">Comparison targets</div>
        <div className="grid gap-2 md:grid-cols-2">
          {availableComparisonTeams.length ? (
            availableComparisonTeams.map((team) => (
              <label key={`${team.team_id}-${team.version_number}`} className="flex items-center gap-3 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/75">
                <input
                  checked={comparisonTargets.some((item) => item.team_id === team.team_id && item.version_number === team.version_number)}
                  onChange={() => toggleComparison({ team_id: team.team_id, version_number: team.version_number })}
                  type="checkbox"
                />
                <span>{team.compiled_team.name} v{team.version_number}</span>
              </label>
            ))
          ) : (
            <div className="rounded-2xl bg-slate px-4 py-3 text-sm text-ink/60">
              Save another team version if you want a side-by-side comparison run.
            </div>
          )}
        </div>
      </div>
      <div className="mt-3 text-xs text-ink/55">
        Strict mode now hard-fails when a team depends on historically unsupported agent families. Experimental mode will run them in degraded mode and show you that gap report.
      </div>
      <button
        className="mt-4 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white"
        onClick={() =>
          onRun({
            ticker: universeMode === "single_ticker" ? ticker : null,
            universe_id: universeMode === "current_sp500" ? "current_sp500" : "current_sp500",
            custom_universe_csv: universeMode === "csv_snapshot" ? customUniverseCsv : null,
            start_date: startDate,
            end_date: endDate,
            initial_cash: initialCash,
            team_id: activeTeam?.team_id,
            version_number: activeTeam?.version_number,
            comparison_targets: comparisonTargets,
            as_of_datetime: asOfDatetime,
            backtest_mode: backtestMode,
            rebalance_frequency: rebalanceFrequency,
            selection_count: selectionCount,
            max_positions: maxPositions,
            weighting_method: weightingMethod,
            fidelity_mode: fidelityMode,
            cache_policy: cachePolicy,
            shortlist_size: shortlistSize,
          })
        }
      >
        {loading ? "Running…" : "Run truthful backtest"}
      </button>
    </Panel>
  );
}
