from __future__ import annotations

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.data.adapters import (
    FinnhubAdapter,
    GdeltAdapter,
    MarketauxAdapter,
    RedditAdapter,
    SecCompanyFactsAdapter,
    YFinanceAdapter,
)
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.security.input_sanitizer import ContentSource, sanitize
from backend.settings.user_settings import DataSourceSettings


class SentimentAgent(BaseAnalysisAgent):
    agent_name = "sentiment"
    EXPECTED_FIELDS = [
        "headline_sentiment",
        "headline_count",
        "entity_sentiment",
        "entity_mentions",
        "reddit_mentions",
        "reddit_upvote_ratio",
        "put_call_ratio",
        "sanitized_news_excerpt",
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
        headline_scores: list[float] = []
        headline_count = 0
        headline_sources: list[str] = []
        headline_ages: list[float] = []
        sanitized_highlights: list[str] = []
        company_name = None

        if data_settings.use_sec_companyfacts:
            company = await SecCompanyFactsAdapter().lookup_company(ticker)
            company_name = company["name"] if company else None

        if data_settings.use_finnhub and "finnhub" in allowed_sources:
            snapshot = await FinnhubAdapter().get_news_snapshot(ticker, as_of_datetime=as_of)
            highlights = snapshot.get("highlights") or []
            if snapshot.get("headline_sentiment") is not None:
                headline_scores.append(float(snapshot["headline_sentiment"]))
                headline_sources.append("finnhub")
                headline_ages.append(30.0)
            if snapshot.get("headline_count") is not None:
                headline_count += int(snapshot["headline_count"])
            sanitized_highlights.extend(str(item) for item in highlights)
        else:
            data.failed_sources.append("finnhub")

        if data_settings.use_marketaux and "marketaux" in allowed_sources:
            snapshot = await MarketauxAdapter().get_entity_sentiment(ticker, as_of_datetime=as_of)
            if snapshot.get("entity_sentiment") is not None:
                data.fields["entity_sentiment"] = snapshot["entity_sentiment"]
                data.field_sources["entity_sentiment"] = "marketaux"
                data.field_ages["entity_sentiment"] = 45.0
            if snapshot.get("entity_mentions") is not None:
                data.fields["entity_mentions"] = snapshot["entity_mentions"]
                data.field_sources["entity_mentions"] = "marketaux"
                data.field_ages["entity_mentions"] = 45.0
            sanitized_highlights.extend(str(item) for item in snapshot.get("highlights", []))
        else:
            data.failed_sources.append("marketaux")

        if data_settings.use_gdelt and "gdelt" in allowed_sources:
            snapshot = await GdeltAdapter().get_news_snapshot(
                ticker,
                company_name=company_name,
                as_of_datetime=as_of,
            )
            if snapshot.get("headline_sentiment") is not None:
                headline_scores.append(float(snapshot["headline_sentiment"]))
                headline_sources.append("gdelt")
                headline_ages.append(60.0)
            if snapshot.get("headline_count") is not None:
                headline_count += int(snapshot["headline_count"])
            sanitized_highlights.extend(str(item) for item in snapshot.get("highlights", []))
        else:
            data.failed_sources.append("gdelt")

        if data_settings.use_reddit and "reddit" in allowed_sources and not historical_replay:
            snapshot = await RedditAdapter().get_social_snapshot(ticker, as_of_datetime=as_of)
            if snapshot.get("mention_count") is not None:
                data.fields["reddit_mentions"] = snapshot["mention_count"]
                data.field_sources["reddit_mentions"] = "reddit"
                data.field_ages["reddit_mentions"] = 60.0
            if snapshot.get("upvote_ratio") is not None:
                data.fields["reddit_upvote_ratio"] = snapshot["upvote_ratio"]
                data.field_sources["reddit_upvote_ratio"] = "reddit"
                data.field_ages["reddit_upvote_ratio"] = 60.0
        elif not historical_replay:
            data.failed_sources.append("reddit")
        else:
            data.failed_sources.append("reddit")

        if data_settings.use_yfinance and "yfinance" in allowed_sources:
            data.fields["put_call_ratio"] = await YFinanceAdapter().get_options_put_call_ratio(
                ticker,
                as_of_datetime=as_of,
                point_in_time_required=False,
            )
            if data.fields["put_call_ratio"] is not None:
                data.field_sources["put_call_ratio"] = "yfinance"
                data.field_ages["put_call_ratio"] = 15.0
        else:
            data.failed_sources.append("yfinance")

        if headline_scores:
            data.fields["headline_sentiment"] = round(sum(headline_scores) / len(headline_scores), 6)
            data.field_sources["headline_sentiment"] = "+".join(dict.fromkeys(headline_sources))
            data.field_ages["headline_sentiment"] = max(headline_ages, default=45.0)
        if headline_count > 0:
            data.fields["headline_count"] = headline_count
            data.field_sources["headline_count"] = "+".join(dict.fromkeys(headline_sources)) or "news"
            data.field_ages["headline_count"] = max(headline_ages, default=45.0)
        if sanitized_highlights:
            excerpt = sanitize(" ".join(dict.fromkeys(sanitized_highlights)), ContentSource.NEWS_BODY)
            data.fields["sanitized_news_excerpt"] = excerpt.sanitized_text
            data.field_sources["sanitized_news_excerpt"] = "+".join(dict.fromkeys(headline_sources)) or "news"
            data.field_ages["sanitized_news_excerpt"] = max(headline_ages, default=45.0)
        return data

    def build_system_prompt(self) -> str:
        return "Synthesize sanitized sentiment and options data only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        headline = float(data.fields.get("headline_sentiment") or 0)
        entity = float(data.fields.get("entity_sentiment") or 0)
        put_call = float(data.fields.get("put_call_ratio") or 1)
        reddit_mentions = float(data.fields.get("reddit_mentions") or 0)
        if variant == "event_driven":
            if headline > 0.2 and entity > 0.1:
                return "BUY", 0.66, "Headline and entity sentiment align for an event-driven positive read."
        if variant == "contrarian_reset":
            if headline < -0.2 and put_call > 1.15 and reddit_mentions > 30:
                return "BUY", 0.58, "Washout-style sentiment may offer contrarian rebound potential."
        if variant == "skeptical_filter" and abs(headline) < 0.1:
            return "HOLD", 0.45, "Sentiment data is noisy without enough corroboration."
        if headline > 0.15 and entity > 0.1 and put_call < 1.0:
            return "BUY", 0.63, "News tone and options positioning lean supportive."
        if headline < -0.15 and put_call > 1.15:
            return "SELL", 0.62, "News tone and options fear gauge both lean negative."
        return "HOLD", 0.5, "Sentiment is noisy or contradictory."
