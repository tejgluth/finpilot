export type PermissionLevel = "full_manual" | "semi_auto" | "full_auto";
export type StrategyConversationStatus = "collecting_requirements" | "draft_ready" | "finalized";
export type StrategyMessageRole = "user" | "assistant" | "system";
export type StrategyMessageType = "input" | "follow_up" | "summary" | "draft" | "final";
export type BacktestMode = "backtest_strict" | "backtest_experimental";
export type DataBoundaryMode = "live" | "paper" | "backtest_strict" | "backtest_experimental";

export interface LlmSettings {
  provider: string;
  model: string;
  temperature_analysis: number;
  temperature_strategy: number;
  max_tokens_per_request: number;
  max_cost_per_session_usd: number;
  show_token_usage_in_ui: boolean;
  ollama_base_url: string;
  ollama_model: string;
}

export interface DataSourceSettings {
  use_yfinance: boolean;
  use_fred: boolean;
  use_edgar: boolean;
  use_coingecko: boolean;
  use_finnhub: boolean;
  use_marketaux: boolean;
  use_fmp: boolean;
  use_reddit: boolean;
  use_alpaca_data: boolean;
  use_polygon: boolean;
  cache_ttl_prices: number;
  cache_ttl_fundamentals: number;
  cache_ttl_news: number;
  cache_ttl_macro: number;
  max_data_age_minutes: number;
  min_data_coverage_pct: number;
  alpaca_plan_override: string;
}

export interface AgentSettings {
  enable_fundamentals: boolean;
  enable_technicals: boolean;
  enable_sentiment: boolean;
  enable_macro: boolean;
  enable_value: boolean;
  enable_momentum: boolean;
  enable_growth: boolean;
  enable_bull_bear_debate: boolean;
  default_weight_fundamentals: number;
  default_weight_technicals: number;
  default_weight_sentiment: number;
  default_weight_macro: number;
  default_weight_value: number;
  default_weight_momentum: number;
  default_weight_growth: number;
  min_confidence_threshold: number;
  reddit_lookback_hours: number;
  news_lookback_days: number;
}

export interface BacktestSettings {
  default_initial_cash: number;
  default_slippage_pct: number;
  default_commission_pct: number;
  default_max_position_pct: number;
  default_lookback_years: number;
  default_fidelity_mode: "full_loop" | "hybrid_shortlist";
  default_cache_policy: "reuse" | "fresh";
  default_shortlist_size: number;
  max_parallel_historical_evaluations: number;
  max_cost_per_backtest_usd: number;
  max_tokens_per_backtest: number;
  walk_forward_enabled: boolean;
  walk_forward_window_months: number;
  show_transaction_costs_separately: boolean;
}

export interface GuardrailConfig {
  max_position_pct: number;
  max_sector_pct: number;
  max_open_positions: number;
  max_daily_loss_pct: number;
  max_weekly_drawdown_pct: number;
  max_total_drawdown_pct: number;
  auto_confirm_max_usd: number;
  max_trades_per_day: number;
  trading_hours_only: boolean;
  max_data_age_minutes: number;
  kill_switch_active: boolean;
}

export interface NotificationSettings {
  browser_notifications: boolean;
  notify_trade_executed: boolean;
  notify_circuit_breaker: boolean;
  notify_daily_summary: boolean;
  notify_paper_milestone: boolean;
  email_enabled: boolean;
  email_address: string;
  slack_enabled: boolean;
  slack_webhook_url: string;
}

export interface SystemSettings {
  backend_port: number;
  frontend_port: number;
  db_path: string;
  cache_dir: string;
  artifacts_dir: string;
  audit_log_path: string;
  debug_logging: boolean;
  paper_trading_minimum_days: number;
}

export interface UserSettings {
  llm: LlmSettings;
  data_sources: DataSourceSettings;
  agents: AgentSettings;
  backtest: BacktestSettings;
  guardrails: GuardrailConfig;
  notifications: NotificationSettings;
  system: SystemSettings;
}

export interface AgentMetadata {
  name: string;
  description: string;
  data_dependencies: string[];
}

export interface SetupStatus {
  configured_sources: string[];
  user_settings: UserSettings;
  has_alpaca: boolean;
  has_ai_provider: boolean;
  first_run?: boolean;
  ai_provider?: string;
  alpaca_mode?: string;
  env_file_present?: boolean;
}

export interface SecretKeyStatus {
  name: string;
  configured: boolean;
  masked_value: string;
  message: string;
}

export interface ProviderGuide {
  id: "openai" | "anthropic" | "google" | "ollama";
  label: string;
  env_key?: string | null;
  recommended: boolean;
  needs_api_key: boolean;
  description: string;
  helper_text: string;
  setup_url: string;
  instructions: string[];
}

export interface ServiceGuide {
  id: string;
  label: string;
  env_keys: string[];
  category: "broker" | "market_data" | "news" | "optional";
  recommended: boolean;
  required_with?: string | null;
  description: string;
  helper_text: string;
  setup_url: string;
  instructions: string[];
}

export interface SetupGuidesResponse {
  security_note: string;
  quickstart_steps: string[];
  providers: ProviderGuide[];
  services: ServiceGuide[];
}

export interface SaveSetupSecretsResponse {
  ok: boolean;
  saved_keys: string[];
  status: SetupStatus;
  keys: SecretKeyStatus[];
  message: string;
}

export interface AlpacaPlanResponse {
  plan: string;
  display_name: string;
  data_requests_per_minute: number;
  orders_per_minute: number;
  orders_per_day: number;
  supports_live_trading: boolean;
  supports_options: boolean;
  description: string;
}

export interface StrategyMessage {
  message_id: string;
  role: StrategyMessageRole;
  content: string;
  sanitized_content: string;
  timestamp: string;
  message_type: StrategyMessageType;
}

export interface StrategyPreferences {
  goal_summary: string;
  risk_level: string;
  time_horizon: string;
  asset_universe: string;
  sector_exclusions: string[];
  preferred_factors: string[];
  deemphasized_factors: string[];
  disabled_agents: string[];
  source_preferences: Record<string, string[]>;
  style_tags: string[];
  agent_modifier_preferences: Record<string, Record<string, unknown>>;
  backtest_mode_default: BacktestMode;
  comparison_target: string;
  unresolved_items: string[];
}

export interface TeamDraft {
  team_id?: string | null;
  name: string;
  description: string;
  enabled_agents: string[];
  agent_weights: Record<string, number>;
  agent_modifiers: Record<string, Record<string, unknown>>;
  risk_level: string;
  time_horizon: string;
  asset_universe: string;
  sector_exclusions: string[];
  team_overrides: Record<string, unknown>;
}

export interface StrategyDraft {
  draft_id: string;
  conversation_id: string;
  summary: string;
  team_draft: TeamDraft;
  rationale: string;
  follow_up_question: string | null;
  unresolved_items: string[];
  default_team_comparison_note: string;
}

export interface ValidationReport {
  valid: boolean;
  warnings: string[];
  normalized_fields: string[];
}

export interface CompiledAgentSpec {
  agent_name: string;
  enabled: boolean;
  weight: number;
  prompt_pack_id: string;
  prompt_pack_version: string;
  variant_id: string;
  modifiers: Record<string, unknown>;
  owned_sources: string[];
  freshness_limit_minutes: number;
  lookback_config: Record<string, number>;
}

export interface CompiledTeam {
  schema_version: string;
  team_id: string;
  version_number: number;
  name: string;
  description: string;
  enabled_agents: string[];
  agent_weights: Record<string, number>;
  compiled_agent_specs: Record<string, CompiledAgentSpec>;
  risk_level: string;
  time_horizon: string;
  asset_universe: string;
  sector_exclusions: string[];
  team_overrides: Record<string, unknown>;
  default_team_reference: string;
  compiler_version: string;
  validation_report: ValidationReport;
}

export interface TeamComparison {
  default_team_id: string;
  candidate_team_id: string;
  agent_diff: Record<string, string[]>;
  weight_diff: Record<string, { default: number; candidate: number }>;
  modifier_diff: Record<string, { default: Record<string, unknown>; candidate: Record<string, unknown> }>;
  risk_diff: Record<string, string>;
  horizon_diff: Record<string, string>;
  exclusion_diff: Record<string, string[]>;
  summary: string;
}

export interface TeamVersion {
  team_id: string;
  version_number: number;
  created_at: string;
  source_conversation_id: string | null;
  is_default: boolean;
  label: string;
  compiled_team: CompiledTeam;
  content_hash: string;
  status: "draft" | "active" | "archived";
}

export interface StrategyConversation {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  status: StrategyConversationStatus;
  messages: StrategyMessage[];
  preferences: StrategyPreferences;
  latest_draft: StrategyDraft | null;
  selected_default_comparison: string;
  final_team_version_id: string | null;
}

export interface DataBoundary {
  mode: DataBoundaryMode;
  as_of_datetime: string | null;
  market_session_reference: string;
  allow_latest_semantics: boolean;
}

export interface ExecutionSnapshot {
  snapshot_id: string;
  mode: "analyze" | "paper" | "live" | BacktestMode;
  created_at: string;
  ticker_or_universe: string;
  effective_team: CompiledTeam;
  provider: string;
  model: string;
  prompt_pack_versions: Record<string, string>;
  settings_hash: string;
  team_hash: string;
  data_boundary: DataBoundary;
  cost_model: Record<string, unknown>;
  benchmark_symbol: string;
  strict_temporal_mode: boolean;
  notes: string[];
}

export interface DataCitation {
  field_name: string;
  value: string;
  source: string;
  fetched_at: string;
}

export interface AgentSignal {
  ticker: string;
  agent_name: string;
  action: "BUY" | "SELL" | "HOLD";
  raw_confidence: number;
  final_confidence: number;
  reasoning: string;
  cited_data: DataCitation[];
  unavailable_fields: string[];
  data_coverage_pct: number;
  oldest_data_age_minutes: number;
  warning: string;
}

export interface DebateOutput {
  position: string;
  thesis: string;
  key_points: string[];
  cited_agents: string[];
  confidence: number;
}

export interface BacktestArtifact {
  artifact_id: string;
  data_hash: string;
  config_snapshot: Record<string, unknown>;
  transaction_cost_model: Record<string, unknown>;
  created_at: string;
  benchmark_symbol: string;
  artifact_path: string;
  execution_snapshot: ExecutionSnapshot;
  temporal_features: Record<string, unknown>;
}

export interface ComparisonTarget {
  team_id: string;
  version_number: number | null;
}

export interface EquityPoint {
  timestamp: string;
  strategy_equity: number;
  benchmark_equity: number;
}

export interface HistoricalAgentSupport {
  agent_name: string;
  support_level: string;
  honored_in_strict: boolean;
  degraded_in_experimental: boolean;
  effective_weight: number;
  reason: string;
  owned_sources: string[];
}

export interface HistoricalEffectiveSignature {
  team_id: string;
  team_name: string;
  version_number: number;
  honored_agents: string[];
  degraded_agents: HistoricalAgentSupport[];
  effective_weights: Record<string, number>;
  ignored_agents: string[];
  summary: string;
}

export interface CacheUsageSummary {
  hits: number;
  misses: number;
  writes: number;
}

export interface HoldingsSnapshot {
  timestamp: string;
  team_id: string;
  team_name: string;
  holdings: {
    ticker: string;
    weight_pct: number;
    score: number;
  }[];
}

export interface DecisionEvent {
  rebalance_date: string;
  execution_date: string;
  team_id: string;
  team_name: string;
  version_number: number;
  ticker: string;
  shortlist_rank: number | null;
  shortlisted: boolean;
  selected_for_execution: boolean;
  cache_status: string;
  score: number;
  target_weight_pct: number;
  signals: AgentSignal[];
  bull_case: DebateOutput | null;
  bear_case: DebateOutput | null;
  decision: {
    ticker: string;
    action: "BUY" | "SELL" | "HOLD";
    confidence: number;
    reasoning: string;
    cited_agents: string[];
    bull_points_used: string[];
    bear_points_addressed: string[];
    risk_notes: string;
    proposed_position_pct: number;
  };
  warnings: string[];
}

export interface TeamBacktestRun {
  team_id: string;
  team_name: string;
  version_number: number;
  metrics: Record<string, number>;
  equity_curve: EquityPoint[];
  trades: Record<string, unknown>[];
  turnover_pct: number;
  max_sector_concentration_pct: number;
  top_holdings_over_time: HoldingsSnapshot[];
  supported_agents: string[];
  degraded_agents: HistoricalAgentSupport[];
  excluded_agents: string[];
  notes: string[];
  warnings: string[];
  effective_signature: HistoricalEffectiveSignature | null;
  cache_usage: CacheUsageSummary;
}

export interface HistoricalGap {
  team_id: string;
  team_name: string;
  version_number: number;
  agent_name: string;
  support_level: string;
  status: string;
  reason: string;
}

export interface HistoricalGapReport {
  strict_temporal_mode: boolean;
  gaps: HistoricalGap[];
  warnings: string[];
  blocking_errors: string[];
}

export interface UniverseDateResolutionReport {
  as_of_date: string;
  ticker_count: number;
  source: string;
  snapshot_hash: string;
  warnings: string[];
}

export interface UniverseResolutionReport {
  requested_universe_id: string;
  resolved_universe_id: string;
  source: string;
  warnings: string[];
  dates: UniverseDateResolutionReport[];
}

export interface BacktestResult {
  ticker: string;
  universe_id: string;
  candidate_count: number;
  rebalance_frequency: string;
  benchmark_symbol: string;
  started_at: string;
  completed_at: string;
  fidelity_mode: "full_loop" | "hybrid_shortlist";
  cache_policy: "reuse" | "fresh";
  shortlist_size: number;
  metrics: Record<string, number>;
  benchmark_metrics: Record<string, number>;
  equity_curve: EquityPoint[];
  trades: Record<string, unknown>[];
  signal_trace: AgentSignal[];
  debates: {
    bull_case: DebateOutput | null;
    bear_case: DebateOutput | null;
    decision: Record<string, unknown>;
  }[];
  artifact: BacktestArtifact;
  execution_snapshot: ExecutionSnapshot | null;
  execution_snapshots: ExecutionSnapshot[];
  comparison_runs: TeamBacktestRun[];
  team_runs: TeamBacktestRun[];
  decision_events: DecisionEvent[];
  historical_gap_report: HistoricalGapReport;
  universe_resolution_report: UniverseResolutionReport;
  team_equivalence_warnings: string[];
  warnings: string[];
}

export interface PortfolioHistoryPoint {
  timestamp: string;
  equity: number;
  cash: number;
}

export interface PortfolioPayload {
  cash: number;
  equity: number;
  daily_pnl: number;
  history: PortfolioHistoryPoint[];
  trade_count: number;
  backtest_count: number;
  positions: {
    ticker: string;
    quantity: number;
    average_cost: number;
    market_price: number;
    market_value: number;
    unrealized_pnl: number;
    sector?: string;
  }[];
  agent_performance: {
    agent_name: string;
    accuracy_pct: number;
  }[];
}

export interface LiveUnlockGate {
  id: string;
  label: string;
  passed: boolean;
  detail: string;
}

export interface LiveUnlockPayload {
  ready: boolean;
  paper_trading_days_completed: number;
  minimum_paper_trading_days: number;
  gates: LiveUnlockGate[];
}

export interface PermissionsPayload {
  level: PermissionLevel;
  paper_trading_days_completed: number;
  live_trading_acknowledged_risks: boolean;
  live_trading_enabled: boolean;
  level_info?: Record<string, unknown>;
  live_unlock?: LiveUnlockPayload;
}

export interface TradingStatusPayload {
  alpaca_mode: string;
  permission_level: PermissionLevel;
  live_risk_acknowledged: boolean;
  live_trading_enabled: boolean;
  paper_trading_days_completed: number;
  live_unlock: LiveUnlockPayload;
  mode_notice: string;
  kill_switch: {
    active: boolean;
    reason: string;
  };
}

export interface TradeOrderPreview {
  ticker: string;
  action: string;
  notional_usd: number;
  estimated_quantity: number;
  estimated_price: number | null;
  mode: string;
  reasons: string[];
  permission_level: PermissionLevel;
}

export interface TradeOrderResponse {
  accepted: boolean;
  requires_confirmation: boolean;
  preview: TradeOrderPreview;
  order?: Record<string, unknown>;
}

export interface AuditEntry {
  timestamp: string;
  actor: string;
  event_type: string;
  [key: string]: unknown;
}

// ── Premade Team Catalog ────────────────────────────────────────────────────

export type TeamComplexity = "beginner" | "intermediate" | "advanced";

export interface PremadeTeamTemplate {
  team_id: string;
  display_name: string;
  description: string;
  target_user: string;
  suitable_for: string[];
  risk_level: string;
  time_horizon: string;
  enabled_analysis_agents: string[];
  weights: Record<string, number>;
  agent_variants: Record<string, string>;
  team_overrides: Record<string, unknown>;
  excluded_sectors: string[];
  complexity: TeamComplexity;
  is_default: boolean;
  is_featured: boolean;
  is_hidden: boolean;
  why_distinct: string;
  known_limitations: string[];
  not_for: string[];
}

export interface PremadeTeamCatalog {
  catalog_version: string;
  teams: PremadeTeamTemplate[];
  default_team_id: string;
  featured_team_ids: string[];
  hidden_team_ids: string[];
}

export interface TeamMatchExplanation {
  team_id: string;
  match_score: number;
  matched_dimensions: string[];
  unmatched_dimensions: string[];
  contradictions_detected: string[];
  explanation: string;
}

export interface TeamRecommendation {
  recommended_team_id: string | null;
  confidence: number;
  explanation: TeamMatchExplanation;
  alternatives: TeamMatchExplanation[];
  follow_up_question: string | null;
  is_premade: boolean;
  is_fallback_to_default: boolean;
  extracted_preferences_summary: string;
  error_code: string | null;
}
