from __future__ import annotations

import pandas as pd

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.data.adapters import YFinanceAdapter
from backend.settings.user_settings import DataSourceSettings


class TechnicalsAgent(BaseAnalysisAgent):
    agent_name = "technicals"
    EXPECTED_FIELDS = [
        "rsi_14",
        "macd",
        "macd_signal",
        "bollinger_upper",
        "bollinger_lower",
        "sma_50",
        "sma_200",
        "volume_20d_avg",
        "atr_14",
        "latest_close",
    ]

    async def fetch_data(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        compiled_spec: CompiledAgentSpec,
        execution_snapshot: ExecutionSnapshot,
    ) -> FetchedData:
        data = FetchedData(ticker=ticker.upper())
        if not data_settings.use_yfinance or "yfinance" not in set(compiled_spec.owned_sources):
            data.failed_sources.append("yfinance")
            return data

        periods = int(compiled_spec.lookback_config.get("days", compiled_spec.modifiers.get("lookback_days", 260)))
        frame = await YFinanceAdapter().get_ohlcv(
            ticker,
            periods=periods,
            as_of_datetime=execution_snapshot.data_boundary.as_of_datetime,
        )
        required_columns = {"close", "high", "low", "volume"}
        if frame.empty or not required_columns.issubset(frame.columns):
            data.failed_sources.append("yfinance")
            return data

        close = pd.to_numeric(frame["close"], errors="coerce").dropna().reset_index(drop=True)
        high = pd.to_numeric(frame["high"], errors="coerce").dropna().reset_index(drop=True)
        low = pd.to_numeric(frame["low"], errors="coerce").dropna().reset_index(drop=True)
        volume = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).reset_index(drop=True)
        if close.empty or high.empty or low.empty:
            data.failed_sources.append("yfinance")
            return data

        delta = close.diff()
        gains = delta.clip(lower=0).rolling(14).mean()
        losses = (-delta.clip(upper=0)).rolling(14).mean().replace(0, 0.0001)
        rs = gains / losses
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9, adjust=False).mean()
        rolling_20 = close.rolling(20)
        bollinger_mid = rolling_20.mean()
        bollinger_std = rolling_20.std().fillna(0)
        atr = (high - low).rolling(14).mean()

        rsi_value = rs.iloc[-1] if not rs.dropna().empty else None
        macd_value = macd.iloc[-1] if not macd.dropna().empty else None
        signal_value = signal.iloc[-1] if not signal.dropna().empty else None
        bollinger_mid_value = bollinger_mid.iloc[-1] if not bollinger_mid.dropna().empty else None
        bollinger_std_value = bollinger_std.iloc[-1] if not bollinger_std.dropna().empty else None
        atr_value = atr.iloc[-1] if not atr.dropna().empty else None

        indicators = {
            "rsi_14": round((100 - (100 / (1 + rsi_value))), 2) if rsi_value is not None else None,
            "macd": round(macd_value, 3) if macd_value is not None else None,
            "macd_signal": round(signal_value, 3) if signal_value is not None else None,
            "bollinger_upper": round((bollinger_mid_value + 2 * bollinger_std_value), 2)
            if bollinger_mid_value is not None and bollinger_std_value is not None
            else None,
            "bollinger_lower": round((bollinger_mid_value - 2 * bollinger_std_value), 2)
            if bollinger_mid_value is not None and bollinger_std_value is not None
            else None,
            "sma_50": round(close.tail(50).mean(), 2) if not close.empty else None,
            "sma_200": round(close.tail(200).mean(), 2) if not close.empty else None,
            "volume_20d_avg": int(volume.tail(20).mean()) if not volume.empty else None,
            "atr_14": round(atr_value, 2) if atr_value is not None else None,
            "latest_close": round(float(close.iloc[-1]), 2) if not close.empty else None,
        }
        for field_name, value in indicators.items():
            data.fields[field_name] = value
            data.field_sources[field_name] = "yfinance"
            data.field_ages[field_name] = 15.0
        return data

    def build_system_prompt(self) -> str:
        return "Interpret pre-computed technical indicators only.\n"

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        variant = compiled_spec.variant_id
        rsi = float(data.fields.get("rsi_14") or 50)
        macd = float(data.fields.get("macd") or 0)
        macd_signal = float(data.fields.get("macd_signal") or 0)
        sma_50 = float(data.fields.get("sma_50") or 0)
        sma_200 = float(data.fields.get("sma_200") or 0)
        latest_close = float(data.fields.get("latest_close") or 0)
        upper = float(data.fields.get("bollinger_upper") or 0)
        lower = float(data.fields.get("bollinger_lower") or 0)
        if variant == "oneil_breakout":
            if macd > macd_signal and sma_50 > sma_200 and rsi >= 55:
                return "BUY", 0.74, "Trend alignment and constructive momentum fit a breakout-style technical read."
        if variant == "minervini_trend_template":
            if sma_50 > sma_200 and latest_close > sma_50 and macd > 0 and rsi < 75:
                return "BUY", 0.73, "Trend structure passes a stricter trend-template style read."
        if variant == "mean_reversion":
            if latest_close < lower and rsi < 35:
                return "BUY", 0.67, "Price extension below the lower band with weak RSI supports a reversion setup."
            if latest_close > upper and rsi > 75:
                return "SELL", 0.65, "Upper-band extension and elevated RSI fit a reversion short signal."
        if macd > 0 and sma_50 > sma_200 and rsi < 70:
            return "BUY", 0.7, "Trend and momentum indicators are aligned without extreme overbought pressure."
        if macd < 0 and sma_50 < sma_200 and rsi > 45:
            return "SELL", 0.66, "Trend structure and MACD are leaning negative."
        return "HOLD", 0.54, "Technicals are mixed or near neutral."
