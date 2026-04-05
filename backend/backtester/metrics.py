from __future__ import annotations

import numpy as np


def compute_metrics(equity_curve: list[float], periods_per_year: int = 252) -> dict:
    if len(equity_curve) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "calmar": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
        }
    series = np.array(equity_curve, dtype=float)
    returns = np.diff(series) / np.where(series[:-1] == 0, 1.0, series[:-1])
    downside = returns[returns < 0]
    total_return = ((series[-1] / series[0]) - 1.0) * 100
    running_max = np.maximum.accumulate(series)
    drawdowns = (series - running_max) / running_max
    max_drawdown = float(drawdowns.min()) if len(drawdowns) else 0.0
    sharpe = float((returns.mean() / (returns.std() or 1e-9)) * np.sqrt(periods_per_year))
    sortino = float((returns.mean() / ((downside.std() if len(downside) else 1e-9) or 1e-9)) * np.sqrt(periods_per_year))
    calmar = float((total_return / 100) / abs(max_drawdown or 1e-9))
    win_rate = float((returns > 0).sum() / len(returns) * 100)
    return {
        "total_return_pct": round(total_return, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3),
        "max_drawdown_pct": round(abs(max_drawdown) * 100, 2),
        "win_rate_pct": round(win_rate, 2),
    }
