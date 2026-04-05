from __future__ import annotations

from pydantic import BaseModel, Field


class RiskSettings(BaseModel):
    max_position_pct: float = Field(default=5.0, ge=0.0, le=20.0)
    max_sector_pct: float = Field(default=30.0, ge=0.0, le=50.0)
    max_open_positions: int = Field(default=10, ge=1, le=50)
    max_daily_loss_pct: float = Field(default=3.0, ge=0.0, le=10.0)
    max_total_drawdown_pct: float = Field(default=20.0, ge=0.0, le=30.0)
    max_trades_per_day: int = Field(default=5, ge=1, le=100)
    auto_confirm_max_usd: float = Field(default=100.0, ge=0.0)
    trading_hours_only: bool = True
    max_data_age_minutes: int = Field(default=60, ge=1, le=1440)
