"""
Runtime user settings persisted in SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from backend.config import settings as env_settings

@dataclass
class LlmSettings:
    provider: str = "openai"
    model: str = ""
    temperature_analysis: float = 0.2
    temperature_strategy: float = 0.7
    max_tokens_per_request: int = 4000
    max_cost_per_session_usd: float = 1.00
    show_token_usage_in_ui: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"


@dataclass
class DataSourceSettings:
    use_yfinance: bool = True
    use_fred: bool = True
    use_edgar: bool = True
    use_coingecko: bool = True
    use_finnhub: bool = False
    use_marketaux: bool = False
    use_fmp: bool = False
    use_reddit: bool = False
    use_alpaca_data: bool = False
    use_polygon: bool = False
    cache_ttl_prices: int = 60
    cache_ttl_fundamentals: int = 1440
    cache_ttl_news: int = 30
    cache_ttl_macro: int = 360
    max_data_age_minutes: int = 60
    min_data_coverage_pct: float = 0.5
    alpaca_plan_override: str = "auto"


@dataclass
class AgentSettings:
    enable_fundamentals: bool = True
    enable_technicals: bool = True
    enable_sentiment: bool = True
    enable_macro: bool = True
    enable_value: bool = True
    enable_momentum: bool = True
    enable_growth: bool = True
    enable_bull_bear_debate: bool = True
    default_weight_fundamentals: int = 80
    default_weight_technicals: int = 60
    default_weight_sentiment: int = 40
    default_weight_macro: int = 70
    default_weight_value: int = 75
    default_weight_momentum: int = 55
    default_weight_growth: int = 65
    min_confidence_threshold: float = 0.55
    reddit_lookback_hours: int = 48
    news_lookback_days: int = 7


@dataclass
class BacktestSettings:
    default_initial_cash: float = 100_000.0
    default_slippage_pct: float = 0.10
    default_commission_pct: float = 0.00
    default_max_position_pct: float = 12.0
    default_min_position_pct: float = 2.0
    default_cash_floor_pct: float = 5.0
    default_max_gross_exposure_pct: float = 100.0
    default_lookback_years: int = 3
    default_universe_id: str = "current_sp500"
    default_min_price: float = 5.0
    default_min_avg_dollar_volume_millions: float = 25.0
    default_liquidity_lookback_days: int = 30
    default_min_history_days: int = 252
    default_fidelity_mode: str = "full_loop"
    default_cache_policy: str = "reuse"
    default_candidate_pool_size: int = 60
    default_shortlist_size: int = 60
    default_top_n_holdings: int = 10
    default_min_conviction_score: float = 0.18
    default_weighting_mode: str = "capped_conviction"
    default_score_normalization_mode: str = "power"
    default_score_exponent: float = 1.6
    default_risk_adjustment_mode: str = "mild_inverse_vol"
    default_selection_buffer_pct: float = 0.50
    default_replacement_threshold: float = 0.06
    default_hold_zone_pct: float = 1.0
    default_turnover_buffer_pct: float = 0.35
    default_max_turnover_pct: float = 25.0
    default_sector_cap_pct: float = 35.0
    default_persistence_bonus: float = 0.03
    max_parallel_historical_evaluations: int = 4
    max_cost_per_backtest_usd: float = 5.0
    max_tokens_per_backtest: int = 120_000
    walk_forward_enabled: bool = False
    walk_forward_window_months: int = 3
    show_transaction_costs_separately: bool = True


@dataclass
class GuardrailConfig:
    max_position_pct: float = 5.0
    max_sector_pct: float = 30.0
    max_open_positions: int = 10
    max_daily_loss_pct: float = 3.0
    max_weekly_drawdown_pct: float = 7.0
    max_total_drawdown_pct: float = 20.0
    auto_confirm_max_usd: float = 100.0
    max_trades_per_day: int = 5
    trading_hours_only: bool = True
    max_data_age_minutes: int = 60
    kill_switch_active: bool = False
    SYSTEM_MAX_POSITION_PCT: float = field(default=20.0, init=False, repr=False)
    SYSTEM_MAX_SECTOR_PCT: float = field(default=50.0, init=False, repr=False)
    SYSTEM_MAX_DAILY_LOSS_PCT: float = field(default=10.0, init=False, repr=False)
    SYSTEM_MAX_TOTAL_DRAWDOWN_PCT: float = field(default=30.0, init=False, repr=False)
    SYSTEM_MAX_TRADES_PER_DAY: int = field(default=20, init=False, repr=False)

    def clamp(self) -> "GuardrailConfig":
        self.max_position_pct = min(self.max_position_pct, self.SYSTEM_MAX_POSITION_PCT)
        self.max_sector_pct = min(self.max_sector_pct, self.SYSTEM_MAX_SECTOR_PCT)
        self.max_daily_loss_pct = min(self.max_daily_loss_pct, self.SYSTEM_MAX_DAILY_LOSS_PCT)
        self.max_total_drawdown_pct = min(self.max_total_drawdown_pct, self.SYSTEM_MAX_TOTAL_DRAWDOWN_PCT)
        self.max_trades_per_day = min(self.max_trades_per_day, self.SYSTEM_MAX_TRADES_PER_DAY)
        return self


@dataclass
class NotificationSettings:
    browser_notifications: bool = True
    notify_trade_executed: bool = True
    notify_circuit_breaker: bool = True
    notify_daily_summary: bool = True
    notify_paper_milestone: bool = True
    email_enabled: bool = False
    email_address: str = ""
    slack_enabled: bool = False
    slack_webhook_url: str = ""


@dataclass
class SystemSettings:
    backend_port: int = 8000
    frontend_port: int = 5173
    db_path: str = "./data/finpilot.db"
    cache_dir: str = "./data/cache"
    artifacts_dir: str = "./data/artifacts"
    audit_log_path: str = "./data/audit.log"
    debug_logging: bool = False
    paper_trading_minimum_days: int = 14


@dataclass
class UserSettings:
    llm: LlmSettings = field(default_factory=LlmSettings)
    data_sources: DataSourceSettings = field(default_factory=DataSourceSettings)
    agents: AgentSettings = field(default_factory=AgentSettings)
    backtest: BacktestSettings = field(default_factory=BacktestSettings)
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    system: SystemSettings = field(default_factory=SystemSettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm": _serialize_dataclass(self.llm),
            "data_sources": _serialize_dataclass(self.data_sources),
            "agents": _serialize_dataclass(self.agents),
            "backtest": _serialize_dataclass(self.backtest),
            "guardrails": _serialize_dataclass(self.guardrails),
            "notifications": _serialize_dataclass(self.notifications),
            "system": _serialize_dataclass(self.system),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "UserSettings":
        raw = raw or {}
        return cls(
            llm=_coerce_dataclass(LlmSettings, raw.get("llm")),
            data_sources=_coerce_dataclass(DataSourceSettings, raw.get("data_sources")),
            agents=_coerce_dataclass(AgentSettings, raw.get("agents")),
            backtest=_coerce_dataclass(BacktestSettings, raw.get("backtest")),
            guardrails=_coerce_dataclass(GuardrailConfig, raw.get("guardrails")).clamp(),
            notifications=_coerce_dataclass(NotificationSettings, raw.get("notifications")),
            system=_coerce_dataclass(SystemSettings, raw.get("system")),
        )

    def apply_patch(self, patch: dict[str, Any]) -> "UserSettings":
        merged = self.to_dict()
        for section, values in patch.items():
            if isinstance(values, dict) and section in merged:
                merged[section].update(values)
            else:
                merged[section] = values
        return self.from_dict(merged)


def default_user_settings() -> UserSettings:
    return UserSettings.from_dict(
        {
            "llm": {
                "provider": env_settings.ai_provider,
                "model": env_settings.ai_model,
                "temperature_analysis": env_settings.llm_temperature,
                "temperature_strategy": env_settings.llm_temperature_strategy_chat,
                "max_tokens_per_request": env_settings.llm_max_tokens_per_request,
                "max_cost_per_session_usd": env_settings.llm_max_cost_per_session_usd,
                "ollama_base_url": env_settings.ollama_base_url,
                "ollama_model": env_settings.ollama_model,
            },
            "data_sources": {
                "use_finnhub": bool(env_settings.finnhub_api_key),
                "use_marketaux": bool(env_settings.marketaux_api_key),
                "use_fmp": bool(env_settings.fmp_api_key),
                "use_reddit": bool(env_settings.reddit_client_id and env_settings.reddit_client_secret),
                "use_alpaca_data": env_settings.has_alpaca(),
                "use_polygon": bool(env_settings.polygon_api_key),
                "cache_ttl_prices": env_settings.cache_ttl_prices_minutes,
                "cache_ttl_fundamentals": env_settings.cache_ttl_fundamentals_minutes,
                "cache_ttl_news": env_settings.cache_ttl_news_minutes,
                "cache_ttl_macro": env_settings.cache_ttl_macro_minutes,
            },
            "system": {
                "backend_port": env_settings.backend_port,
                "frontend_port": env_settings.frontend_port,
                "db_path": str(env_settings.db_path),
                "cache_dir": str(env_settings.cache_dir),
                "artifacts_dir": str(env_settings.artifacts_dir),
                "audit_log_path": str(env_settings.audit_log_path),
                "debug_logging": env_settings.debug_logging,
                "paper_trading_minimum_days": env_settings.paper_trading_minimum_days,
            },
        }
    )


def _coerce_dataclass(cls: type[Any], raw: dict[str, Any] | None) -> Any:
    allowed = {field.name for field in fields(cls) if field.init}
    filtered = {key: value for key, value in (raw or {}).items() if key in allowed}
    return cls(**filtered)


def _serialize_dataclass(instance: Any) -> dict[str, Any]:
    return {
        field.name: getattr(instance, field.name)
        for field in fields(instance)
        if field.init
    }
