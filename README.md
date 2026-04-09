# FinPilot

Your local-first AI investing lab. Design, test, and run strategies honestly — paper trade first, always.

FinPilot is a local-only investing workspace for:

- building and saving agent teams
- backtesting portfolio selection against a real SPY benchmark
- paper trading through a truthful local or broker-backed execution path
- reviewing immutable local audit history

## What Works Now

- Backend-only secret handling with `.env` storage
- Local setup flow for AI providers, Alpaca, and optional data sources
- Truthful data adapters that return real provider data or explicit empty payloads
- Universe backtesting with:
  - single-ticker mode
  - dated CSV universe snapshots for strict runs
  - current S&P 500 membership for experimental runs
  - real historical bars
  - real SPY benchmark comparison
  - configurable rebalance cadence, selection count, max positions, and weighting
  - side-by-side team comparison over the same window
- Paper trading with:
  - server-side guardrails
  - immutable audit logging
  - kill-switch cancellation flow
  - staged live-unlock enforcement
- Local portfolio and audit views derived from stored fills and artifacts

## Important Current Limits

- The universe backtester only scores factor families that are honestly supported with historical market data today:
  - `technicals`
  - `momentum`
  - `macro`
- These agent families are excluded from bulk universe scoring until point-in-time support is added:
  - `fundamentals`
  - `value`
  - `growth`
  - `sentiment`
- Agent-level accuracy attribution is intentionally hidden in the UI until it can be computed honestly from stored outcomes.
- Notification settings are hidden from the main Settings page because delivery channels are not wired up yet.

## Principles

- Local-first analytics only. No telemetry, phone-home, or hosted dashboards.
- Data before LLM. Agents fetch numbers first and only then ask the model to interpret them.
- Paper trading is the default. Live trading stays behind explicit unlock gates.
- Unsupported data paths fail closed. If a provider cannot answer honestly, FinPilot returns `UNAVAILABLE` or disables that factor.
- Every backtest stores config, cost model, execution snapshot, benchmark, and artifact hash.

## Prerequisites

- **Python ≥ 3.11** — `python3 --version` to check
- **Node.js ≥ 18** — `node --version` to check
- `uv` and `pnpm` are installed automatically by `setup.sh` if missing

## Quick Start

1. Clone the repo and run `./setup.sh`
2. The script copies `.env.example` → `.env` on first run and opens the browser
3. Add your API keys through the in-browser setup wizard
4. Re-run `./setup.sh` to restart after adding keys

The setup script installs `uv` and `pnpm`, validates configuration, creates local data folders, starts the backend, and opens the frontend.

## Verification

```bash
# Backend tests
uv run pytest backend/tests

# Lint
uv run ruff check backend

# Frontend typecheck
pnpm --dir frontend typecheck

# Frontend build
pnpm --dir frontend build

# Smoke test (backend boot check)
bash scripts/smoke_test.sh
```

## Safety

- API keys never belong in the browser.
- FinPilot is not investment advice.
- LLM output is schema-validated before it can influence trading behavior.
- Every decision and trade event is written to the local immutable audit log.

Read [RISK_DISCLOSURE.md](RISK_DISCLOSURE.md) before enabling any live trading feature.
