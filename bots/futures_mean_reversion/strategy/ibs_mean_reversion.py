"""
IBS (Internal Bar Strength) Mean Reversion Strategy
----------------------------------------------------
Signal logic:
  rolling_mean  = SMA(high - low, 25)
  lower_band    = highest(high, 10) - 2.5 * rolling_mean
  IBS           = (close - low) / (high - low)
  LONG  if close < lower_band  AND  IBS < 0.30  AND  close > 300-SMA
  EXIT  if close > prev_high   OR   close < 300-SMA  OR  max_hold exceeded
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class Signal:
    direction: str          # "long" | "flat"
    reason: str
    ibs: float
    lower_band: float
    trend_filter: float
    atr: float


class IBSMeanReversion:
    """Stateless indicator calculator + signal generator."""

    def __init__(self, cfg):
        self.cfg = cfg

    # ── Indicator Calculations ──────────────────────────────────────────────

    @staticmethod
    def compute_ibs(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        rng = high - low
        # Guard against zero-range bars (halted trading, etc.)
        return ((close - low) / rng.replace(0, np.nan)).clip(0, 1)

    def compute_rolling_mean(self, high: pd.Series, low: pd.Series) -> pd.Series:
        bar_range = high - low
        return bar_range.rolling(self.cfg.sma_period, min_periods=self.cfg.sma_period).mean()

    def compute_lower_band(self, high: pd.Series, rolling_mean: pd.Series) -> pd.Series:
        highest_high = high.rolling(self.cfg.band_lookback, min_periods=self.cfg.band_lookback).max()
        return highest_high - self.cfg.band_multiplier * rolling_mean

    def compute_trend_filter(self, close: pd.Series) -> pd.Series:
        return close.rolling(self.cfg.trend_filter_sma, min_periods=self.cfg.trend_filter_sma).mean()

    def compute_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(14, min_periods=14).mean()

    # ── Full Feature Frame ──────────────────────────────────────────────────

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expects df with columns: open, high, low, close, volume.
        Returns df with all indicator columns appended.
        """
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        df["ibs"] = self.compute_ibs(df["high"], df["low"], df["close"])
        df["rolling_mean"] = self.compute_rolling_mean(df["high"], df["low"])
        df["lower_band"] = self.compute_lower_band(df["high"], df["rolling_mean"])
        df["trend_sma"] = self.compute_trend_filter(df["close"])
        df["atr"] = self.compute_atr(df["high"], df["low"], df["close"])
        df["prev_high"] = df["high"].shift(1)
        df["prev_close"] = df["close"].shift(1)
        return df

    # ── Signal Generation ───────────────────────────────────────────────────

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns df with 'signal' column: +1 = go long, 0 = flat/exit.
        """
        df = self.compute_features(df)

        long_condition = (
            (df["close"] < df["lower_band"]) &
            (df["ibs"] < self.cfg.ibs_entry_threshold) &
            (df["close"] > df["trend_sma"])  # above 300-SMA = bullish regime
        )

        exit_above_prev_high = df["close"] > df["prev_high"]
        exit_below_trend = df["close"] < df["trend_sma"]

        # Build signal series with hold logic
        signals = pd.Series(0, index=df.index)
        in_trade = False
        bars_held = 0
        entry_idx = None

        for i in range(len(df)):
            row = df.iloc[i]

            if in_trade:
                bars_held += 1
                exit_hit = (
                    (self.cfg.exit_above_prev_high and row["close"] > row["prev_high"]) or
                    (self.cfg.exit_below_trend and row["close"] < row["trend_sma"]) or
                    (bars_held >= self.cfg.max_hold_bars)
                )
                if exit_hit:
                    in_trade = False
                    bars_held = 0
                else:
                    signals.iloc[i] = 1

            else:
                if (not pd.isna(row["lower_band"]) and
                        not pd.isna(row["trend_sma"]) and
                        long_condition.iloc[i]):
                    in_trade = True
                    bars_held = 1
                    signals.iloc[i] = 1

        df["signal"] = signals
        df["in_trade"] = signals
        return df

    # ── Latest Bar Signal (for live trading) ────────────────────────────────

    def latest_signal(self, df: pd.DataFrame, current_position: int = 0) -> Signal:
        df = self.compute_features(df)
        row = df.iloc[-1]

        ibs = row["ibs"]
        lower_band = row["lower_band"]
        trend = row["trend_sma"]
        atr = row["atr"]

        entry_ok = (
            not pd.isna(lower_band) and
            not pd.isna(trend) and
            row["close"] < lower_band and
            ibs < self.cfg.ibs_entry_threshold and
            row["close"] > trend
        )

        if current_position == 0 and entry_ok:
            return Signal("long", "IBS entry: oversold below lower band", ibs, lower_band, trend, atr)

        if current_position > 0:
            if self.cfg.exit_above_prev_high and row["close"] > row["prev_high"]:
                return Signal("flat", "Exit: close above prev high", ibs, lower_band, trend, atr)
            if self.cfg.exit_below_trend and row["close"] < trend:
                return Signal("flat", "Exit: close below 300-SMA trend filter", ibs, lower_band, trend, atr)

        direction = "long" if current_position > 0 else "flat"
        return Signal(direction, "Hold" if current_position > 0 else "No signal", ibs, lower_band, trend, atr)
