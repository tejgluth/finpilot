from __future__ import annotations

import secrets as _secrets
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Startup configuration from .env. Runtime config is persisted separately."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    ai_provider: str = "openai"
    ai_model: str = ""
    llm_temperature: float = 0.2
    llm_temperature_strategy_chat: float = 0.7
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_mode: Literal["paper", "live"] = "paper"
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_live_base_url: str = "https://api.alpaca.markets"
    alpaca_data_base_url: str = "https://data.alpaca.markets"

    finnhub_api_key: str = ""
    marketaux_api_key: str = ""
    fmp_api_key: str = ""
    fred_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "finpilot:v0.1"
    polygon_api_key: str = ""

    backend_port: int = 8000
    frontend_port: int = 5173
    db_path: Path = Path("./data/finpilot.db")
    cache_dir: Path = Path("./data/cache")
    artifacts_dir: Path = Path("./data/artifacts")
    audit_log_path: Path = Path("./data/audit.log")
    llm_max_cost_per_session_usd: float = 1.00
    llm_max_tokens_per_request: int = 4000
    cache_ttl_prices_minutes: int = 60
    cache_ttl_fundamentals_minutes: int = 1440
    cache_ttl_news_minutes: int = 30
    cache_ttl_macro_minutes: int = 360
    paper_trading_minimum_days: int = 14
    secret_key: str = ""
    debug_logging: bool = False

    @field_validator("secret_key", mode="before")
    @classmethod
    def auto_secret(cls, value: str) -> str:
        return value if value else _secrets.token_hex(32)

    def has_ai_provider(self) -> bool:
        if self.ai_provider == "ollama":
            return True
        provider_keys = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "google": self.google_api_key,
        }
        return bool(provider_keys.get(self.ai_provider, ""))

    def has_alpaca(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    def mask(self, key: str) -> str:
        if not key or len(key) < 8:
            return "***"
        return key[:4] + "***" + key[-2:]

    def available_data_sources(self) -> list[str]:
        sources = ["yfinance", "fred", "edgar", "coingecko"]
        if self.finnhub_api_key:
            sources.append("finnhub")
        if self.marketaux_api_key:
            sources.append("marketaux")
        if self.fmp_api_key:
            sources.append("fmp")
        if self.reddit_client_id and self.reddit_client_secret:
            sources.append("reddit")
        if self.has_alpaca():
            sources.append("alpaca_data")
        if self.polygon_api_key:
            sources.append("polygon")
        return sources


settings = Settings()


def reload_settings() -> Settings:
    """Refresh the singleton in place so existing imports continue to work."""

    refreshed = Settings()
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(refreshed, field_name))
    return settings
