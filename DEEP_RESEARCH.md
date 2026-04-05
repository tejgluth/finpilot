# Pre-build research dossier for a local-first AI-assisted investing system

## Executive summary and scope

This dossier evaluates a proposed **local-first**, **browser-based** investing “system” distributed via public source control, where users install locally, provide their own AI model keys and brokerage/data keys, assemble dynamic agent teams, run parallel backtests, paper trade first, and only then (optionally) unlock guarded live trading—with a “truth-first” positioning, accessibility emphasis, low setup friction, and an explicit objective of viral adoption via entity["company","GitHub","code hosting platform"]. fileciteturn0file1

The core idea is technically feasible as a **local orchestration + plugin adapters** architecture, and it aligns well with current open-source adoption patterns (fast onboarding, reproducible demos, and verifiable releases). The two hard constraints that dominate “go/no-go” are:

- **Regulatory/claims risk** if you present backtests, “expected returns,” projections, or marketing that looks like personalized advice or promises—especially once you add “one-click live trading.” The U.S. investment-adviser marketing regime treats “hypothetical performance” and the substantiation of material claims seriously, and recordkeeping obligations attach to many marketing artifacts and workflows. citeturn20search19turn20search4  
- **Security and trust** when your system handles brokerage credentials, executes trades, and uses LLM “agents” exposed to untrusted inputs (prompt injection, poisoned data, malicious plugins). The OWASP LLM Top 10 makes these risks explicit (prompt injection, insecure output handling, model DoS, supply-chain vulnerabilities, etc.). citeturn19search0turn4search25

### What this report explicitly covers

You requested the following dimensions; each is addressed somewhere in the report (facts are cited; inferences and unknowns are labeled):

- **Market map and competitor matrix** (local-first vs hosted, AI, trading automation, open-source vs proprietary)  
- **Technical feasibility** (local orchestration, model providers and local LLM options, backtesting, parallel runs, laptop limits)  
- **Data & brokerage due diligence** (paper/live APIs, rate limits, cost, licensing, key management, “production suitability”)  
- **Strategy evaluation & validation framework** (benchmarks, walk-forward, transaction costs, overfitting, hallucinations, drift, paper-vs-live divergence)  
- **Regulatory/legal** (U.S.-first: adviser/robo-adviser style risk, marketing claims, recordkeeping, open-source vs hosted differences)  
- **Security/privacy/trust** (threat model, secret storage, prompt injection, supply-chain, signed releases, top risks and mitigations)  
- **Live trading risk controls and staged unlock**  
- **UX/accessibility/trust design** (onboarding, plain-language strategy creation, core visualizations/metrics, wireframe-level guidance)  
- **Open-source and GitHub strategy** (README, license, CI, reproducible benchmarks, provenance attestations, release checklist)  
- **Go-to-market + community growth** (channels, narrative, 90-day plan)  
- **Business models and long-term options**  
- **Phased roadmap, pre-build checklist, decision matrix, final recommendation + next-week plan**

### Evidence labels and readiness flags used below

- **[FACT]** = directly supported by cited sources  
- **[INFERENCE]** = reasoned conclusion; test/verify during discovery  
- **[OPEN]** = must be decided or validated with targeted experiments/legal review  

Readiness flags used in tables and recommendations:

- **FOUNDATION** = good long-term base  
- **MVP** = acceptable for an initial release  
- **EXP** = OK for experimentation, risky for production  
- **AVOID** = strongly discouraged

## Market map and competitor matrix

### Market map

The user-facing experience you’re proposing—**“describe your strategy in plain language → agents propose, backtest, and explain → paper trade → guarded live trading”**—overlaps with several mature categories:

1. **Robo-advisors / automated portfolio management**: user answers questions, platform manages portfolios automatically. Representative examples include entity["company","Betterment","robo advisor us"], entity["company","Wealthfront","robo advisor us"], entity["company","Charles Schwab","brokerage firm us"] Intelligent Portfolios, and entity["company","Vanguard","asset manager us"] Digital Advisor. citeturn21search0turn21search5turn21search2turn21search3  
2. **No-code / AI-assisted strategy builders with execution**: entity["company","Composer.trade","automated trading platform"] explicitly markets AI-assisted algorithm creation, backtesting, and execution. citeturn14search3turn14search29  
3. **Trading automation bridges** (alerts → broker orders): platforms that transform charting alerts/webhooks into trades. Webhook-based alerting is a mainstream integration primitive. citeturn15search12turn15search24turn15search34turn15search35  
4. **Open-source trading/bot frameworks** (often crypto-heavy) that already encode best practices like “paper/dry-run first”: e.g., Freqtrade explicitly supports dry-run and backtesting. citeturn15search1turn15search10  
5. **Open-source research/data platforms** that emphasize “bring your own data keys”: entity["company","OpenBB","financial data platform company"] positions its open platform as a “connect once, consume everywhere” data integration layer. citeturn14search0turn14search1  
6. **Backtesting-focused tools** (web or library form): e.g., Portfolio Visualizer offers web backtests for portfolios and asset allocations; tools like testfol.io emphasize sharable backtests. citeturn14search6turn14search2turn14search28

### Competitor matrix and “why you still might win”

The table below highlights **how users solve the “research → backtest → automate” workflow today**, and what that implies for your differentiation. (This is comprehensive across the main overlapping categories; it is not mathematically exhaustive of every fintech/trading product worldwide.)

| Category | Representative product | What it does (as marketed) | Local-first by default | Automation/execution | Implication for your system |
|---|---|---|---|---|---|
| Robo-advisor | Betterment | “Automated investing” with goal-based portfolios and management; positions itself as a fiduciary. citeturn21search0turn21search4 | No | Yes (managed) | Users who want “set-and-forget” already have strong options; you win only if you offer transparency, customization, or local privacy. |
| Robo-advisor | Wealthfront | Automated, diversified investing; markets “we do the busywork,” automation manages trading. citeturn21search1turn21search5 | No | Yes (managed) | Competes mainly on convenience and trust; your “truth-first” angle must counter “why not just use this.” |
| Robo-advisor | Schwab Intelligent Portfolios | Automated investing with automatic rebalancing; includes minimums, positioning around diversified portfolios. citeturn21search2turn21search6 | No | Yes (managed) | Your system is best framed as **DIY + transparency tooling**, not a replacement robo-advisor. |
| Robo-advisor | Vanguard Digital Advisor | Automated investing service; markets low minimums and fee structure details. citeturn21search3turn21search27 | No | Yes (managed) | Competes on “trusted brand + simplicity,” not on power-user customization. |
| AI/no-code strategy execution | Composer.trade | Build trading algorithms with AI, backtest, and execute; includes pricing tiers. citeturn14search3turn14search29 | No | Yes | This is your closest “UX thesis competitor.” Your edge must be: local-first, open source/verifiable, and stricter safety/guardrails. |
| Charting/alerts → execution bridge | TradingView webhooks | Webhooks post alert payloads to a URL for automation. citeturn15search12 | N/A | Indirect | Many traders already trust alert pipelines; your system can integrate here as an input (signals) rather than compete head-on. |
| Alert-to-broker automation | TradersPost | Automate TradingView strategies by receiving webhook alerts and sending orders to brokers. citeturn15search24 | No | Yes | Competes on “turnkey automation.” You win if you provide **auditable reasoning + reproducible evaluation** instead of opaque execution. |
| Alert-to-broker automation | SignalStack | Captures TradingView alerts and converts them into orders at connected broker/exchange. citeturn15search34 | No | Yes | Same lesson: automation is commoditized; trust controls and transparency become differentiators. |
| Automation platform | Option Alpha webhooks | Uses webhooks to trigger an automation from TradingView alerts. citeturn15search35 | No | Yes | Your opportunity: **strategy research + evaluation** rather than just automation. |
| Open-source research/data integration | OpenBB | Open source platform for integrating data sources into downstream apps (AI copilots, dashboards, MCP servers). citeturn14search0 | Can be | Not core | Your “local-first, BYOK” posture fits here; you may integrate rather than compete. |
| Web backtesting | Portfolio Visualizer | Online analytics for backtesting, Monte Carlo, tactical allocation, etc. citeturn14search6turn14search2 | No | No | Strong for *portfolio-level* exploration; you differentiate via **agentic assistance + execution pipeline**. |
| Lightweight sharable backtests | testfol.io | Backtests with benchmark comparison and sharable links. citeturn14search28 | No | No | Indicates demand for **shareable, reproducible backtests**—a key GitHub growth lever for you. |
| Open-source crypto trading bot | Freqtrade | Backtesting + dry-run + automation; warns about distorted backtests. citeturn15search1turn15search22 | Yes | Yes | Their “dry-run first” posture is a norm you should mirror for equities: paper trading required. |
| Open-source crypto bot framework | Hummingbot | Open-source framework to design and deploy automated strategies across many venues. citeturn15search2turn15search5 | Yes | Yes | Shows community appetite for “run locally” + modular connectors, but also highlights security/ops burdens. |
| Broker + trading API | Alpaca | Provides trading + market data APIs; has explicit API throttling guidance. citeturn6search0turn6search13 | N/A | Yes (API) | A common “first broker” for devs; good for MVP but needs careful guardrails and rate-limit handling. |
| Broker API | Tradier | Brokerage API with sandbox base URL for paper trading; documents rate limiting. citeturn6search12turn6search33turn6search2 | N/A | Yes (API) | Attractive for options use cases; sandbox mode aligns with your staged unlock. |
| Broker API | Interactive Brokers | Client Portal/Web API describes HTTP endpoints + websocket access; docs mention local/authorization mechanics and sessions. citeturn6search10turn6search14 | N/A | Yes (API) | Broad instrument coverage, but higher friction and more operational complexity than “starter brokers.” |
| Broker API | Schwab Trader API | Developer portal supports app registration, OAuth guidance, sandbox testing. citeturn7search3turn7search14turn7search5 | N/A | Yes (API) | Huge user base potential, but token lifecycle and approval friction are key risks (see due diligence). |

### Strategic positioning that survives competition

A credible “why you” needs to be **non-overlapping** with what these incumbents sell. The strongest positioning hypothesis is:

**“Truth-first, local-first, auditable research + safety gating”**  
- “Truth-first” means: the system treats uncertainty as first-class, distinguishes *facts vs assumptions*, forces cost/slippage modeling, and makes it hard to accidentally lie with backtests.  
- “Local-first” means: users can run sensitive workflows without sending brokerage credentials or private portfolio data to a hosted service (still respecting that AI calls may go to a cloud model provider unless local LLM is used). fileciteturn0file1  
- “Auditable” means: deterministic configs, pinned dependencies, saved prompts/tools/data snapshots, reproducible backtests, and verifiable releases.

If you pursue “go viral on GitHub,” the most reliable open-source viral loop historically is: **one-command install + impressive demo + reproducible benchmark + clear trust story**. OpenBB’s history shows how open-source finance products can surge quickly when the story is compelling and friction is low. citeturn14search23  

## System architecture and technical feasibility

### Technical feasibility summary

- **Local orchestration for multi-agent workflows** is feasible with existing agent-graph orchestration libraries designed for long-running stateful processes and human-in-the-loop checkpoints. citeturn16search3turn16search24  
- A browser UI can be served locally using common Python web app frameworks (fast prototyping via Streamlit) or more structured API-first approaches (FastAPI) that auto-generate API documentation. citeturn16search2turn16search1  
- **Parallel backtesting** is feasible on a laptop for many medium-frequency strategies if you: cache data locally, vectorize computations where possible, and cap the combinatorial explosion from agent-generated variants. (This is an engineering constraint, not a fundamental blocker.)  
- Supporting **multiple LLM providers + local LLMs** is feasible through an adapter interface; local LLM runtimes like Ollama or llama.cpp reduce privacy and key-handling issues at the cost of local compute and disk. citeturn17search8turn17search1  

### Proposed architecture (local-first, plugin-based)

```mermaid
flowchart LR
  UI[Local Browser UI] --> API[Local API Server]
  API --> ORCH[Agent Orchestrator]
  ORCH -->|create/modify| TEAM[Dynamic Agent Team]
  TEAM --> TOOLS[Tool Router]
  TOOLS --> DATA[Data Adapters\n(prices, fundamentals, news)]
  TOOLS --> BT[Backtest Engine]
  TOOLS --> PAPER[Paper Trading Adapter]
  PAPER --> BROKER[(Broker API Sandbox)]
  ORCH --> AUDIT[(Local Audit Log + Runs DB)]
  API --> VAULT[(Local Secrets Store)]
  ORCH -->|optional| LIVE[Guarded Live Trading]
  LIVE --> BROKERLIVE[(Broker API Live)]
  DATA --> CACHE[(Local Data Cache)]
  BT --> RESULTS[Metrics + Charts + Reports]
  RESULTS --> UI
```

Key design choice: treat everything external (LLM calls, broker calls, data calls) as **adapters** behind strict interfaces, with full logging and replayable runs. This is the single biggest enabler of “truth-first.”

### Laptop vs cloud constraints (what will actually bottleneck)

**Bottleneck class A: LLM calls**  
- Agent-team creation plus iterative strategy testing can blow up into many calls. For correctness and usability, you’ll need: caching, prompt+tool-call budgeting, and concurrency limits; otherwise evaluations become slow and expensive.  
- If you support local LLMs through Ollama, note that model storage can be “tens to hundreds of GB,” which affects onboarding expectations for non-technical users. citeturn17search8  

**Bottleneck class B: data throughput and rate limits**  
- Broker/data APIs throttle; you must implement backoff, caching, and in many cases batch endpoints. Alpaca documents throttling around **200 requests/minute per account**, with HTTP 429 responses when exceeded. citeturn6search0turn6search31  
- The SEC’s EDGAR guidance caps automated access at **10 requests/second** for fair access, and it may temporarily limit IPs that exceed the threshold. citeturn20search2turn20search5  

**Bottleneck class C: parallel backtesting explosion**  
- “LLM generates variants” + “parallel backtest each variant” can become an uncontrolled combinatorial search. Your system needs a **search policy** (budgeted exploration) and a minimum evidence standard before variants graduate to paper trading.

### UX-informing UI inspiration (not a wireframe)

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["algorithmic trading dashboard UI backtesting metrics","portfolio backtesting visualization UI","paper trading dashboard interface","risk controls trading app UI"],"num_per_query":1}

### MVP stack recommendation (prioritized)

The following are implementation recommendations (not claims about any single tool’s superiority), annotated with readiness:

- **FOUNDATION**: Local API + local UI served from the same process (minimize moving parts). Streamlit is explicitly designed to turn Python scripts into shareable web apps quickly, which aligns with low setup friction for MVP demos. citeturn16search2turn16search11  
- **FOUNDATION**: An API-first core (FastAPI) once you outgrow prototype UI: FastAPI emphasizes type-driven validation and auto docs (Swagger UI, ReDoc), which helps with plugin ecosystems and contributor onboarding. citeturn16search1  
- **MVP**: Agent orchestration using a graph model with explicit state/human-in-the-loop hooks, because you need **guarded live trading** and staged unlocks. LangGraph explicitly positions itself around durable execution, streaming, and human-in-the-loop. citeturn16search3turn16search0  
- **EXP**: “Fully autonomous agent that can trade live by default.” This is where prompt injection + hallucination + API misfires become catastrophic. Your staging must make this hard.

## Data and brokerage due diligence

### Data: the hidden “business model” of trading software

In practice, your system’s reliability is gated by data access, licensing, and rate limits more than by code quality. Two facts dominate:

1. **Redistribution and “non-display use” restrictions are common.** As an example, Massive’s market data terms (in a Polygon-branded PDF) state market data is licensed for personal, non-business use in certain contexts and includes explicit restrictions around redistribution and derived works. citeturn22view0turn22view1  
2. **Even free public data sources impose fair-use limits.** EDGAR’s fair access policy explicitly caps request rates and reserves the right to rate-limit automated users. citeturn20search5turn20search2  

**Implication:** you should architect a **data provider abstraction** from day one, and label every feature that depends on third-party data terms (news, sentiment, certain fundamentals) as **conditional**.

### Data provider comparison (licensed vs experimentation)

| Provider | Product positioning | Rate limits and throttling (as documented) | Licensing / suitability | Status |
|---|---|---|---|---|
| entity["company","Massive","market data api provider"] (formerly Polygon.io) | Pricing page describes free and paid tiers; blog confirms rebrand and parallel API domains. citeturn11search8turn13search0turn13search17 | Knowledge base: free tier 5 requests/min; paid customers “unlimited API requests.” citeturn11search16 | Market data terms include strong use restrictions (display-only language and derived-works restrictions). citeturn22view0turn22view1 | FOUNDATION if you constrain usage and terms (especially for open-source distribution). |
| entity["company","Tiingo","market data api provider"] | Pricing page: simple monthly pricing; terms note limits are approximations and can change. citeturn10search6turn10search2 | Rate limits referenced via pricing; terms explicitly reserve right to alter limits. citeturn10search2turn10search29 | Terms emphasize posted limits are approximations; suitability depends on your use and redistribution needs. citeturn10search2 | MVP/FOUNDATION if you treat as BYOK, cache locally, and clearly communicate terms. |
| entity["company","Finnhub","financial data api provider"] | Pricing pages describe personal plans; docs publish rate limiting behavior. citeturn10search3turn10search7 | Docs: returning 429 when exceeded; also “30 API calls/second limit” on top of plan limits. citeturn10search7 | Often marketed for “personal use” tiers; check ToS for redistribution if you plan to share outputs widely. citeturn10search3 | MVP if used for personal research; production suitability depends on licensing + cost planning. |
| entity["company","Alpha Vantage","financial data api provider"] | Official support states free tier “up to 25 requests per day”; premium increases limits. citeturn10search5turn10search21 | Free tier is extremely restrictive for agentic workflows; will cause frequent throttling. citeturn10search5 | Usable for demos; high risk for serious backtesting or multi-symbol workflows. citeturn10search5 | EXP for core workflows; MVP only for narrow demos. |
| Twelve Data | Terms define rate limits by plan; pricing pages describe business plans and credits. citeturn11search3turn11search18 | Rate limits depend on plan; enforce 429 behavior. citeturn11search3 | Viable if your user base is willing to BYOK; business use often requires business plans. citeturn11search18 | MVP/FOUNDATION if you make it optional and terms-aware. |
| SEC EDGAR | Official “fair access” max request rate 10/sec; designed for equitable access. citeturn20search5turn20search2 | 10 req/sec cap; rate-limiting when exceeded. citeturn20search2 | Great for fundamentals/filings ingestion if you build a polite downloader + cache. | FOUNDATION for fundamentals; not for real-time trading. |

### Broker API comparison and staged deployment design

| Broker/API | Paper trading support | Rate limits / operational notes | Key implications for a local-first tool | Status |
|---|---|---|---|---|
| entity["company","Alpaca Markets","brokerage api provider"] | Provides paper trading environment (commonly used by algorithmic traders). citeturn6search13 | Support doc states throttling around 200 requests/min per account; 429 on excess. citeturn6search0turn6search31 | Good “starter broker” for MVP; rate limits force caching and batching. | MVP/FOUNDATION (with strong risk controls). |
| entity["company","Tradier","brokerage api provider"] | FAQ: sandbox endpoints for paper trading (sandbox.tradier.com). citeturn6search12turn6search33 | Docs discuss rate limiting and recommend streaming instead of polling. citeturn6search2 | Attractive for options workflows; sandbox supports your “paper first” philosophy. | MVP/FOUNDATION for options-capable roadmap. |
| entity["company","Interactive Brokers","broker-dealer ibkr"] Client Portal/Web API | API supports trading functionality, market data, websockets; docs emphasize sessions/cookies and authorization mechanics. citeturn6search10turn6search14 | Higher complexity and more “ops-like” integration than starter brokers. citeturn6search14 | Best as an optional connector once core safety/observability is mature. | FOUNDATION (later), not MVP unless you target power users. |
| Schwab Trader API | Developer portal describes app creation, OAuth guides, sandbox testing. citeturn7search13turn7search5turn7search14 | Public docs emphasize OAuth flows; community wrappers report token lifetimes and friction, but treat specifics as validate-in-discovery. citeturn7search11turn9search2 | Large potential user base, but onboarding can require apps, approval, and token UX design. | MVP-optional; prioritize only if you can make onboarding smooth. |

### Key management: the “BYOK” paradox

Your plan depends on “users supply AI and broker keys,” but key handling can easily break trust:

- OpenAI’s key safety guidance explicitly warns: **never deploy keys in client-side environments like browsers** and avoid committing keys to repos; use environment variables. citeturn17search3turn17search7  
- This strengthens your local-first thesis: keep keys in OS-level keychain or local encrypted secret storage, and keep the browser UI a *client of the local backend*, not a place where secrets live.

**Recommendation (FOUNDATION):** enforce a “keys never enter the browser” invariant. The UI should never display raw keys after entry; the backend stores encrypted secrets and only exposes “connection health” and “last successful call” metadata.

## Strategy validation and evaluation framework

### Why most AI-generated strategies “work” in backtests and fail live

This is primarily due to failure modes that are well-known in systematic trading but amplified by LLM-driven iteration:

- **Overfitting / multiple comparisons**: If agents generate many variants and you select the best-looking curve, you are implicitly doing data mining unless you enforce out-of-sample discipline.  
- **Transaction cost blindness**: Even “small” slippage/fees can erase edge, especially in high-turnover strategies.  
- **Data leakage / lookahead**: LLM-written code can accidentally use future info or survivorship-biased universes if guardrails don’t detect it.  
- **Paper vs live divergence**: Fill logic, partial fills, market impact, routing, and broker behaviors differ; paper trading is necessary but not sufficient.

Freqtrade’s own docs warn that backtesting can be distorted and make strategies look much more profitable than reality. citeturn15search22  
Lumibot’s documentation explicitly recommends starting with paper trading first before live. citeturn15search6  

### The validation framework you should build before writing “strategy agents”

A “truth-first” product needs a **standard evaluation protocol** that every strategy—human- or agent-authored—must pass. The goal is not to guarantee profitability; it is to prevent self-deception.

**Core artifacts to persist for every run (FOUNDATION):**
- Strategy spec (plain language + compiled code/version)
- Data sources and timestamps; cached datasets (or hashes)
- Backtest settings: universe definition, rebalancing schedule, fees/slippage model, execution assumptions
- Metrics outputs + plots + warnings
- A “reasoning trace” for agent actions (what changed and why) that is clearly labeled **not a guarantee** but an explanation of decisions.

**Minimum evaluation ladder (MVP):**
1. **Benchmark first**: compare against (a) “do nothing” cash, (b) buy-and-hold baseline for the same universe, and (c) a simple rule-based baseline that is hard to beat (e.g., static allocation).  
2. **Walk-forward evaluation**: multiple contiguous out-of-sample blocks; prohibit tuning on test blocks.  
3. **Execution realism**: model bid/ask spread or slippage; enforce conservative fills.  
4. **Robustness checks**: parameter sensitivity, subperiod stress, and “randomization” tests to catch fragile exploitation of noise.  
5. **Paper trading gate**: paper trade for a minimum duration and minimum sample size of trades before any live unlock.

### LLM-specific safety in evaluation

The OWASP LLM Top 10 highlights risks like insecure output handling and prompt injection that can cause an LLM to produce dangerous or wrong outputs. citeturn19search0  
For your system, that implies:

- **LLM outputs must never be executed directly.** Strategy code or broker instructions produced by an LLM should be treated as *untrusted input* and must pass validation (schema, constraints, simulation).  
- **Hallucination containment:** show users “source-backed facts vs inferred suggestions” and require references for factual claims (e.g., “this company beat earnings”) before the system is allowed to incorporate them into a strategy rule.

## Regulatory and legal considerations

### The core legal reality: marketing and automation change your risk profile

The moment your system:
- markets “AI-driven investing edge,”
- displays backtested/hypothetical performance broadly,
- nudges users to specific securities/strategies,
- or offers an integrated path to live trading,

…you will intersect with investment-adviser marketing and anti-fraud expectations, even if your codebase is open-source and locally installed.

#### Marketing rule and hypothetical performance (U.S.-first)

- The rule governing investment adviser marketing in U.S. law is codified at 17 CFR §275.206(4)-1. citeturn20search19  
- SEC staff guidance emphasizes that advisers must have a reasonable basis to substantiate material statements of fact and that the adopting release for the rule is key background. citeturn20search4  
- “Hypothetical performance” is a particularly sensitive area in practice, and the risk escalates if your GitHub README or demo reports present backtests without clear conditions and limitations. citeturn20search19turn20search4  

**Practical product implication (FOUNDATION):** treat any “leaderboard” or “best strategies” feature as **high legal risk** unless you:
- tightly scope the audience,
- include robust disclosures,
- present assumptions and limitations clearly,
- and retain evidence for substantiation.

#### AI-washing and “truth-first” claims

The SEC has brought enforcement actions around misleading AI claims (“AI-washing”). While many sources discuss these actions, you should treat this as a product constraint: if you claim AI capabilities, you must be able to demonstrate what’s actually happening and how you prevent misleading outputs. citeturn5search30turn5search34  

#### FINRA overlay (if you market to broker-dealer contexts)

FINRA has emphasized that significant technology changes like GenAI can raise questions under existing rules and guidance; its notices point to a broad set of member obligations and risks (including fraud facilitation). citeturn5search27  
If you ever partner with or target broker-dealers, FINRA Rule 2210’s historical prohibition on projections becomes relevant. citeturn5search37  

### Open-source vs hosted: why it matters

**[INFERENCE]** The same code can carry different regulatory exposure depending on whether:
- it is a local tool people use privately (lower marketing/solicitation footprint), or
- it is a hosted service where you collect user data, recommend allocations, or intermediate trade execution (higher risk profile).

**Product recommendation (FOUNDATION):** design the repo so it is **cleanly separable**:
- Open-source local “research + paper trading” core (default),
- Optional live trading module behind explicit unlocks and “I understand” gates,
- A clearly separate path for any future hosted offering (if ever), with compliance investment.

### Compliance-related recordkeeping posture (even as open-source)

Even if you are not an adviser, you should build “as if you might be audited” for user trust:
- immutable run logs,
- reproducible results,
- and versioned templates for reports/claims.

This aligns with your “truth-first” positioning and reduces risk if you later commercialize.

## Security, privacy, and live-trading risk controls

### Threat model summary (what you must defend)

Your system has unusually sensitive assets:

- Brokerage trading authority (API keys / OAuth tokens)  
- AI provider keys and spend risk  
- Users’ portfolio holdings, trades, and strategy IP  
- Open-source supply chain attack surface (dependencies, releases, plugins)

And unusually dangerous actions:

- placing orders in live markets
- turning external text/news into strategy logic
- executing code generated by an LLM

The entity["organization","OWASP","web security nonprofit"] Top 10 for LLM applications enumerates the most relevant classes of LLM-driven risk here: prompt injection, insecure output handling, model DoS, and supply-chain vulnerabilities. citeturn19search0turn19search2  
The entity["organization","NIST","us standards agency"] SSDF provides a baseline “secure software development” posture that’s appropriate for a tool distributing executable software and handling secrets. citeturn4search25  

### Top risks and mitigations (prioritized)

| Risk | How it manifests in your system | Mitigation controls | Flag |
|---|---|---|---|
| Prompt injection via untrusted text | Web/news/filings include hidden instructions; agent is tricked into unsafe actions. citeturn19search0turn19news32 | Treat all external content as untrusted; isolate “content ingestion” from “action selection”; require explicit allow-lists of tools; add “two-man rule” for actions. | FOUNDATION |
| Insecure output handling | LLM outputs used as code/orders without strict validation. citeturn19search0 | Never execute LLM output directly; validate with schemas; run simulations; require human confirmation for any trade action. | FOUNDATION |
| Secrets exposed in browser/UI | Keys end up in localStorage/devtools; XSS steals them. | Enforce “keys never in browser”; backend-only secret handling. OpenAI explicitly warns against deploying keys client-side. citeturn17search3 | FOUNDATION |
| Supply-chain dependency compromise | Malicious dependency update steals keys or trades. | Pin dependencies; SBOM; review critical deps; use OpenSSF Scorecard; signed releases and provenance attestations. citeturn4search36turn18search11turn18search3 | FOUNDATION |
| Malicious plugin/connector | Third-party “broker adapter” exfiltrates secrets. | Plugin signing; permission model; sandboxing; “capabilities” manifest; default deny for network/file. | MVP→FOUNDATION |
| Rate-limit induced logic bugs | 429 responses cause partial data leading to wrong trades. Alpaca documents throttling and 429. citeturn6search0 | Standard retry/backoff; circuit breakers; “data freshness” metadata; block trade decisions on stale/missing data. | MVP |
| Model DoS / runaway cost | Agent loops generate huge token spend. citeturn19search0 | Hard budgets per session/plan; token/cost estimator; cancel button; concurrency caps. | MVP |
| Live trading blast radius | One bug or bad prompt places large orders. | Staged unlock; max position sizing; max daily loss; kill switch; “confirm trade” modal with reasons + constraints. | FOUNDATION |
| Misleading results / “backtest overclaim” | Users (or README) treat backtests as promises. | Force disclosure blocks; show assumptions; require out-of-sample gates; log and link run artifacts. Marketing substantiation matters. citeturn20search4turn20search19 | FOUNDATION |
| Credential leakage via GitHub | Users accidentally commit .env/token file. | .gitignore templates; scanning docs; warnings in installer; explicit checks. OpenAI warns against committing keys. citeturn17search3 | MVP |
| Data licensing violation | Users redistribute restricted data via reports/shares. Massive terms restrict redistribution/derived works. citeturn22view1turn11search36 | Data-source-aware sharing; “share” exports only derived metrics; user attests to licensing; disable in default builds. | MVP |
| Fake “AI” marketing | Claims about AI capabilities exceed reality; enforcement risk. citeturn5search34turn5search30 | “Truth-first” spec: every AI claim must map to a measurable capability; include limitations section. | FOUNDATION |

### Live trading staged unlock model (design requirement)

Lumibot explicitly encourages paper trading first before live. citeturn15search6  
Your product should enforce this culturally and mechanically:

```mermaid
flowchart TD
  A[Install + Connect Keys] --> B[Local Paper Trading Only]
  B --> C{Evidence Gates Passed?}
  C -->|No| B
  C -->|Yes| D[User Requests Live Unlock]
  D --> E[Risk Questionnaire + Explicit Disclosures]
  E --> F[Enable Live Trading in "Guarded Mode"]
  F --> G{User enables "Autonomous Mode"?}
  G -->|No| H[Manual Confirm Each Trade]
  G -->|Yes| I[Autonomous Trades\nwith hard limits + kill switch]
```

**Guarded mode controls (FOUNDATION):**
- Max % of portfolio per position  
- Max number of trades/day  
- Max daily loss (shutoff)  
- “Trading hours only” checks  
- “Stale data” hard stop  
- Full audit log: every order, decision, and data snapshot

### Release integrity and “trust mechanics” (especially for GitHub virality)

If you want users to run local software that can trade, they must trust the distribution channel:

- GitHub supports commit and tag signing (GPG/SSH/S/MIME) so changes can be verified. citeturn18search6turn18search2  
- GitHub Actions supports artifact attestations to establish build provenance; the official action creates a verifiable signature using a Sigstore-issued certificate. citeturn18search7turn18search3  
- SLSA is a supply-chain security framework defining levels and provenance expectations; the spec provides a common language for increasing integrity guarantees. citeturn18search0turn18search4  

**Recommendation (FOUNDATION):** ship “verifiable releases” as a product feature:
- signed tags
- build provenance attestation
- checksums
- reproducible benchmark scripts

## Open-source distribution, go-to-market, and next-week plan

### Open-source strategy for GitHub virality (what actually drives stars)

Open-source finance projects tend to spread when they combine:
1) **Instant gratification** (a demo in minutes),  
2) **Reproducibility** (anyone can reproduce results), and  
3) **Trust affordances** (clear disclosures, secure defaults, signed releases).

OpenBB’s public narrative highlights how open-source momentum can spike quickly when there’s a strong story and community pull. citeturn14search23  

**Repo-level must-haves (FOUNDATION):**
- A README that starts with: “What this is / what it is not / safety constraints / paper trading default”  
- A one-command installer that never asks for secrets in the browser  
- Example strategies that are intentionally boring but honest and reproducible  
- A “trust page”: threat model, risk controls, and what you log locally  
- Signed tags + artifact attestations (build provenance) citeturn18search2turn18search7  
- A LICENSE and explicit “not investment advice” disclaimers (avoid performance promises)

### Go-to-market narrative (90-day outline)

This is a positioning recommendation, not a factual claim.

**Narrative that fits your constraints (MVP):**  
“Local-first investing lab: agents help you design and test strategies *without lying to you*, and you can paper trade safely before you ever consider live trading.”

**Channels that match the product:**
- GitHub + Hacker News-style “show HN” launch (technical proof and reproducibility matter most)  
- YouTube demos focused on: (a) onboarding, (b) backtest reproducibility, (c) safety gating  
- Community contributions around connectors (brokers/data) and strategy templates, with strict review gates

### Business model paths (long-term options)

- **Open-source core + paid “pro” data connectors** (careful with licensing; keep user BYOK)  
- **Paid support / setup services** (white-glove onboarding without hosting user keys)  
- **Hosted version** (highest potential revenue, highest compliance/security burden; should be a separate later decision)

### Pre-build master checklist (condensed but decision-complete)

**Product definition**
- Define target persona: “power-user dev,” “curious retail,” or “serious systematic trader” [OPEN]  
- Decide scope: equities only vs options/crypto later [OPEN]  
- Decide what “AI agents” are allowed to do (suggest only vs modify code vs trade) [OPEN]

**Risk posture**
- Paper trading required by default (non-bypass)  
- Live trading behind staged unlock and hard limits  
- Clear disclosure and marketing policy aligned with Marketing Rule sensitivities citeturn20search19turn20search4  

**Architecture**
- Plugin interface for brokers, data, and model providers  
- Deterministic run artifacts: reproducible configs, cached data, hashed results  
- Local secrets store; keys never in browser; .gitignore templates citeturn17search3  

**Data**
- Choose “starter” data stack for MVP (broker data + one paid provider + EDGAR cache)  
- Implement per-provider rate limiting and caching; respect EDGAR’s 10 req/sec cap citeturn20search5  
- Implement data-source-aware sharing/export to avoid licensing violations (especially for commercial redistribution) citeturn22view1turn11search36  

**Validation**
- Standard evaluation ladder (benchmarks, walk-forward, conservative execution assumptions)  
- Pre-commit tests that detect lookahead and missing-cost models  
- Paper trading gate before live

**Security**
- Threat model document (ship in repo)  
- OWASP LLM Top 10 mitigations mapped to your architecture citeturn19search0  
- Supply-chain: SBOM + signed tags + provenance attestations citeturn18search2turn18search7turn4search36  

**Distribution**
- Reproducible installers; checksum verification instructions  
- “Safety defaults” enforced in code (cannot enable live trading without explicit steps)

### Decision matrix (what matters most before you code)

| Decision | If you choose the risky option | Safer default | Recommendation |
|---|---|---|---|
| Live trading in v1 | High trust + legal risk; one exploit can ruin credibility | Paper trading only | Start paper-only; add live later |
| Agent autonomy | Agents can generate unbounded variants and do unsafe actions | Human-in-the-loop + budgets | Human-in-loop required |
| Data licensing stance | “Share results freely” can violate provider terms | BYOK + limited exports | BYOK + terms-aware sharing |
| Key handling | Browser handles secrets → easy compromise | Local backend + encrypted store | Backend-only secrets citeturn17search3 |
| Distribution integrity | Unsigned binaries erode trust | Signed tags + attestations | Provenance + signatures citeturn18search7turn18search2 |

### Final recommendation

Build this as a **local-first investing lab** whose MVP is *paper-trading-first by design*, with an explicit “truth-first” methodology: reproducible backtests, conservative execution assumptions, and transparent uncertainty. The most important success factor for GitHub virality is not “more agent features,” but **trustable, reproducible, low-friction demos** backed by verifiable releases and explicit safety defaults.

### What to do next this week and most important unknowns

**This week plan (highest leverage)**
1. Write a one-page product spec defining: user persona, asset scope, and what the system will never do by default (e.g., no live trading without unlock).  
2. Draft the threat model and live-trading staged unlock gates (even if live is not in MVP).  
3. Pick one broker API and one market data provider for MVP integration and confirm: paper environment, rate limits, and ToS constraints. citeturn6search0turn11search16turn6search12  
4. Implement the “truth-first run artifact” format: every run writes a local bundle (config, data hashes, metrics, warnings).  
5. Create a single flagship demo: “strategy from plain English → backtest → paper trade,” with strict budgets and explicit disclosures.  
6. Add release integrity basics: signed tags + build provenance attestation in CI. citeturn18search2turn18search7  

**Most important unknowns to resolve early**
- Will users tolerate BYOK friction, or do they expect a hosted experience? [OPEN]  
- Which broker(s) can you support with **low approval friction** while still enabling safe paper trading? [OPEN]  
- What data providers’ licenses allow the sharing experience you want (especially if strategies/results are shared publicly)? [OPEN] citeturn22view1turn10search2  
- Can you design “agent teams” so they improve clarity and safety rather than just generating more overfit variants? [OPEN]  
- How will you ensure marketing and README claims never drift into “AI-washing” or unsubstantiated performance promises? [OPEN] citeturn5search34turn20search4
# Deep Research Dossier

The prompt references a full research dossier that should be pasted here verbatim.
That source dossier was not present in the workspace, so this placeholder keeps the
repository navigable without fabricating research content.

When the dossier is available, replace this file with the provided material exactly.
