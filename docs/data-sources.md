# Data Sources

## Always-available defaults

- `yfinance`
- `FRED`
- `SEC EDGAR`
- `CoinGecko`

## Optional keyed providers

- `Finnhub`
- `Marketaux`
- `Financial Modeling Prep`
- `Reddit PRAW`
- `Alpaca market data`
- `Polygon`

## Usage rules

- Each agent only uses the adapters assigned to its domain.
- Missing providers produce unavailable fields rather than guessed values.
- News, Reddit, and filing text are sanitized before LLM exposure.
- Provider plan and rate limits should be respected through the limiter layer.
