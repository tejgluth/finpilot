from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.data.adapters import YFinanceAdapter
from backend.settings.user_settings import DataSourceSettings


class MomentumAgent(BaseAnalysisAgent):
    agent_name = "momentum"
    EXPECTED_FIELDS = [
        "returns_12m",
        "returns_6m",
        "returns_3m",
        "relative_strength_vs_spy_12m",
        "relative_strength_vs_spy_6m",
        "relative_strength_vs_spy_3m",
        "position_in_52w_range",
        "volume_trend",
    ]

    async def fetch_data(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        compiled_spec: CompiledAgentSpec,
        execution_snapshot: ExecutionSnapshot,
    ) -> FetchedData:
        data = FetchedData(ticker=ticker.upper())
        if not data_settings.use_yfinance or "yfinance" not in set(compiled_spec.owned_sources):
            data.failed_sources.append("yfinance")
            return data
        snapshot = await YFinanceAdapter().get_momentum_snapshot(
            ticker,
            as_of_datetime=execution_snapshot.data_boundary.as_of_datetime,
        )
        for field_name, value in snapshot.items():
            data.fields[field_name] = value
            data.field_sources[field_name] = "yfinance"
            data.field_ages[field_name] = 30.0
        return data

    def build_system_prompt(self) -> str:
        return "Assess trend quality and relative strength from fetched return data only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        relative = float(data.fields.get("relative_strength_vs_spy_12m") or 0)
        relative_6m = float(data.fields.get("relative_strength_vs_spy_6m") or 0)
        relative_3m = float(data.fields.get("relative_strength_vs_spy_3m") or 0)
        range_pos = float(data.fields.get("position_in_52w_range") or 0.5)
        volume_trend = float(data.fields.get("volume_trend") or 0)
        if variant == "oneil_leader_tracking":
            if relative_6m > 0.06 and relative_3m > 0.03 and range_pos > 0.7:
                return "BUY", 0.71, "Market leadership and near-range strength fit a leader-tracking momentum read."
        if variant == "minervini_breakout_quality":
            if relative > 0.08 and range_pos > 0.75 and volume_trend > 0:
                return "BUY", 0.72, "High-quality leadership with healthy participation fits the breakout-quality lens."
        if variant == "druckenmiller_conviction_trend":
            if relative > 0.1 and volume_trend > 0.1:
                return "BUY", 0.73, "Strong relative leadership with participation supports a conviction-trend posture."
        if relative > 0.08 and range_pos > 0.7:
            return "BUY", 0.66, "Relative strength and range position indicate durable momentum."
        if relative < -0.08 and range_pos < 0.35:
            return "SELL", 0.64, "Persistent underperformance and weak range position weigh on momentum."
        return "HOLD", 0.52, "Momentum is present but not decisive."
