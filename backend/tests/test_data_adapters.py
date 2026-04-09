import httpx
import pandas as pd
import pytest

from backend.agents.analysis.fundamentals import FundamentalsAgent
from backend.agents.analysis.sentiment import SentimentAgent
from backend.config import settings
from backend.data.adapters import (
    AlpacaDataAdapter,
    EdgarAdapter,
    FinnhubAdapter,
    FmpAdapter,
    MarketauxAdapter,
    PolygonAdapter,
    RedditAdapter,
    SecCompanyFactsAdapter,
    YFinanceAdapter,
)
from backend.llm.strategy_builder import default_compiled_team
from backend.models.agent_team import DataBoundary, ExecutionSnapshot
from backend.settings.user_settings import DataSourceSettings


@pytest.mark.asyncio
async def test_fmp_adapter_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "fmp_api_key", "")
    payload = await FmpAdapter().get_earnings_snapshot("AAPL")
    assert payload == {}


@pytest.mark.asyncio
async def test_finnhub_adapter_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "finnhub_api_key", "")
    payload = await FinnhubAdapter().get_news_snapshot("AAPL")
    assert payload == {}


@pytest.mark.asyncio
async def test_marketaux_adapter_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "marketaux_api_key", "")
    payload = await MarketauxAdapter().get_entity_sentiment("AAPL")
    assert payload == {}


@pytest.mark.asyncio
async def test_reddit_adapter_returns_empty_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "reddit_client_id", "")
    monkeypatch.setattr(settings, "reddit_client_secret", "")
    payload = await RedditAdapter().get_social_snapshot("AAPL")
    assert payload == {}


@pytest.mark.asyncio
async def test_alpaca_data_adapter_returns_empty_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "alpaca_api_key", "")
    monkeypatch.setattr(settings, "alpaca_secret_key", "")
    payload = await AlpacaDataAdapter().fetch("AAPL")
    assert payload.payload == {}
    assert payload.point_in_time_supported is False


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

    async def fake_get_company_snapshot(self, *args, **kwargs):
        return {"pe_ratio": 18.0}

    async def fake_get_latest_filing_sections(self, *args, **kwargs):
        raise RuntimeError("sec unavailable")

    monkeypatch.setattr(EdgarAdapter, "get_latest_filing_sections", fake_get_latest_filing_sections)
    monkeypatch.setattr(
        "backend.agents.analysis.fundamentals.SecCompanyFactsAdapter.get_company_snapshot",
        fake_get_company_snapshot,
    )

    data = await FundamentalsAgent().fetch_data(
        "AAPL",
        DataSourceSettings(use_yfinance=True, use_edgar=True, use_fmp=False, use_sec_companyfacts=True),
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


def _quarter_fact(start: str, end: str, value: float, filed: str, *, form: str = "10-Q", fp: str = "Q1"):
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": f"accn-{end}",
        "fy": int(end[:4]),
        "fp": fp,
        "form": form,
        "filed": filed,
        "frame": f"CY{end[:4]}Q{fp[-1] if fp.startswith('Q') else '4'}",
    }


def _instant_fact(end: str, value: float, filed: str, *, form: str = "10-Q", fp: str = "Q1"):
    return {
        "end": end,
        "val": value,
        "accn": f"accn-{end}",
        "fy": int(end[:4]),
        "fp": fp,
        "form": form,
        "filed": filed,
        "frame": f"CY{end[:4]}Q{fp[-1] if fp.startswith('Q') else '4'}I",
    }


@pytest.mark.asyncio
async def test_sec_companyfacts_adapter_builds_point_in_time_snapshot(monkeypatch):
    adapter = SecCompanyFactsAdapter()

    async def fake_lookup(_ticker: str):
        return {"cik": "0000000001", "name": "Example Corp"}

    async def fake_get_json(*args, **kwargs):  # noqa: ARG001
        return {
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 130.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 125.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 120.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 110.0, "2024-05-01", fp="Q1"),
                                _quarter_fact("2023-10-01", "2023-12-31", 100.0, "2024-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2023-07-01", "2023-09-30", 95.0, "2023-11-01", fp="Q3"),
                                _quarter_fact("2023-04-01", "2023-06-30", 90.0, "2023-08-01", fp="Q2"),
                                _quarter_fact("2023-01-01", "2023-03-31", 85.0, "2023-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "GrossProfit": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 65.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 62.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 60.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 55.0, "2024-05-01", fp="Q1"),
                                _quarter_fact("2023-10-01", "2023-12-31", 50.0, "2024-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2023-07-01", "2023-09-30", 47.0, "2023-11-01", fp="Q3"),
                                _quarter_fact("2023-04-01", "2023-06-30", 45.0, "2023-08-01", fp="Q2"),
                                _quarter_fact("2023-01-01", "2023-03-31", 42.0, "2023-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "OperatingIncomeLoss": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 32.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 31.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 30.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 28.0, "2024-05-01", fp="Q1"),
                                _quarter_fact("2023-10-01", "2023-12-31", 25.0, "2024-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2023-07-01", "2023-09-30", 24.0, "2023-11-01", fp="Q3"),
                                _quarter_fact("2023-04-01", "2023-06-30", 23.0, "2023-08-01", fp="Q2"),
                                _quarter_fact("2023-01-01", "2023-03-31", 22.0, "2023-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 24.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 23.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 22.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 20.0, "2024-05-01", fp="Q1"),
                                _quarter_fact("2023-10-01", "2023-12-31", 18.0, "2024-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2023-07-01", "2023-09-30", 17.0, "2023-11-01", fp="Q3"),
                                _quarter_fact("2023-04-01", "2023-06-30", 16.0, "2023-08-01", fp="Q2"),
                                _quarter_fact("2023-01-01", "2023-03-31", 15.0, "2023-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 28.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 27.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 26.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 25.0, "2024-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 4.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 4.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 4.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 4.0, "2024-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "DepreciationDepletionAndAmortization": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 3.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 3.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 3.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 3.0, "2024-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "CommonStockDividendsPerShareDeclared": {
                        "units": {
                            "USD/shares": [
                                _quarter_fact("2024-10-01", "2024-12-31", 0.30, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 0.29, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 0.28, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 0.27, "2024-05-01", fp="Q1"),
                                _quarter_fact("2023-10-01", "2023-12-31", 0.26, "2024-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2023-07-01", "2023-09-30", 0.25, "2023-11-01", fp="Q3"),
                                _quarter_fact("2023-04-01", "2023-06-30", 0.24, "2023-08-01", fp="Q2"),
                                _quarter_fact("2023-01-01", "2023-03-31", 0.23, "2023-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "Assets": {"units": {"USD": [_instant_fact("2024-12-31", 500.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "AssetsCurrent": {"units": {"USD": [_instant_fact("2024-12-31", 200.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "LiabilitiesCurrent": {"units": {"USD": [_instant_fact("2024-12-31", 100.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "StockholdersEquity": {"units": {"USD": [_instant_fact("2024-12-31", 250.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "LongTermDebt": {"units": {"USD": [_instant_fact("2024-12-31", 60.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "LongTermDebtCurrent": {"units": {"USD": [_instant_fact("2024-12-31", 10.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_instant_fact("2024-12-31", 40.0, "2025-02-01", form="10-K", fp="FY")]}},
                },
                "dei": {
                    "EntityCommonStockSharesOutstanding": {
                        "units": {
                            "shares": [
                                _instant_fact("2024-12-31", 10.0, "2025-02-01", form="10-K", fp="FY"),
                                _instant_fact("2024-09-30", 10.2, "2024-11-01", fp="Q3"),
                                _instant_fact("2024-06-30", 10.4, "2024-08-01", fp="Q2"),
                                _instant_fact("2024-03-31", 10.6, "2024-05-01", fp="Q1"),
                                _instant_fact("2023-12-31", 10.8, "2024-02-01", form="10-K", fp="FY"),
                            ]
                        }
                    }
                },
            }
        }

    async def fake_ohlcv(self, ticker, periods=5, as_of_datetime=None):  # noqa: ARG001
        return pd.DataFrame({"close": [50.0]})

    monkeypatch.setattr(adapter, "lookup_company", fake_lookup)
    monkeypatch.setattr(adapter, "_get_json", fake_get_json)
    monkeypatch.setattr(YFinanceAdapter, "get_ohlcv", fake_ohlcv)

    snapshot = await adapter.get_company_snapshot("EXM", as_of_datetime="2025-02-15T16:00:00+00:00")

    assert snapshot["company_name"] == "Example Corp"
    assert snapshot["pe_ratio"] == 5.617978
    assert snapshot["current_ratio"] == 2.0
    assert snapshot["dividend_growth_years"] == 2
    assert snapshot["buyback_ratio"] == 0.074074
    assert snapshot["revenue_growth_q1"] == 0.3
    assert snapshot["earnings_growth_last4q"] == 0.348485


@pytest.mark.asyncio
async def test_sec_companyfacts_adapter_ignores_stale_snapshot_cache_version(monkeypatch):
    adapter = SecCompanyFactsAdapter()

    async def fake_lookup(_ticker: str):
        return {"cik": "0000000002", "name": "Replay Safe Corp"}

    async def fake_get_json(*args, **kwargs):  # noqa: ARG001
        return {
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 100.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 100.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 100.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 100.0, "2024-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                _quarter_fact("2024-10-01", "2024-12-31", 25.0, "2025-02-01", form="10-K", fp="Q4"),
                                _quarter_fact("2024-07-01", "2024-09-30", 25.0, "2024-11-01", fp="Q3"),
                                _quarter_fact("2024-04-01", "2024-06-30", 25.0, "2024-08-01", fp="Q2"),
                                _quarter_fact("2024-01-01", "2024-03-31", 25.0, "2024-05-01", fp="Q1"),
                            ]
                        }
                    },
                    "AssetsCurrent": {"units": {"USD": [_instant_fact("2024-12-31", 150.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "LiabilitiesCurrent": {"units": {"USD": [_instant_fact("2024-12-31", 50.0, "2025-02-01", form="10-K", fp="FY")]}},
                    "StockholdersEquity": {"units": {"USD": [_instant_fact("2024-12-31", 200.0, "2025-02-01", form="10-K", fp="FY")]}},
                },
                "dei": {
                    "EntityCommonStockSharesOutstanding": {
                        "units": {"shares": [_instant_fact("2024-12-31", 10.0, "2025-02-01", form="10-K", fp="FY")]}
                    }
                },
            }
        }

    async def fake_ohlcv(self, ticker, periods=5, as_of_datetime=None):  # noqa: ARG001
        return pd.DataFrame({"close": [40.0]})

    stale_key = adapter._cache_key("snapshot", "REPLAY", "2025-02-15")
    await adapter.cache.set(
        stale_key,
        {"company_name": "Stale Corp", "current_ratio": 99.0},
        ttl_minutes=1440,
        source=adapter.source_name,
    )

    monkeypatch.setattr(adapter, "lookup_company", fake_lookup)
    monkeypatch.setattr(adapter, "_get_json", fake_get_json)
    monkeypatch.setattr(YFinanceAdapter, "get_ohlcv", fake_ohlcv)

    snapshot = await adapter.get_company_snapshot("REPLAY", as_of_datetime="2025-02-15T16:00:00+00:00")

    assert snapshot["company_name"] == "Replay Safe Corp"
    assert snapshot["current_ratio"] == 3.0


@pytest.mark.asyncio
async def test_sentiment_agent_uses_archived_news_sources_for_historical_replay(monkeypatch):
    team = default_compiled_team().model_copy(deep=True)
    spec = team.compiled_agent_specs["sentiment"]
    snapshot = ExecutionSnapshot(
        mode="backtest_experimental",
        created_at="2026-04-04T00:00:00+00:00",
        ticker_or_universe="AAPL",
        effective_team=team,
        provider="test",
        model="test",
        prompt_pack_versions={"sentiment": "sentiment-core@1.0.0"},
        settings_hash="settings",
        team_hash="team",
        data_boundary=DataBoundary(mode="backtest_experimental", as_of_datetime="2024-03-29T16:00:00+00:00"),
        cost_model={},
    )

    async def fake_finnhub(self, ticker, as_of_datetime=None):  # noqa: ARG001
        return {
            "headline_sentiment": 0.3,
            "headline_count": 2,
            "highlights": ["Company beats estimates", "Demand remains strong"],
        }

    async def fake_gdelt(self, ticker, company_name=None, as_of_datetime=None):  # noqa: ARG001
        return {
            "headline_sentiment": 0.1,
            "headline_count": 1,
            "highlights": ["Example wins new contract"],
        }

    async def fake_marketaux(self, ticker, as_of_datetime=None):  # noqa: ARG001
        return {}

    async def fake_options(self, ticker, as_of_datetime=None, point_in_time_required=False):  # noqa: ARG001
        return None

    monkeypatch.setattr("backend.agents.analysis.sentiment.FinnhubAdapter.get_news_snapshot", fake_finnhub)
    monkeypatch.setattr("backend.agents.analysis.sentiment.GdeltAdapter.get_news_snapshot", fake_gdelt)
    monkeypatch.setattr("backend.agents.analysis.sentiment.MarketauxAdapter.get_entity_sentiment", fake_marketaux)
    monkeypatch.setattr("backend.agents.analysis.sentiment.YFinanceAdapter.get_options_put_call_ratio", fake_options)

    data = await SentimentAgent().fetch_data(
        "AAPL",
        DataSourceSettings(
            use_finnhub=True,
            use_marketaux=True,
            use_reddit=True,
            use_yfinance=True,
            use_gdelt=True,
            use_sec_companyfacts=False,
        ),
        spec,
        snapshot,
    )

    assert data.fields["headline_sentiment"] == 0.2
    assert data.fields["headline_count"] == 3
    assert "sanitized_news_excerpt" in data.fields
    assert "reddit" in data.failed_sources
