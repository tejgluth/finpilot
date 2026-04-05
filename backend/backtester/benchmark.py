from __future__ import annotations


def build_benchmark_curve(starting_cash: float, closes: list[float]) -> list[float]:
    if not closes:
        return []
    first = closes[0]
    if first <= 0:
        return [round(starting_cash, 2) for _ in closes]
    return [round(starting_cash * (close / first), 2) for close in closes]
