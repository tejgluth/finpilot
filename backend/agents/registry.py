from __future__ import annotations

from backend.models.agent_team import (
    REQUIRED_DECISION_AGENTS,
    VALID_ANALYSIS_AGENTS,
    VALID_SECTORS,
    VALID_TEAM_AGENTS,
)

AGENT_DESCRIPTIONS: dict[str, str] = {
    "fundamentals": (
        "Analyzes company financial health using SEC CompanyFacts, SEC EDGAR, yfinance, and FMP with grounded, "
        "field-cited reasoning."
    ),
    "technicals": (
        "Interprets pre-computed technical indicators calculated from yfinance OHLCV data."
    ),
    "sentiment": (
        "Synthesizes sanitized headline archives, Reddit mention trends, and options fear gauges from approved "
        "sentiment sources only."
    ),
    "macro": (
        "Evaluates rates, inflation, labor, and market regime proxies using FRED and yfinance."
    ),
    "value": (
        "Applies a value investing lens to fetched valuation ratios, SEC CompanyFacts history, and sanitized filing context."
    ),
    "momentum": (
        "Measures price leadership, trend persistence, and relative strength versus SPY."
    ),
    "growth": (
        "Assesses revenue growth, earnings growth, and surprise history with grounded evidence."
    ),
    "risk_manager": (
        "Deterministic position sizing, confidence threshold enforcement, and circuit breaker logic."
    ),
    "portfolio_manager": (
        "Aggregates weighted analysis signals, bull/bear debate context, and risk notes into the "
        "final BUY/SELL/HOLD decision."
    ),
}

AGENT_DATA_DEPS: dict[str, list[str]] = {
    "fundamentals": ["sec_companyfacts", "edgar", "yfinance", "fmp"],
    "technicals": ["yfinance"],
    "sentiment": ["finnhub", "marketaux", "gdelt", "reddit", "yfinance"],
    "macro": ["fred", "yfinance"],
    "value": ["sec_companyfacts", "edgar", "yfinance"],
    "momentum": ["yfinance"],
    "growth": ["sec_companyfacts", "yfinance", "fmp"],
    "risk_manager": [],
    "portfolio_manager": [],
}

ANALYSIS_FACTOR_MAP: dict[str, list[str]] = {
    "quality": ["fundamentals", "value", "growth"],
    "value": ["fundamentals", "value"],
    "growth": ["growth", "fundamentals", "momentum"],
    "momentum": ["technicals", "momentum"],
    "sentiment": ["sentiment"],
    "macro": ["macro"],
    "income": ["value", "fundamentals"],
    "defensive": ["macro", "fundamentals", "value"],
}

STYLE_TAGS: dict[str, dict[str, str]] = {
    "buffett": {"fundamentals": "buffett_moat", "value": "buffett_quality_value"},
    "graham": {"fundamentals": "graham_deep_value", "value": "graham_margin_of_safety"},
    "lynch": {"fundamentals": "lynch_garp", "growth": "lynch_garp"},
    "oneil": {"technicals": "oneil_breakout", "momentum": "oneil_leader_tracking"},
    "minervini": {"technicals": "minervini_trend_template", "momentum": "minervini_breakout_quality"},
    "dalio": {"macro": "dalio_all_weather"},
    "marks": {"macro": "marks_cycle_watch", "value": "balance_sheet_discipline"},
    "druckenmiller": {"macro": "risk_on_risk_off", "momentum": "druckenmiller_conviction_trend"},
    "contrarian": {"sentiment": "contrarian_reset", "value": "graham_margin_of_safety"},
    "dividend": {"value": "dividend_steward"},
}

REGISTERED_AGENT_NAMES: set[str] = set(VALID_TEAM_AGENTS)
SECTOR_NAMES: list[str] = sorted(VALID_SECTORS)
EXECUTABLE_ANALYSIS_AGENTS: set[str] = set(VALID_ANALYSIS_AGENTS)
REQUIRED_AGENTS: set[str] = set(REQUIRED_DECISION_AGENTS)
