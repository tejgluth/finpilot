# Contributing

## Development flow
1. Run `./setup.sh` to install dependencies and prepare local data directories.
2. Keep secrets in `.env` only.
3. Prefer paper trading and backtests while iterating on behavior.
4. Add or update tests for any safety-sensitive change.

## Standards
- Python: `uv`
- Frontend: `pnpm`
- Keep analytics local-only
- Never send telemetry
- Preserve the data-before-LLM pipeline

## Pull request checklist
- [ ] No secrets in code or frontend bundles
- [ ] Audit logging preserved
- [ ] Guardrails still enforced server-side
- [ ] Tests added or updated
- [ ] Risk disclosures remain visible in the UI
# Contributing

Thanks for helping improve FinPilot.

## Development Rules

- Python uses `uv`.
- Frontend packages use `pnpm`.
- Do not add telemetry.
- Do not move secrets into the frontend.
- Keep paper trading as the default path.
- Preserve the data-before-LLM architecture.

## Suggested Workflow

1. Run `./setup.sh`.
2. Make focused changes.
3. Add or update tests for behavior that changed.
4. Run the backend test suite before opening a PR.

## Style

- Prefer small, typed helpers over hidden magic.
- Keep comments concise and explain intent, not syntax.
- When touching agents, preserve the fetch -> context -> analyze pipeline.

## Pull Requests

Include:

- summary of behavioral changes
- risk or safety impact
- tests run
- screenshots if UI changed materially
