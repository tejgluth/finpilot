from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.data.adapters import FredAdapter, YFinanceAdapter
from backend.settings.user_settings import DataSourceSettings


class MacroAgent(BaseAnalysisAgent):
    agent_name = "macro"
    EXPECTED_FIELDS = [
        "fed_funds_rate",
        "treasury_10y",
        "treasury_2y",
        "yield_curve_spread",
        "cpi_yoy",
        "pce_yoy",
        "gdp_growth_qoq",
        "unemployment_rate",
        "vix",
        "spy_return_1m",
        "tlt_return_1m",
        "gld_return_1m",
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
        allowed_sources = set(compiled_spec.owned_sources)
        if data_settings.use_fred and "fred" in allowed_sources:
            macro = await FredAdapter().get_macro_snapshot(as_of_datetime=as_of)
            for field_name, value in macro.items():
                data.fields[field_name] = value
                data.field_sources[field_name] = "fred"
                data.field_ages[field_name] = 120.0
        else:
            data.failed_sources.append("fred")

        if data_settings.use_yfinance and "yfinance" in allowed_sources:
            proxies = await YFinanceAdapter().get_macro_proxy_snapshot(as_of_datetime=as_of)
            for field_name, value in proxies.items():
                data.fields[field_name] = value
                data.field_sources[field_name] = "yfinance"
                data.field_ages[field_name] = 20.0
        else:
            data.failed_sources.append("yfinance")
        return data

    def build_system_prompt(self) -> str:
        return "Assess the macro regime using only rates, inflation, employment, and market proxy data.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        curve = float(data.fields.get("yield_curve_spread") or 0)
        vix = float(data.fields.get("vix") or 20)
        gdp = float(data.fields.get("gdp_growth_qoq") or 0)
        inflation = float(data.fields.get("cpi_yoy") or 0)
        if variant == "dalio_all_weather":
            if abs(curve) < 0.5 and inflation < 3.5 and vix < 24:
                return "BUY", 0.66, "Cross-asset regime balance looks constructive for an all-weather macro read."
        if variant == "marks_cycle_watch":
            if curve < 0 and vix > 23:
                return "SELL", 0.69, "Cycle signals and volatility point to a later-cycle caution signal."
        if variant == "risk_on_risk_off":
            if gdp > 0.01 and vix < 18:
                return "BUY", 0.64, "The regime leans risk-on across growth and volatility proxies."
        if curve > 0 and vix < 20 and gdp > 0:
            return "BUY", 0.61, "Macro backdrop looks constructive enough to support risk appetite."
        if curve < 0 and vix > 25:
            return "SELL", 0.64, "Inversion pressure and elevated volatility argue for caution."
        return "HOLD", 0.52, "Macro regime is mixed."
