from __future__ import annotations

import math
import re


POSITIVE_TERMS = {
    "beat",
    "beats",
    "bullish",
    "buyback",
    "contract",
    "expands",
    "gain",
    "gains",
    "growth",
    "improves",
    "improving",
    "optimistic",
    "outperform",
    "partnership",
    "profit",
    "profits",
    "raises",
    "record",
    "rebound",
    "recovery",
    "strong",
    "surge",
    "surges",
    "upside",
    "wins",
}

NEGATIVE_TERMS = {
    "bearish",
    "cut",
    "cuts",
    "decline",
    "declines",
    "downgrade",
    "downgrades",
    "fall",
    "falls",
    "fraud",
    "investigation",
    "lawsuit",
    "loss",
    "losses",
    "miss",
    "misses",
    "probe",
    "recall",
    "recession",
    "risk",
    "risks",
    "selloff",
    "slump",
    "warning",
    "weak",
}

POSITIVE_PHRASES = (
    "beats expectations",
    "beat expectations",
    "raises guidance",
    "strong demand",
    "record revenue",
    "profit forecast raised",
)

NEGATIVE_PHRASES = (
    "cuts guidance",
    "cut guidance",
    "misses expectations",
    "missed expectations",
    "profit warning",
    "demand weakens",
)


def normalize_headlines(headlines: list[str], *, limit: int = 8) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for headline in headlines:
        cleaned = " ".join(str(headline).strip().split())
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def score_headlines(headlines: list[str]) -> float | None:
    cleaned = normalize_headlines(headlines, limit=24)
    if not cleaned:
        return None

    scores = [_headline_score(headline) for headline in cleaned]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 6)


def _headline_score(headline: str) -> float:
    lowered = headline.lower()
    token_score = 0
    for token in re.findall(r"[a-z']+", lowered):
        if token in POSITIVE_TERMS:
            token_score += 1
        elif token in NEGATIVE_TERMS:
            token_score -= 1

    phrase_score = 0
    for phrase in POSITIVE_PHRASES:
        if phrase in lowered:
            phrase_score += 2
    for phrase in NEGATIVE_PHRASES:
        if phrase in lowered:
            phrase_score -= 2

    raw = token_score + phrase_score
    if raw == 0:
        return 0.0

    # Keep the score bounded while still rewarding consistent wording.
    normalized = raw / max(2.5, math.sqrt(len(lowered.split())))
    return max(-1.0, min(1.0, round(normalized, 6)))
