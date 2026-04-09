# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-04-08

### Added

- Local setup wizard for AI providers (Ollama, OpenAI, Anthropic), Alpaca broker, and optional data sources (yfinance, Finnhub, MarketAux, GDELT, SEC EDGAR)
- Agent team system with premade catalog (18 teams) and custom team builder
- Strategy conversation system with draft extraction, deterministic compiler, and immutable `TeamVersion` records
- Universe backtester with strict and experimental modes, real SPY benchmark, and side-by-side team comparison
- Paper trading with server-side guardrails, immutable audit log, and kill-switch flow
- Local portfolio and audit views derived from stored fills and artifacts
- Input sanitizer (13 injection patterns) and output validator (Pydantic schema enforcement on all LLM output)
- CORS restricted to localhost/127.0.0.1 only; API keys backend-only, never in browser storage
- `scripts/smoke_test.sh` for lightweight backend boot verification
- Playwright E2E first-run test suite as a release gate

### Fixed

- `BacktestPanel.tsx`: universe_id ternary bug where both branches returned `"current_sp500"` instead of `null` for non-S&P-500 modes
- `agents.py`: fail-open mode default changed from `"live"` to `"paper"` for unrecognized mode strings

### Security

- Added `max_length=16384` to custom system prompt fields to prevent unbounded token budget exhaustion
- CI now enforces pnpm lockfile (removed `--frozen-lockfile=false`)
- CI dependency audit jobs added for Python (`pip-audit`) and JavaScript (`pnpm audit`)

### Known Limits

- Universe backtester scores only `technicals`, `momentum`, and `macro` agent families in strict mode. `fundamentals`, `value`, `growth`, and `sentiment` require point-in-time data support before they can be included honestly.
- Agent-level accuracy attribution is hidden in the UI pending honest computation from stored outcomes.
- Notification delivery channels (email, Slack) are not wired up; browser notifications only.
