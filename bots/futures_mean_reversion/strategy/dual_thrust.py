"""
Dual Thrust Breakout Strategy (intraday variant)
-------------------------------------------------
Range = max(HH - LC, HC - LL)  where HH/LC/HC/LL come from prior N sessions
Upper trigger = Open + K_long  * Range
Lower trigger = Open - K_short * Range

Long  when price breaks above upper trigger
Short when price breaks below lower trigger
Flatten at session close.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class DTSignal:
    direction: str      # "long" | "short" | "flat"
    upper: float
    lower: float
    range_val: float
    reason: str


class DualThrust:
    def __init__(self, cfg):
        self.cfg = cfg

    def _compute_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Daily range using Dual Thrust formula.
        df must have daily OHLC. Returns series aligned to df index.
        """
        n = self.cfg.lookback
        hh = df["high"].rolling(n).max()
        lc = df["close"].rolling(n).min()
        hc = df["close"].rolling(n).max()
        ll = df["low"].rolling(n).min()
        return pd.concat([hh - lc, hc - ll], axis=1).max(axis=1)

    def compute_triggers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expects daily OHLC. Returns df with upper/lower trigger columns.
        Triggers are based on prior-day range, applied at today's open.
        """
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        rng = self._compute_range(df).shift(1)   # prior day
        df["dt_range"] = rng
        df["dt_upper"] = df["open"] + self.cfg.k_long * rng
        df["dt_lower"] = df["open"] - self.cfg.k_short * rng
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.compute_triggers(df)
        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            row = df.iloc[i]
            if pd.isna(row["dt_upper"]):
                continue
            if row["high"] >= row["dt_upper"]:
                signals.iloc[i] = 1    # long breakout
            elif row["low"] <= row["dt_lower"]:
                signals.iloc[i] = -1   # short breakout
            # Dual Thrust reverses intraday; flatten at close handled by backtester

        df["signal"] = signals
        return df

    def latest_signal(self, df: pd.DataFrame) -> DTSignal:
        df = self.compute_triggers(df)
        row = df.iloc[-1]
        if pd.isna(row.get("dt_upper", np.nan)):
            return DTSignal("flat", np.nan, np.nan, np.nan, "Insufficient data")

        if row["high"] >= row["dt_upper"]:
            direction = "long"
            reason = "Price broke above upper Dual Thrust trigger"
        elif row["low"] <= row["dt_lower"]:
            direction = "short"
            reason = "Price broke below lower Dual Thrust trigger"
        else:
            direction = "flat"
            reason = "Price within range"

        return DTSignal(direction, row["dt_upper"], row["dt_lower"], row["dt_range"], reason)
