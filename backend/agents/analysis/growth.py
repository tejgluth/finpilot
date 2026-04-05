from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.data.adapters import FmpAdapter, YFinanceAdapter
from backend.settings.user_settings import DataSourceSettings


class GrowthAgent(BaseAnalysisAgent):
    agent_name = "growth"
    EXPECTED_FIELDS = [
        "revenue_growth_q1",
        "revenue_growth_q2",
        "revenue_growth_q3",
        "revenue_growth_q4",
        "earnings_growth_last4q",
        "gross_margin_trend",
        "beat_rate",
    ]

    async def fetch_data(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        compiled_spec: CompiledAgentSpec,
        execution_snapshot: ExecutionSnapshot,
    ) -> FetchedData:
        data = FetchedData(ticker=ticker.upper())
        as_of = execution_snapshot.data_boundary.as_of_datetime
        point_in_time_required = execution_snapshot.strict_temporal_mode
        allowed_sources = set(compiled_spec.owned_sources)
        if data_settings.use_yfinance and "yfinance" in allowed_sources:
            snapshot = await YFinanceAdapter().get_growth_snapshot(
                ticker,
                as_of_datetime=as_of,
                point_in_time_required=point_in_time_required,
            )
            for field_name, value in snapshot.items():
                data.fields[field_name] = value
                data.field_sources[field_name] = "yfinance"
                data.field_ages[field_name] = 60.0
        else:
            data.failed_sources.append("yfinance")

        if data_settings.use_fmp and "fmp" in allowed_sources:
            earnings = await FmpAdapter().get_earnings_snapshot(ticker, as_of_datetime=as_of)
            if earnings.get("beat_rate") is not None:
                data.fields["beat_rate"] = earnings["beat_rate"]
                data.field_sources["beat_rate"] = "fmp"
                data.field_ages["beat_rate"] = 180.0
        else:
            data.failed_sources.append("fmp")
        return data

    def build_system_prompt(self) -> str:
        return "Assess growth quality using fetched revenue growth, earnings growth, and surprise data only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        growth = float(data.fields.get("earnings_growth_last4q") or 0)
        beat_rate = float(data.fields.get("beat_rate") or 0)
        margin_trend = float(data.fields.get("gross_margin_trend") or 0)
        revenue_avg = sum(float(data.fields.get(field) or 0) for field in self.EXPECTED_FIELDS[:4]) / 4
        if variant == "fisher_quality_growth":
            if revenue_avg > 0.12 and margin_trend > 0 and growth > 0.1:
                return "BUY", 0.72, "Revenue and margin quality support a quality-growth read."
        if variant == "earnings_revision":
            if beat_rate >= 0.625 and growth > 0.08:
                return "BUY", 0.71, "Repeated beats and earnings follow-through support the revision lens."
        if variant == "quality_compounder":
            if revenue_avg > 0.08 and margin_trend >= 0:
                return "BUY", 0.68, "Steady compounding growth quality looks constructive."
        if growth > 0.12 and beat_rate >= 0.5 and margin_trend >= 0:
            return "BUY", 0.68, "Growth and execution are trending in the right direction."
        if growth < -0.05 and beat_rate < 0.4:
            return "SELL", 0.63, "Growth deceleration and weak earnings execution hurt the case."
        return "HOLD", 0.55, "Growth signals are mixed."
