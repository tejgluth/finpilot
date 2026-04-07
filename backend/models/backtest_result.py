from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.agent_team import ExecutionSnapshot
from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision


class EquityPoint(BaseModel):
    timestamp: str
    strategy_equity: float
    benchmark_equity: float


class HistoricalAgentSupport(BaseModel):
    agent_name: str
    support_level: str
    honored_in_strict: bool = False
    degraded_in_experimental: bool = False
    effective_weight: float = 0.0
    reason: str = ""
    owned_sources: list[str] = Field(default_factory=list)


class HistoricalEffectiveSignature(BaseModel):
    team_id: str
    team_name: str
    version_number: int = 0
    honored_agents: list[str] = Field(default_factory=list)
    degraded_agents: list[HistoricalAgentSupport] = Field(default_factory=list)
    effective_weights: dict[str, float] = Field(default_factory=dict)
    ignored_agents: list[str] = Field(default_factory=list)
    summary: str = ""


class HoldingsSnapshot(BaseModel):
    timestamp: str
    team_id: str
    team_name: str
    holdings: list[dict] = Field(default_factory=list)


class CacheUsageSummary(BaseModel):
    hits: int = 0
    misses: int = 0
    writes: int = 0


class DecisionEvent(BaseModel):
    rebalance_date: str
    execution_date: str
    team_id: str
    team_name: str
    version_number: int = 0
    ticker: str
    shortlist_rank: int | None = None
    shortlisted: bool = True
    selected_for_execution: bool = False
    cache_status: str = "miss"
    score: float = 0.0
    current_weight_pct: float = 0.0
    target_weight_pct: float = 0.0
    signals: list[AgentSignal] = Field(default_factory=list)
    bull_case: DebateOutput | None = None
    bear_case: DebateOutput | None = None
    decision: PortfolioDecision
    selection_reason: str = ""
    exclusion_reason: str = ""
    construction_details: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class TeamBacktestRun(BaseModel):
    team_id: str
    team_name: str
    version_number: int = 0
    metrics: dict = Field(default_factory=dict)
    equity_curve: list[EquityPoint] = Field(default_factory=list)
    trades: list[dict] = Field(default_factory=list)
    turnover_pct: float = 0.0
    max_sector_concentration_pct: float = 0.0
    top_holdings_over_time: list[HoldingsSnapshot] = Field(default_factory=list)
    supported_agents: list[str] = Field(default_factory=list)
    degraded_agents: list[HistoricalAgentSupport] = Field(default_factory=list)
    excluded_agents: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    effective_signature: HistoricalEffectiveSignature | None = None
    cache_usage: CacheUsageSummary = Field(default_factory=CacheUsageSummary)


class BacktestArtifact(BaseModel):
    artifact_id: str
    data_hash: str
    config_snapshot: dict = Field(default_factory=dict)
    transaction_cost_model: dict = Field(default_factory=dict)
    portfolio_construction: dict = Field(default_factory=dict)
    created_at: str
    benchmark_symbol: str = "SPY"
    artifact_path: str = ""
    execution_snapshot: ExecutionSnapshot
    temporal_features: dict = Field(default_factory=dict)


class HistoricalGap(BaseModel):
    team_id: str
    team_name: str
    version_number: int = 0
    agent_name: str
    support_level: str
    status: str
    reason: str


class HistoricalGapReport(BaseModel):
    strict_temporal_mode: bool = False
    gaps: list[HistoricalGap] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_errors: list[str] = Field(default_factory=list)


class UniverseDateResolutionReport(BaseModel):
    as_of_date: str
    ticker_count: int
    source: str
    snapshot_hash: str
    warnings: list[str] = Field(default_factory=list)


class UniverseResolutionReport(BaseModel):
    requested_universe_id: str
    resolved_universe_id: str
    source: str
    warnings: list[str] = Field(default_factory=list)
    dates: list[UniverseDateResolutionReport] = Field(default_factory=list)


class BacktestResult(BaseModel):
    ticker: str
    universe_id: str = ""
    candidate_count: int = 0
    rebalance_frequency: str = "monthly"
    benchmark_symbol: str = "SPY"
    started_at: str
    completed_at: str
    fidelity_mode: str = "full_loop"
    cache_policy: str = "reuse"
    shortlist_size: int = 0
    top_n_holdings: int = 0
    portfolio_construction: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    benchmark_metrics: dict = Field(default_factory=dict)
    equity_curve: list[EquityPoint] = Field(default_factory=list)
    trades: list[dict] = Field(default_factory=list)
    signal_trace: list[AgentSignal] = Field(default_factory=list)
    debates: list[dict] = Field(default_factory=list)
    artifact: BacktestArtifact
    execution_snapshot: ExecutionSnapshot | None = None
    execution_snapshots: list[ExecutionSnapshot] = Field(default_factory=list)
    comparison_runs: list[TeamBacktestRun] = Field(default_factory=list)
    team_runs: list[TeamBacktestRun] = Field(default_factory=list)
    decision_events: list[DecisionEvent] = Field(default_factory=list)
    historical_gap_report: HistoricalGapReport = Field(default_factory=HistoricalGapReport)
    universe_resolution_report: UniverseResolutionReport
    team_equivalence_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
