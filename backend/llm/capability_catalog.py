from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings as env_settings
from backend.models.agent_team import CapabilityBinding, CapabilityGap
from backend.settings.user_settings import UserSettings


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    label: str
    description: str
    source_ids: tuple[str, ...]
    strict_backtest_supported: bool
    supported_modes: tuple[str, ...]


CAPABILITIES_BY_AGENT: dict[str, tuple[CapabilityDescriptor, ...]] = {
    "fundamentals": (
        CapabilityDescriptor(
            capability_id="financial_statements",
            label="Financial Statements",
            description="Income statement, balance sheet, and cash flow snapshots.",
            source_ids=("yfinance", "edgar"),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="earnings_execution_history",
            label="Earnings Execution History",
            description="Historical earnings surprises and analyst consensus context.",
            source_ids=("fmp",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="filing_text_context",
            label="Filing Text Context",
            description="Latest 10-K and 10-Q filing text grounded from EDGAR.",
            source_ids=("edgar",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
    ),
    "technicals": (
        CapabilityDescriptor(
            capability_id="ohlcv_indicators",
            label="OHLCV Indicators",
            description="Historical OHLCV with TA-derived indicators like RSI, MACD, and moving averages.",
            source_ids=("yfinance",),
            strict_backtest_supported=True,
            supported_modes=("analyze", "paper", "live", "backtest_strict", "backtest_experimental"),
        ),
    ),
    "sentiment": (
        CapabilityDescriptor(
            capability_id="headline_news_sentiment",
            label="Headline News Sentiment",
            description="Recent headline sentiment and company-news snapshots.",
            source_ids=("finnhub", "marketaux"),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="social_mention_velocity",
            label="Social Mention Velocity",
            description="Reddit mention counts and related crowd positioning proxies.",
            source_ids=("reddit",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="options_fear_gauge",
            label="Options Fear Gauge",
            description="Put-call ratio and options positioning proxies from current chains.",
            source_ids=("yfinance",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
    ),
    "macro": (
        CapabilityDescriptor(
            capability_id="rates_curve_regime",
            label="Rates And Curve Regime",
            description="Policy rate, 2y/10y yields, and curve-spread regime context.",
            source_ids=("fred",),
            strict_backtest_supported=True,
            supported_modes=("analyze", "paper", "live", "backtest_strict", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="inflation_growth_regime",
            label="Inflation And Growth Regime",
            description="CPI, PCE, GDP, and unemployment regime context.",
            source_ids=("fred",),
            strict_backtest_supported=True,
            supported_modes=("analyze", "paper", "live", "backtest_strict", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="risk_proxy_prices",
            label="Risk Proxy Prices",
            description="VIX, SPY, TLT, and GLD proxy series for macro risk context.",
            source_ids=("yfinance",),
            strict_backtest_supported=True,
            supported_modes=("analyze", "paper", "live", "backtest_strict", "backtest_experimental"),
        ),
    ),
    "value": (
        CapabilityDescriptor(
            capability_id="valuation_ratios",
            label="Valuation Ratios",
            description="P/E, forward P/E, P/B, EV/Revenue, FCF yield, and dividend metrics.",
            source_ids=("yfinance",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="management_discussion_text",
            label="Management Discussion Text",
            description="Sanitized MD&A and related filing narrative.",
            source_ids=("edgar",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
    ),
    "momentum": (
        CapabilityDescriptor(
            capability_id="relative_strength_windows",
            label="Relative Strength Windows",
            description="3m, 6m, and 12m relative return and range-position data.",
            source_ids=("yfinance",),
            strict_backtest_supported=True,
            supported_modes=("analyze", "paper", "live", "backtest_strict", "backtest_experimental"),
        ),
    ),
    "growth": (
        CapabilityDescriptor(
            capability_id="growth_trend_metrics",
            label="Growth Trend Metrics",
            description="Revenue growth, earnings growth, and margin trend metrics.",
            source_ids=("yfinance", "fmp"),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
        CapabilityDescriptor(
            capability_id="surprise_history",
            label="Surprise History",
            description="Beat, miss, and execution-consistency history.",
            source_ids=("fmp",),
            strict_backtest_supported=False,
            supported_modes=("analyze", "paper", "live", "backtest_experimental"),
        ),
    ),
}


def _source_configured(source_id: str, settings: UserSettings) -> bool:
    return {
        "yfinance": settings.data_sources.use_yfinance,
        "fred": settings.data_sources.use_fred,
        "edgar": settings.data_sources.use_edgar,
        "coingecko": settings.data_sources.use_coingecko,
        "finnhub": settings.data_sources.use_finnhub and bool(env_settings.finnhub_api_key),
        "marketaux": settings.data_sources.use_marketaux and bool(env_settings.marketaux_api_key),
        "fmp": settings.data_sources.use_fmp and bool(env_settings.fmp_api_key),
        "reddit": (
            settings.data_sources.use_reddit
            and bool(env_settings.reddit_client_id)
            and bool(env_settings.reddit_client_secret)
            and bool(env_settings.reddit_user_agent)
        ),
        "alpaca_data": settings.data_sources.use_alpaca_data and env_settings.has_alpaca(),
        "polygon": settings.data_sources.use_polygon and bool(env_settings.polygon_api_key),
    }.get(source_id, False)


def bindings_for_agent(agent_name: str, settings: UserSettings) -> list[CapabilityBinding]:
    bindings: list[CapabilityBinding] = []
    for descriptor in CAPABILITIES_BY_AGENT.get(agent_name, ()):
        configured = any(_source_configured(source_id, settings) for source_id in descriptor.source_ids)
        bindings.append(
            CapabilityBinding(
                capability_id=descriptor.capability_id,
                label=descriptor.label,
                description=descriptor.description,
                source_ids=list(descriptor.source_ids),
                configured=configured,
                strict_backtest_supported=descriptor.strict_backtest_supported,
                supported_modes=list(descriptor.supported_modes),
                detail=(
                    "Ready with current settings."
                    if configured
                    else "This role can be approximated now, but richer grounding needs one of the listed sources."
                ),
            )
        )
    return bindings


def build_capability_catalog(settings: UserSettings) -> dict[str, list[dict[str, object]]]:
    return {
        agent_name: [binding.model_dump(mode="json") for binding in bindings_for_agent(agent_name, settings)]
        for agent_name in sorted(CAPABILITIES_BY_AGENT)
    }


def build_capability_gaps(agent_name: str, settings: UserSettings) -> list[CapabilityGap]:
    gaps: list[CapabilityGap] = []
    for binding in bindings_for_agent(agent_name, settings):
        if binding.configured:
            continue
        status = "available_but_disabled"
        if all(source_id in {"finnhub", "marketaux", "fmp", "reddit", "polygon", "alpaca_data"} for source_id in binding.source_ids):
            status = "missing_key"
        gaps.append(
            CapabilityGap(
                capability_id=binding.capability_id,
                label=binding.label,
                detail=(
                    f"{binding.label} is not fully configured. The architect can still design a degraded role "
                    "with current data, or the user can enable one of the listed sources for fuller coverage."
                ),
                source_ids=binding.source_ids,
                status=status,
                can_proceed_degraded=True,
                recommended_action="Use the current data mix now, or enable one of the missing sources in Settings.",
            )
        )
    return gaps
