from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.data.adapters import EdgarAdapter, YFinanceAdapter
from backend.security.input_sanitizer import ContentSource, sanitize
from backend.settings.user_settings import DataSourceSettings


class ValueAgent(BaseAnalysisAgent):
    agent_name = "value"
    EXPECTED_FIELDS = [
        "pe_ratio",
        "forward_pe",
        "pb_ratio",
        "ev_revenue",
        "fcf_yield",
        "dividend_yield",
        "dividend_growth_years",
        "buyback_ratio",
        "mda_excerpt",
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
            snapshot = await YFinanceAdapter().get_fundamentals(
                ticker,
                as_of_datetime=as_of,
                point_in_time_required=point_in_time_required,
            )
            snapshot.update(
                await YFinanceAdapter().get_value_snapshot(
                    ticker,
                    as_of_datetime=as_of,
                    point_in_time_required=point_in_time_required,
                )
            )
            for field_name in (
                "pe_ratio",
                "forward_pe",
                "pb_ratio",
                "ev_revenue",
                "fcf_yield",
                "dividend_yield",
                "dividend_growth_years",
                "buyback_ratio",
            ):
                data.fields[field_name] = snapshot.get(field_name)
                data.field_sources[field_name] = "yfinance"
                data.field_ages[field_name] = 45.0
        else:
            data.failed_sources.append("yfinance")

        if data_settings.use_edgar and "edgar" in allowed_sources:
            try:
                filing = await EdgarAdapter().get_latest_filing_sections(ticker, as_of_datetime=as_of)
            except Exception:
                data.failed_sources.append("edgar")
            else:
                if filing.get("mda_section"):
                    excerpt = sanitize(filing["mda_section"], ContentSource.SEC_FILING)
                    data.fields["mda_excerpt"] = excerpt.sanitized_text
                    data.field_sources["mda_excerpt"] = "edgar"
                    data.field_ages["mda_excerpt"] = 1440.0
        else:
            data.failed_sources.append("edgar")
        return data

    def build_system_prompt(self) -> str:
        return "Apply a value investing lens to valuation ratios and sanitized management commentary only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        pe = float(data.fields.get("pe_ratio") or 0)
        pb = float(data.fields.get("pb_ratio") or 0)
        fcf = float(data.fields.get("fcf_yield") or 0)
        dividend = float(data.fields.get("dividend_yield") or 0)
        dividend_growth_years = float(data.fields.get("dividend_growth_years") or 0)
        buyback = float(data.fields.get("buyback_ratio") or 0)
        if variant == "graham_margin_of_safety":
            if pe < 15 and pb < 1.8 and fcf > 0.04:
                return "BUY", 0.73, "Low valuation and cash yield provide a margin-of-safety style setup."
        if variant == "buffett_quality_value":
            if pe < 24 and fcf > 0.05 and buyback > 0.01:
                return "BUY", 0.71, "Fair valuation plus durable cash generation fits a quality-value lens."
        if variant == "dividend_steward":
            if dividend > 0.02 and dividend_growth_years >= 5:
                return "BUY", 0.7, "Income durability and dividend growth support the dividend stewardship read."
        if pe and pe < 18 and fcf > 0.05:
            return "BUY", 0.67, "Valuation and free cash flow yield look supportive for a value thesis."
        if pe > 30 and dividend < 0.01:
            return "SELL", 0.6, "Valuation is stretched without much cash yield support."
        return "HOLD", 0.53, "Value evidence is balanced."
