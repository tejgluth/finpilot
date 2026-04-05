from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

import httpx
import pandas as pd

from backend.config import settings


CURRENT_SP500_SOURCES = [
    "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv",
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
]
HISTORICAL_SP500_MONTHLY_URL = "https://yfiua.github.io/index-constituents/{year}/{month:02d}/constituents-sp500.csv"
HISTORICAL_SP500_DAILY_URL = (
    "https://raw.githubusercontent.com/fja05680/sp500/master/"
    "S%26P%20500%20Historical%20Components%20%26%20Changes(01-17-2026).csv"
)
MONTHLY_SP500_START = date(2023, 7, 1)
SOURCE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
YAHOO_TICKER_ALIASES = {
    "BRKA": "BRK-A",
    "BRKB": "BRK-B",
    "BFA": "BF-A",
    "BFB": "BF-B",
}


@dataclass
class UniverseDateResolution:
    as_of_date: str
    tickers: list[str]
    source: str
    snapshot_hash: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class UniverseTimelineResolution:
    requested_universe_id: str
    universe_id: str
    source: str
    dates: list[UniverseDateResolution]
    warnings: list[str] = field(default_factory=list)

    @property
    def all_tickers(self) -> list[str]:
        return sorted({ticker for entry in self.dates for ticker in entry.tickers})

    def tickers_for(self, as_of_date: date) -> list[str]:
        target = as_of_date.isoformat()
        for entry in self.dates:
            if entry.as_of_date == target:
                return entry.tickers
        return self.dates[-1].tickers if self.dates else []


@dataclass
class UniverseResolution:
    universe_id: str
    tickers: list[str]
    source: str
    warnings: list[str] = field(default_factory=list)


class UniverseProvider:
    async def resolve(
        self,
        *,
        universe_id: str,
        custom_universe_csv: str | None,
        strict_mode: bool,
        single_ticker: str | None = None,
    ) -> UniverseResolution:
        timeline = await HistoricalUniverseResolver().resolve_for_dates(
            universe_id=universe_id,
            custom_universe_csv=custom_universe_csv,
            strict_mode=strict_mode,
            single_ticker=single_ticker,
            rebalance_dates=[date.today()],
        )
        tickers = timeline.dates[0].tickers if timeline.dates else []
        return UniverseResolution(
            universe_id=timeline.universe_id,
            tickers=tickers,
            source=timeline.source,
            warnings=timeline.warnings,
        )


class HistoricalUniverseResolver:
    async def resolve_for_dates(
        self,
        *,
        universe_id: str,
        custom_universe_csv: str | None,
        strict_mode: bool,
        rebalance_dates: list[date],
        single_ticker: str | None = None,
    ) -> UniverseTimelineResolution:
        unique_dates = sorted({item for item in rebalance_dates})
        if single_ticker:
            ticker = _normalize_ticker(single_ticker)
            entry = UniverseDateResolution(
                as_of_date=unique_dates[0].isoformat() if unique_dates else date.today().isoformat(),
                tickers=[ticker],
                source="direct_request",
                snapshot_hash=_hash_tickers([ticker]),
            )
            return UniverseTimelineResolution(
                requested_universe_id="single_ticker",
                universe_id="single_ticker",
                source="direct_request",
                dates=[entry],
            )

        if custom_universe_csv:
            tickers = await asyncio.to_thread(_load_csv_universe, custom_universe_csv)
            entry = UniverseDateResolution(
                as_of_date=unique_dates[0].isoformat() if unique_dates else date.today().isoformat(),
                tickers=tickers,
                source=f"csv_snapshot:{custom_universe_csv}",
                snapshot_hash=_hash_tickers(tickers),
                warnings=[
                    "Using the supplied universe snapshot for every rebalance date. "
                    "This is reproducible but only point-in-time honest if that CSV matches the requested window."
                ],
            )
            return UniverseTimelineResolution(
                requested_universe_id=universe_id,
                universe_id="csv_snapshot",
                source=f"csv_snapshot:{custom_universe_csv}",
                dates=[
                    UniverseDateResolution(
                        as_of_date=item.isoformat(),
                        tickers=entry.tickers,
                        source=entry.source,
                        snapshot_hash=entry.snapshot_hash,
                        warnings=list(entry.warnings),
                    )
                    for item in unique_dates
                ],
                warnings=list(entry.warnings),
            )

        normalized_id = universe_id.strip().lower()
        if normalized_id not in {"sp500", "current_sp500"}:
            raise ValueError(f"Unsupported universe_id: {universe_id}")

        resolved_entries: list[UniverseDateResolution] = []
        timeline_warnings: list[str] = []
        for as_of_date in unique_dates:
            entry = await self._resolve_sp500_date(
                as_of_date=as_of_date,
                strict_mode=strict_mode,
            )
            resolved_entries.append(entry)
            timeline_warnings.extend(entry.warnings)
        source = resolved_entries[0].source if resolved_entries else "historical_sp500"
        return UniverseTimelineResolution(
            requested_universe_id=universe_id,
            universe_id="historical_sp500" if not strict_mode else "strict_sp500",
            source=source,
            dates=resolved_entries,
            warnings=_dedupe(timeline_warnings),
        )

    async def _resolve_sp500_date(
        self,
        *,
        as_of_date: date,
        strict_mode: bool,
    ) -> UniverseDateResolution:
        errors: list[str] = []

        if as_of_date >= MONTHLY_SP500_START:
            try:
                tickers, source = await _load_monthly_snapshot(as_of_date)
                return UniverseDateResolution(
                    as_of_date=as_of_date.isoformat(),
                    tickers=tickers,
                    source=source,
                    snapshot_hash=_hash_tickers(tickers),
                    warnings=[
                        "Resolved S&P 500 membership from a free monthly historical snapshot."
                    ],
                )
            except ValueError as exc:
                errors.append(str(exc))

        try:
            tickers, source = await _load_daily_historical_snapshot(as_of_date)
            return UniverseDateResolution(
                as_of_date=as_of_date.isoformat(),
                tickers=tickers,
                source=source,
                snapshot_hash=_hash_tickers(tickers),
                warnings=[
                    "Resolved S&P 500 membership from a free historical constituent archive."
                ],
            )
        except ValueError as exc:
            errors.append(str(exc))

        if strict_mode:
            raise ValueError(
                f"Strict mode could not resolve historical S&P 500 membership for {as_of_date.isoformat()}. "
                + " | ".join(errors)
            )

        tickers = await asyncio.to_thread(_load_current_sp500)
        return UniverseDateResolution(
            as_of_date=as_of_date.isoformat(),
            tickers=tickers,
            source="fallback_current_sp500",
            snapshot_hash=_hash_tickers(tickers),
            warnings=[
                "Experimental mode fell back to today's S&P 500 membership. Results are survivorship-biased.",
                *errors,
            ],
        )


async def _load_monthly_snapshot(as_of_date: date) -> tuple[list[str], str]:
    cache_dir = _universe_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"sp500-monthly-{as_of_date.year}-{as_of_date.month:02d}.csv"
    if cache_path.exists():
        return _parse_symbol_csv(cache_path.read_text(encoding="utf-8")), f"cache:yfiua:{cache_path.name}"

    url = HISTORICAL_SP500_MONTHLY_URL.format(year=as_of_date.year, month=as_of_date.month)
    text = await _fetch_text(url)
    cache_path.write_text(text, encoding="utf-8")
    return _parse_symbol_csv(text), f"remote:yfiua:{as_of_date.year}-{as_of_date.month:02d}"


async def _load_daily_historical_snapshot(as_of_date: date) -> tuple[list[str], str]:
    cache_dir = _universe_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "sp500-historical-daily.csv"
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        source = f"cache:{cache_path.name}"
    else:
        text = await _fetch_text(HISTORICAL_SP500_DAILY_URL)
        cache_path.write_text(text, encoding="utf-8")
        source = "remote:fja05680"

    frame = pd.read_csv(StringIO(text))
    lower_columns = {str(column).strip().lower(): column for column in frame.columns}
    date_column = lower_columns.get("date")
    tickers_column = lower_columns.get("tickers")
    if date_column is None or tickers_column is None:
        raise ValueError("Historical S&P 500 daily archive is missing the expected date/tickers columns.")

    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame = frame.dropna(subset=[date_column])
    eligible = frame[frame[date_column].dt.date <= as_of_date]
    if eligible.empty:
        raise ValueError(f"Historical S&P 500 archive had no snapshot on or before {as_of_date.isoformat()}.")

    latest = eligible.iloc[-1]
    raw_tickers = str(latest[tickers_column])
    tickers = sorted(
        {
            _normalize_ticker(item)
            for item in raw_tickers.split(",")
            if _normalize_ticker(item)
        }
    )
    if not tickers:
        raise ValueError(f"Historical S&P 500 archive contained no tickers for {as_of_date.isoformat()}.")
    return tickers, source


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers=SOURCE_HEADERS,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _load_current_sp500() -> list[str]:
    errors: list[str] = []
    for source in CURRENT_SP500_SOURCES:
        try:
            response = httpx.get(
                source,
                follow_redirects=True,
                headers=SOURCE_HEADERS,
                timeout=20.0,
            )
            response.raise_for_status()
            return _parse_symbol_csv(response.text)
        except (httpx.HTTPError, ValueError, pd.errors.ParserError) as exc:
            errors.append(f"{source}: {exc}")

    raise ValueError(
        "Unable to load the current S&P 500 universe from public CSV sources. "
        + " | ".join(errors)
    )


def _load_csv_universe(path: str) -> list[str]:
    candidate = Path(path).expanduser().resolve()
    if not candidate.exists():
        raise ValueError(f"Universe CSV not found: {candidate}")
    if candidate.suffix.lower() not in {".csv", ".txt"}:
        raise ValueError("custom_universe_csv must point to a .csv or .txt file.")

    if candidate.suffix.lower() == ".txt":
        tickers = [_normalize_ticker(line) for line in candidate.read_text(encoding="utf-8").splitlines()]
        resolved = sorted({ticker for ticker in tickers if ticker})
        if not resolved:
            raise ValueError("Universe file did not contain any tickers.")
        return resolved

    return _parse_symbol_csv(candidate.read_text(encoding="utf-8"))


def _parse_symbol_csv(raw_csv: str) -> list[str]:
    frame = pd.read_csv(StringIO(raw_csv))
    lower_columns = {str(column).strip().lower(): column for column in frame.columns}
    symbol_column = lower_columns.get("symbol") or lower_columns.get("ticker")
    if symbol_column is None:
        if len(frame.columns) != 1:
            raise ValueError("Universe CSV must contain a 'symbol' or 'ticker' column.")
        symbol_column = frame.columns[0]
    tickers = [_normalize_ticker(value) for value in frame[symbol_column].astype(str).tolist()]
    resolved = sorted({ticker for ticker in tickers if ticker})
    if not resolved:
        raise ValueError("Universe CSV did not contain any tickers.")
    return resolved


def _hash_tickers(tickers: list[str]) -> str:
    return sha256(json.dumps(sorted(tickers)).encode("utf-8")).hexdigest()


def _normalize_ticker(raw: str) -> str:
    ticker = raw.strip().upper().replace(".", "-")
    if not ticker:
        return ""
    ticker = YAHOO_TICKER_ALIASES.get(ticker, ticker)
    if ticker[0].isdigit():
        return ""
    if ticker.endswith("-W") or ticker.endswith("-WI"):
        return ""
    return ticker


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _universe_cache_dir() -> Path:
    return Path(settings.cache_dir).expanduser().resolve() / "universes"
