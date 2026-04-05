from __future__ import annotations

from pydantic import BaseModel, Field


class Order(BaseModel):
    id: str
    ticker: str
    action: str
    quantity: float = Field(gt=0)
    notional_usd: float = Field(gt=0)
    mode: str = "paper"
    status: str = "proposed"
    reasoning: str = ""
    submitted_at: str | None = None
    filled_at: str | None = None
    fill_price: float | None = None
    filled_quantity: float | None = None
    fees: float = 0.0
    broker_order_id: str | None = None
    broker_status: str | None = None
    team_id: str | None = None
    execution_snapshot_id: str | None = None


class Fill(BaseModel):
    order_id: str
    filled_at: str
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    fees: float = 0.0


class Position(BaseModel):
    ticker: str
    quantity: float
    average_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    sector: str = "unknown"


class Portfolio(BaseModel):
    cash: float
    total_value: float
    daily_pnl: float
    positions: list[Position]
    history: list[dict] = []
