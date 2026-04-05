# Security Model

## Secret handling

- API keys are backend-only.
- Secret-like fields are masked before returning status summaries.
- `.env` is ignored by git.

## Prompt injection handling

- External content is sanitized and quarantine-framed.
- The LLM is told that external text is data, not instructions.

## Output handling

- LLM responses must parse as JSON.
- Pydantic schemas validate trading-adjacent responses.
- Guardrails and permission checks still run after validation.

## Auditability

- Startup, shutdown, signal, backtest, permission, and kill switch events are logged locally.
