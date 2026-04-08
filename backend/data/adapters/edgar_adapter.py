from __future__ import annotations

import re
from typing import Any

import httpx

from backend.data.adapters.base import AdapterFetchResult, DataAdapter, iso_timestamp, parse_as_of_date


SEC_HEADERS = {
    "User-Agent": "FinPilot/0.1 support@local.invalid",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}


class EdgarAdapter(DataAdapter):
    source_name = "edgar"
    default_ttl_minutes = 1440
    supports_point_in_time = True

    async def fetch(self, ticker: str, as_of_datetime: str | None = None) -> AdapterFetchResult:
        payload = await self.get_latest_filing_sections(ticker, as_of_datetime=as_of_datetime)
        return AdapterFetchResult(
            source=self.source_name,
            fetched_at=iso_timestamp(as_of_datetime),
            payload=payload,
            point_in_time_supported=True,
        )

    async def get_latest_filing_sections(self, ticker: str, as_of_datetime: str | None = None) -> dict[str, str | None]:
        cik = await self._lookup_cik(ticker)
        if cik is None:
            return {
                "latest_10k_summary": None,
                "latest_10q_summary": None,
                "mda_section": None,
            }

        as_of = parse_as_of_date(as_of_datetime)
        try:
            submissions = await self._get_json(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                headers=SEC_HEADERS,
                cache_key=self._cache_key("submissions", cik),
                ttl_minutes=1440,
                rate_limit_name="edgar",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {
                    "latest_10k_summary": None,
                    "latest_10q_summary": None,
                    "mda_section": None,
                }
            raise
        except httpx.HTTPError:
            return {
                "latest_10k_summary": None,
                "latest_10q_summary": None,
                "mda_section": None,
            }

        recent = submissions.get("filings", {}).get("recent", {})
        filing_10k = self._latest_filing(recent, as_of, {"10-K", "10-K/A"})
        filing_10q = self._latest_filing(recent, as_of, {"10-Q", "10-Q/A"})

        ten_k_text = await self._fetch_filing_text(cik, filing_10k) if filing_10k else None
        ten_q_text = await self._fetch_filing_text(cik, filing_10q) if filing_10q else None

        return {
            "latest_10k_summary": self._excerpt(ten_k_text),
            "latest_10q_summary": self._excerpt(ten_q_text),
            "mda_section": self._extract_mda(ten_k_text) or self._extract_mda(ten_q_text),
        }

    async def _lookup_cik(self, ticker: str) -> str | None:
        try:
            payload = await self._get_json(
                "https://www.sec.gov/files/company_tickers.json",
                headers=SEC_HEADERS,
                cache_key=self._cache_key("company-tickers"),
                ttl_minutes=10080,
                rate_limit_name="edgar",
            )
        except httpx.HTTPError:
            return None
        normalized = ticker.strip().upper()
        for item in payload.values():
            if str(item.get("ticker", "")).upper() == normalized:
                return str(item.get("cik_str", "")).zfill(10)
        return None

    def _latest_filing(
        self,
        recent: dict[str, list[Any]],
        as_of,
        accepted_forms: set[str],
    ) -> dict[str, str] | None:
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_documents = recent.get("primaryDocument", [])
        for form, filing_date, accession_number, primary_document in zip(
            forms,
            filing_dates,
            accession_numbers,
            primary_documents,
            strict=False,
        ):
            if form not in accepted_forms:
                continue
            if filing_date and parse_as_of_date(f"{filing_date}T00:00:00+00:00") <= as_of:
                return {
                    "form": form,
                    "filing_date": filing_date,
                    "accession_number": accession_number,
                    "primary_document": primary_document,
                }
        return None

    async def _fetch_filing_text(self, cik: str, filing: dict[str, str]) -> str | None:
        accession = filing["accession_number"].replace("-", "")
        cik_int = str(int(cik))
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{filing['primary_document']}"
        try:
            raw = await self._get_text(
                url,
                headers=SEC_HEADERS,
                cache_key=self._cache_key("filing", cik, filing["accession_number"], filing["primary_document"]),
                ttl_minutes=10080,
                rate_limit_name="edgar",
                timeout=30.0,
            )
        except Exception:
            return None
        cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
        cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
        cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"&nbsp;|&#160;", " ", cleaned)
        cleaned = re.sub(r"&amp;", "&", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip() or None

    def _excerpt(self, text: str | None, limit: int = 900) -> str | None:
        if not text:
            return None
        return text[:limit].strip()

    def _extract_mda(self, text: str | None, limit: int = 2000) -> str | None:
        if not text:
            return None
        patterns = [
            r"management(?:’|')?s discussion and analysis",
            r"item\s+7\.\s+management(?:’|')?s discussion and analysis",
            r"item\s+2\.\s+management(?:’|')?s discussion and analysis",
        ]
        lowered = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return text[match.start() : match.start() + limit].strip()
        return self._excerpt(text, limit=limit)
