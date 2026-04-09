# FinPilot Risk Disclosure

Last updated: April 3, 2026

## What FinPilot is
A local, open-source research and automation tool. It is a personal research lab,
not a licensed investment adviser, broker-dealer, or regulated financial service.

## What FinPilot is NOT
- Not investment advice
- Not a guarantee of any return or performance
- Not regulated by the SEC, FINRA, or any financial authority
- Not a replacement for professional financial guidance

## Risks you must understand

**Market risk:** All investing involves risk of loss, including total loss of principal.

**Backtesting risk:** Past performance does not predict future results. FinPilot models
transaction costs and shows benchmark comparison, but real results will differ.

**AI and hallucination risk:** Despite grounding and validation safeguards, agents can
produce incorrect outputs. All agent decisions should be reviewed critically.

**Live trading automation risk:** In Full Auto mode, real money is spent automatically.
Circuit breakers reduce but do not eliminate risk.

**Prompt injection risk:** External content is sanitized but novel injection techniques
could potentially affect agent behavior. Monitor decisions for anomalies.

**Technical risk:** Bugs, API outages, network failures, or data errors can cause
unexpected behavior. Maintain the ability to manually intervene at all times.

**Credential risk:** If your API keys are compromised, an attacker could trade on your
brokerage account. Never commit your `.env` file to a public repository.

## Your responsibilities
1. You are responsible for all trades executed by this system, even in Full Auto mode.
2. Paper trade and backtest before using real money.
3. Start with Full Manual and graduate up slowly.
4. Monitor the system actively during live trading.
5. Use the kill switch immediately if anything seems wrong.
6. Keep your API keys secure.
7. Consult a licensed financial professional for personalized advice.

*By using FinPilot's live trading features, you confirm that you have read,
understood, and accepted all risks described above.*
