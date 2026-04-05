import httpx
import pandas as pd
import pytest

from backend.agents.analysis.fundamentals import FundamentalsAgent
from backend.config import settings
from backend.data.adapters import EdgarAdapter, FmpAdapter, PolygonAdapter, YFinanceAdapter
from backend.llm.strategy_builder import default_compiled_team
from backend.models.agent_team import DataBoundary, ExecutionSnapshot
from backend.settings.user_settings import DataSourceSettings


@pytest.mark.asyncio
async def test_fmp_adapter_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "fmp_api_key", "")
    payload = await FmpAdapter().get_earnings_snapshot("AAPL")
    assert payload == {}


@pytest.mark.asyncio
async def test_polygon_adapter_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "polygon_api_key", "")
    payload = await PolygonAdapter().fetch("AAPL")
    assert payload.payload == {}
    assert payload.point_in_time_supported is False


@pytest.mark.asyncio
async def test_fmp_adapter_returns_empty_for_historical_request_without_key(monkeypatch):
    monkeypatch.setattr(settings, "fmp_api_key", "")
    earlier = await FmpAdapter().get_earnings_snapshot("AAPL", as_of_datetime="2024-01-01T00:00:00+00:00")
    later = await FmpAdapter().get_earnings_snapshot("AAPL", as_of_datetime="2025-01-01T00:00:00+00:00")
    assert earlier == {}
    assert later == {}


@pytest.mark.asyncio
async def test_edgar_adapter_returns_empty_sections_on_missing_submission(monkeypatch):
    adapter = EdgarAdapter()

    async def fake_lookup(_ticker: str) -> str | None:
        return "0000947484"

    async def fake_get_json(*args, **kwargs):
        request = httpx.Request("GET", "https://data.sec.gov/submissions/CIK0000947484.json")
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr(adapter, "_lookup_cik", fake_lookup)
    monkeypatch.setattr(adapter, "_get_json", fake_get_json)

    payload = await adapter.get_latest_filing_sections("XYZ")

    assert payload == {
        "latest_10k_summary": None,
        "latest_10q_summary": None,
        "mda_section": None,
    }


@pytest.mark.asyncio
async def test_fundamentals_agent_marks_edgar_as_failed_when_adapter_raises(monkeypatch):
    team = default_compiled_team().model_copy(deep=True)
    spec = team.compiled_agent_specs["fundamentals"]
    snapshot = ExecutionSnapshot(
        mode="backtest_experimental",
        created_at="2026-04-04T00:00:00+00:00",
        ticker_or_universe="AAPL",
        effective_team=team,
        provider="test",
        model="test",
        prompt_pack_versions={"fundamentals": "fundamentals-core@1.0.0"},
        settings_hash="settings",
        team_hash="team",
        data_boundary=DataBoundary(mode="backtest_experimental", as_of_datetime="2024-03-29T16:00:00+00:00"),
        cost_model={},
    )

    async def fake_get_fundamentals(self, *args, **kwargs):
        return {"pe_ratio": 18.0}

    async def fake_get_latest_filing_sections(self, *args, **kwargs):
        raise RuntimeError("sec unavailable")

    monkeypatch.setattr(EdgarAdapter, "get_latest_filing_sections", fake_get_latest_filing_sections)
    monkeypatch.setattr("backend.agents.analysis.fundamentals.YFinanceAdapter.get_fundamentals", fake_get_fundamentals)

    data = await FundamentalsAgent().fetch_data(
        "AAPL",
        DataSourceSettings(use_yfinance=True, use_edgar=True, use_fmp=False),
        spec,
        snapshot,
    )

    assert data.fields["pe_ratio"] == 18.0
    assert "edgar" in data.failed_sources


@pytest.mark.asyncio
async def test_yfinance_dividends_cache_handles_mixed_timezones_and_empty_indexes():
    adapter = YFinanceAdapter()

    async def fake_get(_key: str):
        return {
            "index": [
                "2024-03-01T00:00:00-0500",
                "2024-06-01T00:00:00-0400",
            ],
            "values": [0.24, 0.25],
        }

    adapter.cache.get = fake_get  # type: ignore[method-assign]
    dividends = await adapter._dividends("AAPL")

    assert list(dividends.astype(float)) == [0.24, 0.25]
    assert isinstance(dividends.index, pd.DatetimeIndex)
    assert dividends.index.tz is None

    async def fake_empty_get(_key: str):
        return {"index": [], "values": []}

    adapter.cache.get = fake_empty_get  # type: ignore[method-assign]
    empty_dividends = await adapter._dividends("ABC")
    assert empty_dividends.empty
