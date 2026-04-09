from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.data.adapters import EdgarAdapter, FmpAdapter, SecCompanyFactsAdapter, YFinanceAdapter
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.settings.user_settings import DataSourceSettings


class FundamentalsAgent(BaseAnalysisAgent):
    agent_name = "fundamentals"
    EXPECTED_FIELDS = [
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "gross_margin",
        "operating_margin",
        "net_margin",
        "roe",
        "roa",
        "debt_to_equity",
        "current_ratio",
        "latest_10k_summary",
        "latest_10q_summary",
        "analyst_consensus_eps",
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
        historical_replay = as_of is not None
        allowed_sources = set(compiled_spec.owned_sources)
        if data_settings.use_sec_companyfacts and "sec_companyfacts" in allowed_sources:
            snapshot = await SecCompanyFactsAdapter().get_company_snapshot(ticker, as_of_datetime=as_of)
            for field_name in (
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "gross_margin",
                "operating_margin",
                "net_margin",
                "roe",
                "roa",
                "debt_to_equity",
                "current_ratio",
            ):
                if snapshot.get(field_name) is None:
                    continue
                data.fields[field_name] = snapshot[field_name]
                data.field_sources[field_name] = "sec_companyfacts"
                data.field_ages[field_name] = 1440.0
        elif historical_replay:
            data.failed_sources.append("sec_companyfacts")

        if data_settings.use_yfinance and "yfinance" in allowed_sources and not historical_replay:
            fundamentals = await YFinanceAdapter().get_fundamentals(
                ticker,
                as_of_datetime=as_of,
                point_in_time_required=False,
            )
            for field_name, value in fundamentals.items():
                data.fields[field_name] = value
                data.field_sources[field_name] = "yfinance"
                data.field_ages[field_name] = 15.0
        elif not historical_replay:
            data.failed_sources.append("yfinance")

        if data_settings.use_edgar and "edgar" in allowed_sources:
            try:
                filings = await EdgarAdapter().get_latest_filing_sections(ticker, as_of_datetime=as_of)
            except Exception:
                data.failed_sources.append("edgar")
            else:
                for field_name in ("latest_10k_summary", "latest_10q_summary"):
                    if filings.get(field_name) is not None:
                        data.fields[field_name] = filings.get(field_name)
                        data.field_sources[field_name] = "edgar"
                        data.field_ages[field_name] = 1440.0
        else:
            data.failed_sources.append("edgar")

        if data_settings.use_fmp and "fmp" in allowed_sources:
            earnings = await FmpAdapter().get_earnings_snapshot(ticker, as_of_datetime=as_of)
            if earnings.get("analyst_consensus_eps") is not None:
                data.fields["analyst_consensus_eps"] = earnings["analyst_consensus_eps"]
                data.field_sources["analyst_consensus_eps"] = "fmp"
                data.field_ages["analyst_consensus_eps"] = 180.0
            if earnings.get("beat_rate") is not None:
                data.fields["beat_rate"] = earnings["beat_rate"]
                data.field_sources["beat_rate"] = "fmp"
                data.field_ages["beat_rate"] = 180.0
        else:
            data.failed_sources.append("fmp")
        return data

    def build_system_prompt(self) -> str:
        return "Assess financial health from fetched financial statements and earnings context only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        roe = float(data.fields.get("roe") or 0)
        debt = float(data.fields.get("debt_to_equity") or 0)
        beat_rate = float(data.fields.get("beat_rate") or 0)
        pe_ratio = float(data.fields.get("pe_ratio") or 0)
        current_ratio = float(data.fields.get("current_ratio") or 0)
        pb_ratio = float(data.fields.get("pb_ratio") or 0)
        if variant == "graham_deep_value":
            if pe_ratio < 16 and pb_ratio < 2.2 and current_ratio > 1.2:
                return "BUY", 0.76, "Cheap valuation, liquidity, and downside discipline support the deep value case."
            if debt > 2.0 or current_ratio < 1.0:
                return "SELL", 0.7, "Balance-sheet protection is too weak for a Graham-style read."
        if variant == "buffett_moat":
            if roe > 0.2 and debt < 1.0 and float(data.fields.get("gross_margin") or 0) > 0.45:
                return "BUY", 0.78, "High returns, resilient margins, and debt discipline fit the moat-compounder lens."
            if roe < 0.1 and debt > 1.8:
                return "SELL", 0.68, "Capital efficiency and balance-sheet discipline are too weak for a moat lens."
        if variant == "lynch_garp":
            if beat_rate >= 0.5 and roe > 0.15 and pe_ratio < 24:
                return "BUY", 0.72, "Reasonable valuation with steady execution fits a pragmatic growth-at-a-fair-price read."
        if roe > 0.18 and debt < 1.2 and beat_rate >= 0.5:
            return "BUY", 0.74, "ROE, debt discipline, and beat rate support a stronger fundamentals view."
        if debt > 2.0 and beat_rate < 0.4:
            return "SELL", 0.69, "Debt burden and weaker earnings execution pressure the fundamentals outlook."
        return "HOLD", 0.56, "Fundamental evidence is mixed, so the safer posture is HOLD."
