import { useEffect, useState } from "react";
import type { ComparisonTarget } from "../../api/types";
import { useSettings } from "../../hooks/useSettings";
import { useStrategyStore } from "../../stores/strategyStore";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";
import TeamSelectorDropdown from "../strategy/TeamSelectorDropdown";

type UniverseMode = "single_ticker" | "current_sp500" | "csv_snapshot";
type BacktestMode = "backtest_strict" | "backtest_experimental";
type RebalanceFrequency = "weekly" | "biweekly" | "monthly";
type FidelityMode = "full_loop" | "hybrid_shortlist";
type CachePolicy = "reuse" | "fresh";
type WeightingMode = "equal_weight" | "confidence_weighted" | "capped_conviction" | "risk_budgeted";
type ScoreNormalizationMode = "linear" | "power";
type RiskAdjustmentMode = "none" | "mild_inverse_vol" | "full_inverse_vol";

export default function BacktestPanel({
  onRun,
  loading,
}: {
  onRun: (payload: Record<string, unknown>) => void;
  loading: boolean;
}) {
  const { settings } = useSettings();
  const activeTeam = useStrategyStore((state) => state.activeTeam);
  const teams = useStrategyStore((state) => state.teams);
  const selectTeam = useStrategyStore((state) => state.selectTeam);
  const strategySaving = useStrategyStore((state) => state.saving);

  const [universeMode, setUniverseMode] = useState<UniverseMode>("current_sp500");
  const [ticker, setTicker] = useState("AAPL");
  const [customUniverseCsv, setCustomUniverseCsv] = useState("");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [initialCash, setInitialCash] = useState(100000);
  const [backtestMode, setBacktestMode] = useState<BacktestMode>("backtest_experimental");
  const [rebalanceFrequency, setRebalanceFrequency] = useState<RebalanceFrequency>("weekly");
  const [candidatePoolSize, setCandidatePoolSize] = useState(60);
  const [topNHoldings, setTopNHoldings] = useState(10);
  const [minConvictionScore, setMinConvictionScore] = useState(0.18);
  const [minConfidenceThreshold, setMinConfidenceThreshold] = useState(0.55);
  const [weightingMode, setWeightingMode] = useState<WeightingMode>("confidence_weighted");
  const [scoreNormalizationMode, setScoreNormalizationMode] = useState<ScoreNormalizationMode>("power");
  const [scoreExponent, setScoreExponent] = useState(1.6);
  const [riskAdjustmentMode, setRiskAdjustmentMode] = useState<RiskAdjustmentMode>("mild_inverse_vol");
  const [minPositionPct, setMinPositionPct] = useState(2);
  const [maxPositionPct, setMaxPositionPct] = useState(12);
  const [cashFloorPct, setCashFloorPct] = useState(5);
  const [maxGrossExposurePct, setMaxGrossExposurePct] = useState(100);
  const [sectorCapPct, setSectorCapPct] = useState(35);
  const [selectionBufferPct, setSelectionBufferPct] = useState(0.5);
  const [replacementThreshold, setReplacementThreshold] = useState(0.06);
  const [holdZonePct, setHoldZonePct] = useState(1.0);
  const [turnoverBufferPct, setTurnoverBufferPct] = useState(0.35);
  const [maxTurnoverPct, setMaxTurnoverPct] = useState(25);
  const [persistenceBonus, setPersistenceBonus] = useState(0.03);
  const [minPrice, setMinPrice] = useState(5);
  const [minAvgDollarVolumeMillions, setMinAvgDollarVolumeMillions] = useState(25);
  const [liquidityLookbackDays, setLiquidityLookbackDays] = useState(30);
  const [minHistoryDays, setMinHistoryDays] = useState(252);
  const [fidelityMode, setFidelityMode] = useState<FidelityMode>("full_loop");
  const [cachePolicy, setCachePolicy] = useState<CachePolicy>("reuse");
  const [comparisonTargets, setComparisonTargets] = useState<ComparisonTarget[]>([]);

  useEffect(() => {
    if (!settings) {
      return;
    }
    const profile = activeTeam?.compiled_team.portfolio_construction;
    setInitialCash(settings.backtest.default_initial_cash);
    setCandidatePoolSize(profile?.candidate_pool_size ?? settings.backtest.default_candidate_pool_size);
    setTopNHoldings(profile?.top_n_target ?? settings.backtest.default_top_n_holdings);
    setMinConvictionScore(profile?.min_conviction_score ?? settings.backtest.default_min_conviction_score);
    setMinConfidenceThreshold(activeTeam?.compiled_team.team_overrides?.min_confidence_threshold as number ?? settings.agents.min_confidence_threshold);
    setWeightingMode(profile?.weighting_mode ?? "confidence_weighted");
    setScoreNormalizationMode(settings.backtest.default_score_normalization_mode);
    setScoreExponent(profile?.score_exponent ?? settings.backtest.default_score_exponent);
    setRiskAdjustmentMode(profile?.risk_adjustment_mode ?? settings.backtest.default_risk_adjustment_mode);
    setMinPositionPct(profile?.min_position_pct ?? settings.backtest.default_min_position_pct);
    setMaxPositionPct(profile?.max_position_pct ?? settings.backtest.default_max_position_pct);
    setCashFloorPct(profile?.cash_floor_pct ?? settings.backtest.default_cash_floor_pct);
    setMaxGrossExposurePct(profile?.max_gross_exposure_pct ?? settings.backtest.default_max_gross_exposure_pct);
    setSectorCapPct(profile?.sector_cap_pct ?? settings.backtest.default_sector_cap_pct);
    setSelectionBufferPct(profile?.selection_buffer_pct ?? settings.backtest.default_selection_buffer_pct);
    setReplacementThreshold(profile?.replacement_threshold ?? settings.backtest.default_replacement_threshold);
    setHoldZonePct(profile?.hold_zone_pct ?? settings.backtest.default_hold_zone_pct);
    setTurnoverBufferPct(profile?.turnover_buffer_pct ?? settings.backtest.default_turnover_buffer_pct);
    setMaxTurnoverPct(profile?.max_turnover_pct ?? settings.backtest.default_max_turnover_pct);
    setPersistenceBonus(profile?.persistence_bonus ?? settings.backtest.default_persistence_bonus);
    setMinPrice(settings.backtest.default_min_price);
    setMinAvgDollarVolumeMillions(settings.backtest.default_min_avg_dollar_volume_millions);
    setLiquidityLookbackDays(settings.backtest.default_liquidity_lookback_days);
    setMinHistoryDays(settings.backtest.default_min_history_days);
    setFidelityMode(settings.backtest.default_fidelity_mode);
    setCachePolicy(settings.backtest.default_cache_policy);
    setRebalanceFrequency((profile?.rebalance_frequency_preference as RebalanceFrequency | undefined) ?? "weekly");
  }, [settings, activeTeam?.team_id, activeTeam?.version_number]);

  const availableComparisonTeams = teams.filter(
    (team) => !(team.team_id === activeTeam?.team_id && team.version_number === activeTeam?.version_number),
  );
  const asOfDatetime = `${endDate}T16:00:00+00:00`;

  const toggleComparison = (target: ComparisonTarget) => {
    const key = `${target.team_id}:${target.version_number ?? "latest"}`;
    setComparisonTargets((current) => {
      const exists = current.some((item) => `${item.team_id}:${item.version_number ?? "latest"}` === key);
      if (exists) {
        return current.filter((item) => `${item.team_id}:${item.version_number ?? "latest"}` !== key);
      }
      return [...current, target].slice(0, 3);
    });
  };

  return (
    <Panel title="Backtest controls" eyebrow="Run">
      <div className="mb-4 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/70">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">Active team:</span>
          <TeamSelectorDropdown
            activeTeam={activeTeam}
            align="left"
            buttonClassName="max-w-full"
            currentLabel={activeTeam?.compiled_team.name ?? "Default team"}
            currentSubtitle={activeTeam ? `v${activeTeam.version_number} · backtest target` : undefined}
            disabled={strategySaving}
            labelClassName="text-base"
            menuClassName="w-[min(28rem,calc(100vw-2rem))]"
            onSelectTeam={(teamId, versionNumber) => selectTeam(teamId, versionNumber)}
            teams={teams}
          />
        </div>
        {activeTeam?.compiled_team.portfolio_construction ? (
          <div className="mt-2 text-xs text-ink/55">
            Style: {activeTeam.compiled_team.portfolio_construction.concentration_style} · {activeTeam.compiled_team.portfolio_construction.weighting_mode} · {activeTeam.compiled_team.portfolio_construction.turnover_style} turnover
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Universe mode</span>
          <select
            className="rounded-2xl bg-slate px-4 py-3"
            onChange={(event) => setUniverseMode(event.target.value as UniverseMode)}
            value={universeMode}
          >
            <option value="single_ticker">Single ticker</option>
            <option value="current_sp500">Current S&amp;P 500</option>
            <option value="csv_snapshot">CSV snapshot</option>
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
              placeholder="/absolute/path/to/universe.csv"
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
          <select className="rounded-2xl bg-slate px-4 py-3" onChange={(e) => setBacktestMode(e.target.value as BacktestMode)} value={backtestMode}>
            <option value="backtest_strict">Strict</option>
            <option value="backtest_experimental">Experimental</option>
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Rebalance</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={rebalanceFrequency} onChange={(event) => setRebalanceFrequency(event.target.value as RebalanceFrequency)}>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every 2 weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Candidate pool</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} max={250} value={candidatePoolSize} onChange={(event) => setCandidatePoolSize(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Top-N holdings</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} max={100} value={topNHoldings} onChange={(event) => setTopNHoldings(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Weighting</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={weightingMode} onChange={(event) => setWeightingMode(event.target.value as WeightingMode)}>
            <option value="capped_conviction">Capped conviction</option>
            <option value="risk_budgeted">Risk budgeted</option>
            <option value="confidence_weighted">Confidence weighted</option>
            <option value="equal_weight">Equal weight</option>
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min conviction</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={1} step={0.01} value={minConvictionScore} onChange={(event) => setMinConvictionScore(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min confidence</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={1} step={0.01} value={minConfidenceThreshold} onChange={(event) => setMinConfidenceThreshold(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Score curve</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={scoreNormalizationMode} onChange={(event) => setScoreNormalizationMode(event.target.value as ScoreNormalizationMode)}>
            <option value="power">Power</option>
            <option value="linear">Linear</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Score exponent</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={1} max={4} step={0.05} value={scoreExponent} onChange={(event) => setScoreExponent(Number(event.target.value))} />
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min position %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={minPositionPct} onChange={(event) => setMinPositionPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Max position %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={maxPositionPct} onChange={(event) => setMaxPositionPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Cash floor %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={cashFloorPct} onChange={(event) => setCashFloorPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Max gross %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={maxGrossExposurePct} onChange={(event) => setMaxGrossExposurePct(Number(event.target.value))} />
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Sector cap %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={sectorCapPct} onChange={(event) => setSectorCapPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Selection buffer</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={1} step={0.05} value={selectionBufferPct} onChange={(event) => setSelectionBufferPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Replacement gap</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={1} step={0.01} value={replacementThreshold} onChange={(event) => setReplacementThreshold(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Persistence bonus</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={1} step={0.01} value={persistenceBonus} onChange={(event) => setPersistenceBonus(Number(event.target.value))} />
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Hold zone %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.25} value={holdZonePct} onChange={(event) => setHoldZonePct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Turnover buffer</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={0.95} step={0.05} value={turnoverBufferPct} onChange={(event) => setTurnoverBufferPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Max turnover %</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} max={100} step={0.5} value={maxTurnoverPct} onChange={(event) => setMaxTurnoverPct(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Risk adjustment</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={riskAdjustmentMode} onChange={(event) => setRiskAdjustmentMode(event.target.value as RiskAdjustmentMode)}>
            <option value="mild_inverse_vol">Mild inverse vol</option>
            <option value="full_inverse_vol">Full inverse vol</option>
            <option value="none">None</option>
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min price</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} step={0.5} value={minPrice} onChange={(event) => setMinPrice(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min ADV ($M)</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={0} step={1} value={minAvgDollarVolumeMillions} onChange={(event) => setMinAvgDollarVolumeMillions(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Liquidity lookback</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={5} step={1} value={liquidityLookbackDays} onChange={(event) => setLiquidityLookbackDays(Number(event.target.value))} />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Min history days</span>
          <input className="rounded-2xl bg-slate px-4 py-3" type="number" min={30} step={1} value={minHistoryDays} onChange={(event) => setMinHistoryDays(Number(event.target.value))} />
        </label>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Fidelity mode</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={fidelityMode} onChange={(event) => setFidelityMode(event.target.value as FidelityMode)}>
            <option value="full_loop">Full loop</option>
            <option value="hybrid_shortlist">Hybrid shortlist</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-semibold text-ink">Cache policy</span>
          <select className="rounded-2xl bg-slate px-4 py-3" value={cachePolicy} onChange={(event) => setCachePolicy(event.target.value as CachePolicy)}>
            <option value="reuse">Reuse cached decisions</option>
            <option value="fresh">Recompute everything</option>
          </select>
        </label>
        <div className="rounded-2xl bg-slate px-4 py-3 text-sm text-ink/70">
          Candidate scout is deterministic and point-in-time only. Current holdings are always re-evaluated, even if they fall outside the scout ranks.
        </div>
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
        Strict mode hard-fails unsupported historical agent families. Experimental mode still degrades them instead of silently pretending they existed.
      </div>

      <button
        className="mt-4 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white"
        onClick={() =>
          onRun({
            ticker: universeMode === "single_ticker" ? ticker : null,
            universe_id: universeMode === "current_sp500" ? "current_sp500" : null,
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
            candidate_pool_size: candidatePoolSize,
            shortlist_size: candidatePoolSize,
            top_n_holdings: topNHoldings,
            selection_count: topNHoldings,
            max_positions: topNHoldings,
            min_conviction_score: minConvictionScore,
            min_confidence_threshold: minConfidenceThreshold,
            weighting_mode: weightingMode,
            weighting_method: weightingMode,
            score_normalization_mode: scoreNormalizationMode,
            score_exponent: scoreExponent,
            risk_adjustment_mode: riskAdjustmentMode,
            min_position_pct: minPositionPct,
            max_position_pct: maxPositionPct,
            cash_floor_pct: cashFloorPct,
            max_gross_exposure_pct: maxGrossExposurePct,
            sector_cap_pct: sectorCapPct,
            selection_buffer_pct: selectionBufferPct,
            replacement_threshold: replacementThreshold,
            hold_zone_pct: holdZonePct,
            turnover_buffer_pct: turnoverBufferPct,
            max_turnover_pct: maxTurnoverPct,
            persistence_bonus: persistenceBonus,
            min_price: minPrice,
            min_avg_dollar_volume_millions: minAvgDollarVolumeMillions,
            liquidity_lookback_days: liquidityLookbackDays,
            min_history_days: minHistoryDays,
            fidelity_mode: fidelityMode,
            cache_policy: cachePolicy,
          })
        }
      >
        {loading ? <ThinkingDots className="text-white" /> : "Run truthful backtest"}
      </button>
    </Panel>
  );
}
