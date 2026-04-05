# Architecture

FinPilot is split into a local FastAPI backend and a Vite/React frontend.

## Backend flow

1. Settings load from `.env` for startup defaults.
2. Runtime user settings persist in SQLite and can be patched from the UI.
3. Strategy conversations persist locally and compile into immutable `TeamVersion` records.
4. Executable behavior comes from `CompiledTeam`, prompt-pack variants, and validated bounded modifiers.
5. Analysis agents follow `fetch -> build grounded context -> analyze`.
6. Debate and risk nodes review the signals before a portfolio action is proposed.
7. Analyze and backtest runs first resolve a single `ExecutionSnapshot` with team config, prompt-pack versions, provider/model, and temporal boundary.
8. Backtests always produce an artifact with config, cost model, benchmark, data hash, and execution snapshot metadata.
9. Audit events are written to both SQLite and a flat log file.

## Frontend flow

- Setup shows backend key status, source posture, plan detection, and risk acknowledgment.
- Strategy runs a real multi-turn team builder, shows the compiled draft, compares it with the premade default team, and saves immutable versions.
- Backtest runs against the currently selected team and shows benchmarked results, execution snapshot context, and signal transparency.
- Trading exposes guardrails, permission level, live unlock gates, and the kill switch.
- Portfolio and audit stay local-only.

## Safety constraints

- Secrets never live in frontend state.
- External text must be sanitized before any LLM use.
- Schema validation gates model output before downstream actions.
- Guardrails clamp unsafe values server-side.
