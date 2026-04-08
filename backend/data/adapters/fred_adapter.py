from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pandas as pd

from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date


SERIES_IDS = {
    "fed_funds_rate": "FEDFUNDS",
    "treasury_10y": "GS10",
    "treasury_2y": "GS2",
    "cpi_index": "CPIAUCSL",
    "pce_index": "PCEPI",
    "gdp_growth_qoq": "A191RL1Q225SBEA",
    "unemployment_rate": "UNRATE",
}


class FredAdapter(DataAdapter):
    source_name = "fred"
    default_ttl_minutes = 360
    supports_point_in_time = True

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_macro_snapshot(as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=True,
        )

    async def get_macro_snapshot(self, as_of_datetime: str | None = None) -> dict[str, float | None]:
        as_of = parse_as_of_date(as_of_datetime)
        fed_funds = await self._series_value(SERIES_IDS["fed_funds_rate"], as_of)
        treasury_10y = await self._series_value(SERIES_IDS["treasury_10y"], as_of)
        treasury_2y = await self._series_value(SERIES_IDS["treasury_2y"], as_of)
        cpi_series = await self._series(SERIES_IDS["cpi_index"])
        pce_series = await self._series(SERIES_IDS["pce_index"])

        cpi_latest = self._last_value(cpi_series, as_of)
        cpi_year_ago = self._last_value(cpi_series, as_of - timedelta(days=365))
        pce_latest = self._last_value(pce_series, as_of)
        pce_year_ago = self._last_value(pce_series, as_of - timedelta(days=365))

        cpi_yoy = None
        if cpi_latest is not None and cpi_year_ago not in (None, 0):
            cpi_yoy = round((cpi_latest / cpi_year_ago) - 1.0, 6)

        pce_yoy = None
        if pce_latest is not None and pce_year_ago not in (None, 0):
            pce_yoy = round((pce_latest / pce_year_ago) - 1.0, 6)

        yield_curve_spread = None
        if treasury_10y is not None and treasury_2y is not None:
            yield_curve_spread = round(treasury_10y - treasury_2y, 6)

        return {
            "fed_funds_rate": fed_funds,
            "treasury_10y": treasury_10y,
            "treasury_2y": treasury_2y,
            "yield_curve_spread": yield_curve_spread,
            "cpi_yoy": cpi_yoy,
            "pce_yoy": pce_yoy,
            "gdp_growth_qoq": await self._series_value(SERIES_IDS["gdp_growth_qoq"], as_of),
            "unemployment_rate": await self._series_value(SERIES_IDS["unemployment_rate"], as_of),
        }

    async def _series(self, series_id: str) -> pd.Series:
        cache_key = self._cache_key("series", series_id)
        cached = await self.cache.get(cache_key)
        if isinstance(cached, dict):
            index = pd.to_datetime(cached.get("index", []))
            values = pd.to_numeric(cached.get("values", []), errors="coerce")
            return pd.Series(values, index=index, dtype=float).dropna()

        csv_text = await self._get_text(
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
            cache_key=cache_key,
            ttl_minutes=self.default_ttl_minutes,
        )
        frame = pd.read_csv(StringIO(csv_text))
        if frame.empty:
            return pd.Series(dtype=float)
        lower_columns = {str(column).strip().lower(): column for column in frame.columns}
        date_column = lower_columns.get("date") or lower_columns.get("observation_date")
        if date_column is None:
            return pd.Series(dtype=float)
        value_column = next(
            (column for column in frame.columns if column != date_column),
            frame.columns[-1],
        )
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
        cleaned = frame.dropna(subset=[date_column, value_column])
        series = pd.Series(cleaned[value_column].values, index=cleaned[date_column], dtype=float)
        await self.cache.set(
            cache_key,
            {
                "index": [item.isoformat() for item in series.index.to_pydatetime()],
                "values": series.tolist(),
            },
            ttl_minutes=self.default_ttl_minutes,
            source=self.source_name,
        )
        return series

    async def _series_value(self, series_id: str, as_of: pd.Timestamp | object) -> float | None:
        series = await self._series(series_id)
        return self._last_value(series, as_of)

    def _last_value(self, series: pd.Series, as_of: pd.Timestamp | object) -> float | None:
        if series.empty:
            return None
        boundary = pd.Timestamp(as_of)
        eligible = series[series.index <= boundary]
        if eligible.empty:
            return None
        return round(float(eligible.iloc[-1]), 6)
