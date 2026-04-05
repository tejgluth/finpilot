from __future__ import annotations


def compute_transaction_cost(entry_notional: float, slippage_pct: float, commission_pct: float) -> float:
    return round(entry_notional * ((slippage_pct + commission_pct) / 100.0), 2)
