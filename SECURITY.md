# Security Policy

## Threat Model

FinPilot assumes a local single-user deployment with optional access to external market-data and brokerage APIs. The highest-risk assets are:

- brokerage credentials
- AI provider API keys
- historical artifacts and audit logs
- live-trading permissions and guardrail settings

## Primary Risks

- Secret leakage through logs, frontend bundles, or accidental commits
- Prompt injection from news, SEC filings, Reddit posts, or user-supplied strategy text
- Treating model output as trusted instructions instead of validated structured data
- Unauthorized live trading through misconfiguration or bypassed guardrails
- Tampering with audit records or backtest artifacts

## Controls In This Repository

- Secrets are read from `.env` on the backend only.
- External text is sanitized before LLM use.
- LLM outputs are parsed as JSON and validated against strict schemas.
- Guardrails clamp unsafe settings server-side even if a client is manipulated.
- Paper trading is the default.
- Live trading stays locked behind four backend-enforced gates.
- Audit events are append-only and mirrored to both SQLite and a flat log file.
- There is no telemetry or phone-home analytics in the app.

## Secure Development Expectations

- Never commit `.env`, private keys, or broker credentials.
- Do not copy provider keys into frontend state, localStorage, or cookies.
- Do not add telemetry or third-party analytics.
- Do not reintroduce placeholder market data, synthetic equity curves, or fabricated analytics.
- Treat all external text as untrusted input.

## Reporting Vulnerabilities

If you discover a security issue, do not publish exploit details in a public issue first.

Send a private report that includes:

- affected version or commit
- reproduction steps
- expected impact
- suggested mitigation if known

Rotate any affected credentials immediately if secret exposure is suspected.
