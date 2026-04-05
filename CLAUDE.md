# FinPilot Repo Guide

This file is the current working guide for the repository. It is not an implementation prompt anymore.

## What FinPilot Is

FinPilot is a local-first investing lab:

- build agent teams
- backtest strategies against an always-visible benchmark
- review local audit history
- run paper trading by default
- optionally point Alpaca at live mode, with the decision left to the user

## Core Constraints

These are still active and should stay true in code:

1. API keys never belong in browser storage. They live in the backend `.env` only.
2. Local-first only. No telemetry, phone-home, or hosted analytics.
3. Data before LLM. Agents fetch hard numbers first and only then ask a model to interpret them.
4. LLM output must stay schema-validated before it can influence decisions.
5. Audit logging is local and append-only.
6. Paper mode is the default. The app can warn clearly about live mode, but it should not pretend to manage that decision for the user.
7. User-adjustable settings should stay editable through the Settings UI whenever practical.

## Current Product Direction

- Setup should be direct and honest. Do not label required integrations as "safe to skip" if they are actually needed for a workflow.
- The top-level red research disclaimer banner was intentionally removed from the UI.
- Completing setup should move the user forward cleanly instead of leaving them stranded.
- Notifications in the UI are browser-focused. Email and Slack are not part of the active UI surface.
- Trading permissions control confirmation behavior only. They do not act as a live-trading gate.

## Stack

- Backend: FastAPI, SQLite, Pydantic
- Frontend: Vite, React, TypeScript, Zustand, Tailwind
- Python package manager: `uv`
- Node package manager: `pnpm`

## Important Paths

### Backend

- `backend/main.py`: FastAPI entrypoint
- `backend/api/routes/`: API routes
- `backend/agents/`: analysis, debate, and decision logic
- `backend/backtester/`: backtest engine and artifacts
- `backend/security/`: sanitization, validation, audit logging, secrets helpers
- `backend/settings/user_settings.py`: runtime user settings model
- `backend/tests/`: backend test suite

### Frontend

- `frontend/src/pages/`: app pages
- `frontend/src/components/setup/`: onboarding flow
- `frontend/src/components/strategy/`: team builder and team display
- `frontend/src/components/settings/`: editable settings sections
- `frontend/src/components/trading/`: trading status, notice, kill switch
- `frontend/src/stores/`: Zustand stores
- `frontend/src/api/`: client and shared TS types

## Current Behavior Notes

- Strategy team generation currently goes through `backend/llm/strategy_builder.py`.
- Settings are editable in-app and persist through the backend settings route.
- Trading shows responsibility warnings for live mode instead of staged unlock gates.
- Browser notifications are the only notification channel exposed in the UI.
- Some backend and docs files may still reference older live-unlock language; update them when touching adjacent code.

## Local Commands

### Setup

```bash
./setup.sh
```

### Backend tests

```bash
python3 -m pytest backend/tests -q
```

### Frontend build

```bash
cd frontend
pnpm build
```

### Frontend dev

```bash
cd frontend
pnpm dev --host
```

### Backend dev

```bash
python3 -m backend.main
```

## Editing Guidance

- Prefer updating the repo to match current product decisions rather than preserving outdated prompt/spec language.
- Keep docs concise and operational.
- If you remove a product concept from the UI, also remove stale supporting code and copy where practical.
- When changing API shapes, update both:
  - `frontend/src/api/types.ts`
  - the matching backend route payload/response
- When changing settings behavior, verify:
  - the frontend editor
  - the store/hook wiring
  - the backend PATCH route

## Verification Expectations

After meaningful changes, try to run:

```bash
python3 -m pytest backend/tests -q
cd frontend && pnpm build
```

If something is intentionally left incomplete, document that clearly rather than hiding it in product copy.

## Strategy Builder Architecture

- The strategy section is a real multi-turn local conversation system.
- Draft state is persisted as `StrategyConversation`, `StrategyMessage`, `StrategyPreferences`, and `StrategyDraft`.
- Draft output is not executable.
- Executable behavior comes only from `CompiledTeam`.
- `AgentTeamConfig` is legacy compatibility only and must not be treated as the canonical executable schema.
- Saved teams are immutable `TeamVersion` records; editing a team creates a new version.
- v1 custom teams are limited to the trusted executable catalog:
  - analysis agents: `fundamentals`, `technicals`, `sentiment`, `macro`, `value`, `momentum`, `growth`
  - required decision agents: `risk_manager`, `portfolio_manager`

## Builder Safety Contract

The model may generate:

- team composition from the trusted catalog
- per-agent weights
- sector exclusions
- risk level and time horizon
- rationale
- follow-up questions
- bounded per-agent modifiers

The model must never generate:

- new executable agent classes
- new data adapters
- new indicators
- new tools
- new broker actions
- raw freeform executable prompt text

All executable behavior must be compiled and validated by deterministic Python before use.

## PromptPack System

- Prompt packs are versioned local assets.
- Each analysis agent has a fixed base prompt pack, named variants, and bounded modifier slots.
- Runtime prompt assembly uses: base prompt pack + selected variant + validated modifiers.
- User text and raw model text must never be persisted as executable runtime instructions.
- Prompt packs may change framing and emphasis, but they may not expand data access, tools, or broker permissions.

## Compiler Pipeline

The only valid builder pipeline is:

1. conversation
2. extracted preferences
3. model-assisted draft
4. deterministic compile
5. validation
6. saved immutable team version

Compiler responsibilities:

- enforce trusted catalog membership
- enforce required decision agents
- validate and clamp weights
- validate prompt-pack variants and modifiers
- validate owned-source subsets against each agent ownership map
- fill defaults for missing prompt packs and overrides
- produce `CompiledTeam`

## Execution Resolution Rules

Team resolution precedence is fixed:

1. explicit `team_config`
2. explicit `team_id` and optional `version_number`
3. globally selected active team
4. premade default team

Global settings remain runtime defaults. Team-specific overrides may narrow or specialize behavior for one run, but they may not expand broker permissions, bypass guardrails, or add new tools/actions.

Every analyze, paper, live, and backtest run must freeze an `ExecutionSnapshot` before any agent executes.

## Backtesting Integrity

Backtests use the same core agent pipeline as live and paper modes. Only the data boundary and execution environment change.

- `backtest_strict` is the default truthful mode.
- `backtest_strict` requires `as_of_datetime`.
- No unconstrained “current” or “latest” semantics are allowed in strict mode.
- In strict mode, “latest” means latest available as of simulated time only.
- Features that cannot be supported honestly in strict mode must be excluded or explicitly lagged and labeled.
- `backtest_experimental` may relax temporal integrity rules, but it must stay clearly labeled and cannot be the default headline performance view.

## Artifact And Audit Requirements

Every run artifact must store:

- effective compiled team config
- prompt pack ids and versions
- provider and model
- settings hash
- team hash
- temporal boundary
- benchmark symbol
- transaction cost model
- any lagged or excluded temporal features

Audit log entries are required for:

- conversation start and compile
- team save and team selection
- execution snapshot creation
- agent signal generation
- portfolio decision output
- backtest completion
