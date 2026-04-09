from __future__ import annotations

import asyncio
from contextvars import ContextVar
from datetime import date
from datetime import timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _latest_valid(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[0])


def _normalize_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    return timestamp


def _normalize_datetime_index(values: Any) -> pd.DatetimeIndex:
    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    if not isinstance(parsed, pd.DatetimeIndex):
        return pd.DatetimeIndex([])
    return parsed.tz_convert(None)


_SEEDED_BACKTEST_HISTORY: ContextVar[dict[str, pd.DataFrame] | None] = ContextVar(
    "seeded_backtest_history",
    default=None,
)


class YFinanceAdapter(DataAdapter):
    source_name = "yfinance"
    default_ttl_minutes = 30
    supports_point_in_time = True

    @classmethod
    def seed_backtest_history(cls, frames: dict[str, pd.DataFrame]):
        normalized: dict[str, pd.DataFrame] = {}
        for ticker, frame in frames.items():
            if frame.empty:
                normalized[ticker.upper()] = frame.copy()
                continue
            seeded = frame.copy()
            if not isinstance(seeded.index, pd.DatetimeIndex):
                seeded.index = _normalize_datetime_index(seeded.index)
            else:
                seeded.index = _normalize_datetime_index(seeded.index)
            seeded = seeded[~seeded.index.isna()].sort_index()
            normalized[ticker.upper()] = seeded
        return _SEEDED_BACKTEST_HISTORY.set(normalized)

    @classmethod
    def reset_backtest_history(cls, token) -> None:
        _SEEDED_BACKTEST_HISTORY.reset(token)

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_fundamentals(
            ticker,
            as_of_datetime=as_of_datetime,
            point_in_time_required=bool(as_of_datetime),
        )
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=False,
        )

    async def get_fundamentals(
        self,
        ticker: str,
        as_of_datetime: str | None = None,
        *,
        point_in_time_required: bool = False,
    ) -> dict[str, float | None]:
        if point_in_time_required:
            return {}

        info = await self._get_info(ticker)
        return {
            "pe_ratio": _to_float(info.get("trailingPE")),
            "pb_ratio": _to_float(info.get("priceToBook")),
            "ev_ebitda": _to_float(info.get("enterpriseToEbitda")),
            "gross_margin": _to_float(info.get("grossMargins")),
            "operating_margin": _to_float(info.get("operatingMargins")),
            "net_margin": _to_float(info.get("profitMargins")),
            "roe": _to_float(info.get("returnOnEquity")),
            "roa": _to_float(info.get("returnOnAssets")),
            "debt_to_equity": _to_float(info.get("debtToEquity")),
            "current_ratio": _to_float(info.get("currentRatio")),
        }

    async def get_ohlcv(self, ticker: str, periods: int = 260, as_of_datetime: str | None = None) -> pd.DataFrame:
        as_of = parse_as_of_date(as_of_datetime)
        start = as_of - timedelta(days=max(periods * 4, 400))
        frame = await self._history(ticker, start=start.isoformat(), end=(as_of + timedelta(days=1)).isoformat())
        if frame.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        frame = self._normalize_history_frame(frame)
        return frame.tail(periods).reset_index(drop=True)

    async def get_price_history(
        self,
        ticker: str,
        *,
        start_date: date | str,
        end_date: date | str,
    ) -> pd.DataFrame:
        start = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
        end = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
        frame = await self._history(ticker, start=start, end=end)
        if frame.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        return self._normalize_history_frame(frame)

    async def get_latest_price(self, ticker: str) -> float | None:
        frame = await self.get_price_history(
            ticker,
            start_date=(parse_as_of_date(None) - timedelta(days=10)),
            end_date=(parse_as_of_date(None) + timedelta(days=1)),
        )
        closes = pd.to_numeric(frame.get("close"), errors="coerce").dropna()
        if closes.empty:
            return None
        return round(float(closes.iloc[-1]), 4)

    async def get_security_profile(self, ticker: str) -> dict[str, str | None]:
        info = await self._get_info(ticker)
        return {
            "sector": str(info.get("sector") or "").strip() or None,
            "name": str(info.get("shortName") or info.get("longName") or ticker.upper()).strip(),
        }

    async def get_options_put_call_ratio(
        self,
        ticker: str,
        as_of_datetime: str | None = None,
        *,
        point_in_time_required: bool = False,
    ) -> float | None:
        if point_in_time_required or as_of_datetime is not None:
            return None

        cache_key = self._cache_key("options-put-call", ticker.upper())
        cached = await self.cache.get(cache_key)
        if isinstance(cached, (int, float)):
            return float(cached)

        def _load() -> float | None:
            security = yf.Ticker(ticker)
            expirations = list(security.options or [])
            if not expirations:
                return None
            chain = security.option_chain(expirations[0])
            calls = chain.calls
            puts = chain.puts
            call_oi = float(calls.get("openInterest", pd.Series(dtype=float)).fillna(0).sum())
            put_oi = float(puts.get("openInterest", pd.Series(dtype=float)).fillna(0).sum())
            if call_oi <= 0:
                return None
            return round(put_oi / call_oi, 4)

        ratio = await asyncio.to_thread(_load)
        if ratio is not None:
            await self.cache.set(cache_key, ratio, ttl_minutes=15, source=self.source_name)
        return ratio

    async def get_value_snapshot(
        self,
        ticker: str,
        as_of_datetime: str | None = None,
        *,
        point_in_time_required: bool = False,
    ) -> dict[str, float | int | None]:
        if point_in_time_required:
            return {}

        info = await self._get_info(ticker)
        dividends = await self._dividends(ticker)
        market_cap = _to_float(info.get("marketCap"))
        free_cash_flow = _to_float(info.get("freeCashflow"))
        fcf_yield = None
        if market_cap and market_cap > 0 and free_cash_flow is not None:
            fcf_yield = round(free_cash_flow / market_cap, 6)

        return {
            "forward_pe": _to_float(info.get("forwardPE")),
            "ev_revenue": _to_float(info.get("enterpriseToRevenue")),
            "fcf_yield": fcf_yield,
            "dividend_yield": _to_float(info.get("dividendYield")),
            "dividend_growth_years": self._dividend_growth_years(dividends),
            "buyback_ratio": None,
        }

    async def get_momentum_snapshot(self, ticker: str, as_of_datetime: str | None = None) -> dict[str, float | None]:
        periods = 260
        frame = await self.get_ohlcv(ticker, periods=periods, as_of_datetime=as_of_datetime)
        benchmark = await self.get_ohlcv("SPY", periods=periods, as_of_datetime=as_of_datetime)
        if frame.empty or benchmark.empty:
            return {}

        closes = pd.to_numeric(frame["close"], errors="coerce").dropna().reset_index(drop=True)
        spy_closes = pd.to_numeric(benchmark["close"], errors="coerce").dropna().reset_index(drop=True)
        volume = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).reset_index(drop=True)
        if len(closes) < 65 or len(spy_closes) < 65:
            return {}

        def _period_return(series: pd.Series, days: int) -> float | None:
            if len(series) <= days:
                return None
            start = float(series.iloc[-days - 1])
            end = float(series.iloc[-1])
            if start == 0:
                return None
            return round((end / start) - 1.0, 6)

        ret_12m = _period_return(closes, min(252, len(closes) - 1))
        ret_6m = _period_return(closes, min(126, len(closes) - 1))
        ret_3m = _period_return(closes, min(63, len(closes) - 1))
        spy_12m = _period_return(spy_closes, min(252, len(spy_closes) - 1))
        spy_6m = _period_return(spy_closes, min(126, len(spy_closes) - 1))
        spy_3m = _period_return(spy_closes, min(63, len(spy_closes) - 1))
        high_52 = float(closes.max())
        low_52 = float(closes.min())
        latest = float(closes.iloc[-1])
        range_position = None
        if high_52 > low_52:
            range_position = round((latest - low_52) / (high_52 - low_52), 6)

        recent_volume = float(volume.tail(20).mean())
        prior_volume = float(volume.iloc[-40:-20].mean()) if len(volume) >= 40 else 0.0
        volume_trend = None
        if prior_volume > 0:
            volume_trend = round((recent_volume / prior_volume) - 1.0, 6)

        return {
            "returns_12m": ret_12m,
            "returns_6m": ret_6m,
            "returns_3m": ret_3m,
            "relative_strength_vs_spy_12m": None if ret_12m is None or spy_12m is None else round(ret_12m - spy_12m, 6),
            "relative_strength_vs_spy_6m": None if ret_6m is None or spy_6m is None else round(ret_6m - spy_6m, 6),
            "relative_strength_vs_spy_3m": None if ret_3m is None or spy_3m is None else round(ret_3m - spy_3m, 6),
            "position_in_52w_range": range_position,
            "volume_trend": volume_trend,
        }

    async def get_growth_snapshot(
        self,
        ticker: str,
        as_of_datetime: str | None = None,
        *,
        point_in_time_required: bool = False,
    ) -> dict[str, float | None]:
        if point_in_time_required:
            return {}

        income_stmt = await self._quarterly_income_statement(ticker)
        if income_stmt.empty:
            return {}

        revenue = self._statement_row(income_stmt, ["Total Revenue", "Revenue", "Operating Revenue"])
        gross_profit = self._statement_row(income_stmt, ["Gross Profit"])
        net_income = self._statement_row(income_stmt, ["Net Income", "Net Income Common Stockholders"])
        revenue_growth = self._quarterly_yoy_growth(revenue)
        gross_margin = (gross_profit / revenue.replace(0, pd.NA)).dropna() if not gross_profit.empty and not revenue.empty else pd.Series(dtype=float)

        recent_net = pd.to_numeric(net_income.iloc[:4], errors="coerce").dropna()
        prior_net = pd.to_numeric(net_income.iloc[4:8], errors="coerce").dropna()
        earnings_growth = None
        if len(recent_net) == 4 and len(prior_net) == 4:
            previous = float(prior_net.sum())
            if previous != 0:
                earnings_growth = round((float(recent_net.sum()) / previous) - 1.0, 6)

        gross_margin_trend = None
        if len(gross_margin) >= 4:
            recent_margin = float(gross_margin.iloc[:2].mean())
            prior_margin = float(gross_margin.iloc[2:4].mean())
            gross_margin_trend = round(recent_margin - prior_margin, 6)

        payload: dict[str, float | None] = {
            "revenue_growth_q1": revenue_growth[0] if len(revenue_growth) > 0 else None,
            "revenue_growth_q2": revenue_growth[1] if len(revenue_growth) > 1 else None,
            "revenue_growth_q3": revenue_growth[2] if len(revenue_growth) > 2 else None,
            "revenue_growth_q4": revenue_growth[3] if len(revenue_growth) > 3 else None,
            "earnings_growth_last4q": earnings_growth,
            "gross_margin_trend": gross_margin_trend,
        }
        return payload

    async def get_macro_proxy_snapshot(self, as_of_datetime: str | None = None) -> dict[str, float | None]:
        vix = await self.get_ohlcv("^VIX", periods=30, as_of_datetime=as_of_datetime)
        spy = await self.get_ohlcv("SPY", periods=30, as_of_datetime=as_of_datetime)
        tlt = await self.get_ohlcv("TLT", periods=30, as_of_datetime=as_of_datetime)
        gld = await self.get_ohlcv("GLD", periods=30, as_of_datetime=as_of_datetime)

        def _monthly_return(frame: pd.DataFrame) -> float | None:
            closes = pd.to_numeric(frame.get("close"), errors="coerce").dropna().reset_index(drop=True)
            if len(closes) < 22:
                return None
            start = float(closes.iloc[-22])
            end = float(closes.iloc[-1])
            if start == 0:
                return None
            return round((end / start) - 1.0, 6)

        vix_close = pd.to_numeric(vix.get("close"), errors="coerce").dropna()
        return {
            "vix": None if vix_close.empty else round(float(vix_close.iloc[-1]), 4),
            "spy_return_1m": _monthly_return(spy),
            "tlt_return_1m": _monthly_return(tlt),
            "gld_return_1m": _monthly_return(gld),
        }

    async def _history(self, ticker: str, *, start: str, end: str) -> pd.DataFrame:
        seeded = self._seeded_history_frame(ticker, start=start, end=end)
        if seeded is not None:
            return seeded

        cache_key = self._cache_key("history", ticker.upper(), start, end)
        cached = await self.cache.get(cache_key)
        if isinstance(cached, list):
            return pd.DataFrame(cached)

        def _download() -> pd.DataFrame:
            frame = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=False)
            if frame.empty:
                return pd.DataFrame()
            return frame.reset_index()

        frame = await asyncio.to_thread(_download)
        serializable = frame.copy()
        for column in serializable.columns:
            if pd.api.types.is_datetime64_any_dtype(serializable[column]):
                serializable[column] = serializable[column].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        records = serializable.to_dict(orient="records")
        await self.cache.set(cache_key, records, ttl_minutes=15, source=self.source_name)
        return frame

    def _normalize_history_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        if "date" not in frame.columns:
            frame = frame.reset_index().rename(columns={"index": "date"})
        normalized_dates = _normalize_datetime_index(frame["date"])
        if len(normalized_dates) == len(frame):
            frame = frame.loc[~normalized_dates.isna()].copy()
            frame["date"] = normalized_dates[~normalized_dates.isna()].strftime("%Y-%m-%d")
        else:
            frame["date"] = frame["date"].astype(str).str[:10]
        return frame[["date", "open", "high", "low", "close", "volume"]]

    async def _get_info(self, ticker: str) -> dict[str, Any]:
        cache_key = self._cache_key("info", ticker.upper())
        cached = await self.cache.get(cache_key)
        if isinstance(cached, dict):
            return cached

        def _load() -> dict[str, Any]:
            return dict(yf.Ticker(ticker).info or {})

        info = await asyncio.to_thread(_load)
        await self.cache.set(cache_key, info, ttl_minutes=60, source=self.source_name)
        return info

    async def _dividends(self, ticker: str) -> pd.Series:
        cache_key = self._cache_key("dividends", ticker.upper())
        cached = await self.cache.get(cache_key)
        if isinstance(cached, dict):
            raw_index = cached.get("index", [])
            raw_values = cached.get("values", [])
            if not raw_index or not raw_values:
                return pd.Series(dtype=float)
            index = _normalize_datetime_index(raw_index)
            values = pd.to_numeric(pd.Series(raw_values), errors="coerce")
            usable = min(len(index), len(values))
            if usable == 0:
                return pd.Series(dtype=float)
            index = index[:usable]
            values = values.iloc[:usable]
            valid_mask = ~index.isna() & values.notna().to_numpy()
            if not valid_mask.any():
                return pd.Series(dtype=float)
            return pd.Series(values.iloc[valid_mask].to_numpy(), index=index[valid_mask], dtype=float).sort_index()

        def _load() -> pd.Series:
            series = yf.Ticker(ticker).dividends
            if series is None or series.empty or not isinstance(series.index, pd.Index):
                return pd.Series(dtype=float)
            if not isinstance(series.index, pd.DatetimeIndex):
                return pd.Series(dtype=float)
            cleaned = series.astype(float)
            cleaned.index = _normalize_datetime_index(cleaned.index)
            cleaned = cleaned[~cleaned.index.isna()]
            return cleaned.sort_index()

        dividends = await asyncio.to_thread(_load)
        await self.cache.set(
            cache_key,
            {
                "index": [item.isoformat() for item in dividends.index.to_pydatetime()],
                "values": dividends.tolist(),
            },
            ttl_minutes=1440,
            source=self.source_name,
        )
        return dividends

    async def _quarterly_income_statement(self, ticker: str) -> pd.DataFrame:
        cache_key = self._cache_key("quarterly-income-statement", ticker.upper())
        cached = await self.cache.get(cache_key)
        if isinstance(cached, dict):
            frame = pd.DataFrame(cached["data"], index=cached["index"], columns=cached["columns"])
            parsed_columns = _normalize_datetime_index(frame.columns)
            if len(parsed_columns) == len(frame.columns):
                frame.columns = parsed_columns
            return frame

        def _load() -> pd.DataFrame:
            frame = yf.Ticker(ticker).quarterly_income_stmt
            if frame is None or frame.empty:
                return pd.DataFrame()
            ordered = frame.sort_index(axis=1, ascending=False)
            return ordered

        frame = await asyncio.to_thread(_load)
        await self.cache.set(
            cache_key,
            {
                "index": [str(item) for item in frame.index],
                "columns": [col.isoformat() if hasattr(col, "isoformat") else str(col) for col in frame.columns],
                "data": frame.values.tolist(),
            },
            ttl_minutes=360,
            source=self.source_name,
        )
        return frame

    def _seeded_history_frame(self, ticker: str, *, start: str, end: str) -> pd.DataFrame | None:
        seeded_frames = _SEEDED_BACKTEST_HISTORY.get()
        if not seeded_frames:
            return None
        frame = seeded_frames.get(ticker.upper())
        if frame is None:
            return None
        if frame.empty:
            return pd.DataFrame()
        start_ts = _normalize_timestamp(start)
        end_ts = _normalize_timestamp(end)
        window = frame.loc[(frame.index >= start_ts) & (frame.index < end_ts)].copy()
        if window.empty:
            return pd.DataFrame()
        return window.reset_index(names="Date")

    def _statement_row(self, frame: pd.DataFrame, labels: list[str]) -> pd.Series:
        for label in labels:
            if label in frame.index:
                series = pd.to_numeric(frame.loc[label], errors="coerce")
                return series.sort_index(ascending=False)
        return pd.Series(dtype=float)

    def _quarterly_yoy_growth(self, series: pd.Series) -> list[float | None]:
        if series.empty:
            return []
        values = pd.to_numeric(series, errors="coerce").dropna().reset_index(drop=True)
        growth: list[float | None] = []
        for offset in range(4):
            if len(values) <= offset + 4:
                growth.append(None)
                continue
            previous = float(values.iloc[offset + 4])
            current = float(values.iloc[offset])
            if previous == 0:
                growth.append(None)
                continue
            growth.append(round((current / previous) - 1.0, 6))
        return growth

    def _dividend_growth_years(self, dividends: pd.Series) -> int | None:
        if dividends.empty:
            return None
        yearly = dividends.resample("YE").sum()
        if yearly.empty:
            return None
        count = 0
        previous: float | None = None
        for value in yearly.sort_index(ascending=False):
            numeric = float(value)
            if numeric <= 0:
                break
            if previous is not None and numeric > previous:
                break
            count += 1
            previous = numeric
        return count
