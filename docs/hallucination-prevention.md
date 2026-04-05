# Hallucination Prevention

FinPilot uses a strict grounding strategy.

## Core rule

Data before LLM.

## Pipeline

1. Fetch real data into typed structures.
2. Build a context that labels every value with source and age.
3. Mark missing values as unavailable instead of estimating.
4. Constrain analysis output to JSON schemas.
5. Apply deterministic confidence penalties after model output.

## Extra defenses

- Debate nodes challenge weak or inconsistent signals.
- Risk checks can block trades when confidence is too low.
- Transparency UI exposes coverage, data freshness, and cited fields.
