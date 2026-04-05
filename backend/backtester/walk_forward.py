from __future__ import annotations

import pandas as pd


def split_walk_forward(frame: pd.DataFrame, window_months: int) -> list[pd.DataFrame]:
    if frame.empty:
        return []
    approx_days = max(21, window_months * 21)
    windows = []
    for start in range(0, len(frame), approx_days):
        window = frame.iloc[start : start + approx_days]
        if len(window) >= 10:
            windows.append(window)
    return windows
