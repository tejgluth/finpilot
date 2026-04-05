# Backtesting Guide

## Default behavior

- `backtest_strict` is the default truthful mode.
- Strict mode requires `as_of_datetime` and disallows unconstrained latest/current semantics.
- `backtest_experimental` exists for clearly labeled exploratory runs.
- The selected compiled team drives the same core agent pipeline used in analyze and paper/live modes.
- Transaction costs are included.
- S&P 500 buy-and-hold remains visible for comparison.

## Artifacts

Each run stores:

- data hash
- config snapshot
- transaction cost model
- timestamp
- benchmark reference
- effective compiled team config
- prompt pack ids and versions
- provider/model
- temporal boundary
- lagged or excluded temporal features

## Notes

Backtests are a research tool. They are not a promise of future performance.
