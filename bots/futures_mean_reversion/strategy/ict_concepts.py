"""
ICT Core Concepts — Detection Engine
======================================
Implements the core Inner Circle Trader (ICT) market concepts as pure
detection functions operating on OHLC DataFrames.

Concepts implemented:
  - Fair Value Gap (FVG)
  - Order Block (OB)
  - Market Structure Shift (MSS) / Change of Character (ChoCH)
  - Swing High / Swing Low detection
  - Previous Day Levels (liquidity)
  - Judas Swing detection
  - Displacement detection
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class FairValueGap:
    """3-candle imbalance — price expected to return to fill."""
    idx: int                        # bar index in DataFrame
    timestamp: pd.Timestamp
    top: float                      # upper boundary
    bottom: float                   # lower boundary
    midpoint: float                 # 50% — preferred entry level
    direction: str                  # "bullish" | "bearish"
    size_pts: float                 # gap size in points
    filled: bool = False            # True once price trades through midpoint


@dataclass
class OrderBlock:
    """Last opposing candle before a displacement move."""
    idx: int
    timestamp: pd.Timestamp
    top: float
    bottom: float
    midpoint: float
    direction: str                  # "bullish" | "bearish"
    displaced: bool = False         # True = confirmed with displacement


@dataclass
class SwingPoint:
    idx: int
    timestamp: pd.Timestamp
    price: float
    kind: str                       # "high" | "low"
    taken: bool = False             # True = liquidity was swept


@dataclass
class MarketStructureShift:
    """Break of the most recent opposing swing after a liquidity raid."""
    idx: int
    timestamp: pd.Timestamp
    direction: str                  # "bullish" | "bearish"
    broken_level: float             # the swing that was broken
    displacement: bool              # was the break impulsive?
    fvg: Optional[FairValueGap] = None   # FVG created in the displacement


@dataclass
class JudasSwing:
    """Fake initial move off the open to grab liquidity before the real move."""
    idx: int
    timestamp: pd.Timestamp
    direction: str                  # "bullish" = swept highs, "bearish" = swept lows
    swept_level: float              # the liquidity level that was taken
    reversal_price: float           # price at which Judas ended
    confirmed: bool = False         # True once MSS confirmed


@dataclass
class PrevDayLevels:
    date: object
    high: float
    low: float
    close: float
    open: float
    range_pts: float = 0.0

    def __post_init__(self):
        self.range_pts = self.high - self.low


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _avg_range(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return (df["high"] - df["low"]).rolling(period, min_periods=5).mean()


def _is_displaced(df: pd.DataFrame, idx: int, mult: float = 1.5, period: int = 20) -> bool:
    """True if candle at idx has range > mult × average range."""
    avg = _avg_range(df, period).iloc[idx]
    if pd.isna(avg) or avg == 0:
        return False
    candle_range = df["high"].iloc[idx] - df["low"].iloc[idx]
    return candle_range > mult * avg


# ─── Swing Points ─────────────────────────────────────────────────────────────

def detect_swing_points(df: pd.DataFrame, lookback: int = 3) -> list[SwingPoint]:
    """
    Detect swing highs and lows using a simple N-bar pivot.
    lookback=3 works well on 5-min charts for intraday structure.
    """
    points: list[SwingPoint] = []
    n = lookback

    for i in range(n, len(df) - n):
        h = df["high"].iloc[i]
        lo = df["low"].iloc[i]

        is_sh = (
            all(h >= df["high"].iloc[i - j] for j in range(1, n + 1)) and
            all(h >= df["high"].iloc[i + j] for j in range(1, n + 1))
        )
        is_sl = (
            all(lo <= df["low"].iloc[i - j] for j in range(1, n + 1)) and
            all(lo <= df["low"].iloc[i + j] for j in range(1, n + 1))
        )

        if is_sh:
            points.append(SwingPoint(i, df.index[i], h, "high"))
        if is_sl:
            points.append(SwingPoint(i, df.index[i], lo, "low"))

    return points


# ─── Fair Value Gaps ──────────────────────────────────────────────────────────

def detect_fvg(
    df: pd.DataFrame,
    min_gap_pts: float = 2.0,
    require_displacement: bool = True,
) -> list[FairValueGap]:
    """
    Scan DataFrame for Fair Value Gaps.

    Bullish FVG : candle[i-2].high  <  candle[i].low   (gap between them)
    Bearish FVG : candle[i-2].low   >  candle[i].high  (gap between them)

    The middle candle (i-1) should be a strong displacement candle.
    """
    fvgs: list[FairValueGap] = []

    for i in range(2, len(df)):
        c0_high = df["high"].iloc[i - 2]
        c0_low  = df["low"].iloc[i - 2]
        c2_high = df["high"].iloc[i]
        c2_low  = df["low"].iloc[i]

        # Bullish FVG
        if c2_low > c0_high:
            gap = c2_low - c0_high
            if gap >= min_gap_pts:
                if require_displacement and not _is_displaced(df, i - 1):
                    continue
                fvgs.append(FairValueGap(
                    idx=i,
                    timestamp=df.index[i],
                    top=c2_low,
                    bottom=c0_high,
                    midpoint=(c2_low + c0_high) / 2,
                    direction="bullish",
                    size_pts=gap,
                ))

        # Bearish FVG
        elif c2_high < c0_low:
            gap = c0_low - c2_high
            if gap >= min_gap_pts:
                if require_displacement and not _is_displaced(df, i - 1):
                    continue
                fvgs.append(FairValueGap(
                    idx=i,
                    timestamp=df.index[i],
                    top=c0_low,
                    bottom=c2_high,
                    midpoint=(c0_low + c2_high) / 2,
                    direction="bearish",
                    size_pts=gap,
                ))

    return fvgs


def mark_filled_fvgs(fvgs: list[FairValueGap], df: pd.DataFrame) -> None:
    """Mark FVGs as filled once price trades to the midpoint."""
    for fvg in fvgs:
        subsequent = df.iloc[fvg.idx + 1:]
        if fvg.direction == "bullish":
            if (subsequent["low"] <= fvg.midpoint).any():
                fvg.filled = True
        else:
            if (subsequent["high"] >= fvg.midpoint).any():
                fvg.filled = True


# ─── Order Blocks ─────────────────────────────────────────────────────────────

def detect_order_blocks(
    df: pd.DataFrame,
    displacement_mult: float = 1.5,
) -> list[OrderBlock]:
    """
    Detect Order Blocks — last opposing candle before displacement.

    Bullish OB : last bearish candle before a bullish displacement
    Bearish OB : last bullish candle before a bearish displacement
    """
    obs: list[OrderBlock] = []

    for i in range(1, len(df) - 1):
        curr = df.iloc[i]
        nxt  = df.iloc[i + 1]

        displaced = _is_displaced(df, i + 1, displacement_mult)

        # Bullish OB
        if curr["close"] < curr["open"] and nxt["close"] > nxt["open"] and displaced:
            obs.append(OrderBlock(
                idx=i,
                timestamp=df.index[i],
                top=max(curr["open"], curr["close"]),
                bottom=curr["low"],
                midpoint=(max(curr["open"], curr["close"]) + curr["low"]) / 2,
                direction="bullish",
                displaced=True,
            ))

        # Bearish OB
        elif curr["close"] > curr["open"] and nxt["close"] < nxt["open"] and displaced:
            obs.append(OrderBlock(
                idx=i,
                timestamp=df.index[i],
                top=curr["high"],
                bottom=min(curr["open"], curr["close"]),
                midpoint=(curr["high"] + min(curr["open"], curr["close"])) / 2,
                direction="bearish",
                displaced=True,
            ))

    return obs


# ─── Market Structure Shift ───────────────────────────────────────────────────

def detect_mss(
    df: pd.DataFrame,
    swing_lookback: int = 3,
    require_displacement: bool = True,
) -> list[MarketStructureShift]:
    """
    Detect Market Structure Shifts (MSS / ChoCH).

    Bullish MSS : close breaks above recent swing high  → impulsive
    Bearish MSS : close breaks below recent swing low   → impulsive
    """
    msses: list[MarketStructureShift] = []
    swings = detect_swing_points(df, swing_lookback)
    fvgs   = detect_fvg(df, require_displacement=False)

    sh_list = [(s.idx, s.price) for s in swings if s.kind == "high"]
    sl_list = [(s.idx, s.price) for s in swings if s.kind == "low"]

    for i in range(swing_lookback * 2 + 2, len(df)):
        close     = df["close"].iloc[i]
        prev_close = df["close"].iloc[i - 1]

        recent_sh = [p for idx, p in sh_list if idx < i]
        recent_sl = [p for idx, p in sl_list if idx < i]

        if not recent_sh or not recent_sl:
            continue

        last_sh = recent_sh[-1]
        last_sl = recent_sl[-1]
        displaced = _is_displaced(df, i) if require_displacement else True

        # Bullish MSS
        if close > last_sh and prev_close <= last_sh:
            # Find most recent bullish FVG before this bar
            rel_fvg = next(
                (f for f in reversed(fvgs)
                 if f.direction == "bullish" and f.idx < i and not f.filled),
                None
            )
            msses.append(MarketStructureShift(
                idx=i,
                timestamp=df.index[i],
                direction="bullish",
                broken_level=last_sh,
                displacement=displaced,
                fvg=rel_fvg,
            ))

        # Bearish MSS
        elif close < last_sl and prev_close >= last_sl:
            rel_fvg = next(
                (f for f in reversed(fvgs)
                 if f.direction == "bearish" and f.idx < i and not f.filled),
                None
            )
            msses.append(MarketStructureShift(
                idx=i,
                timestamp=df.index[i],
                direction="bearish",
                broken_level=last_sl,
                displacement=displaced,
                fvg=rel_fvg,
            ))

    return msses


# ─── Previous Day Levels ──────────────────────────────────────────────────────

def get_prev_day_levels(daily_df: pd.DataFrame, trade_date) -> Optional[PrevDayLevels]:
    """
    Return OHLC of the day prior to trade_date from a daily DataFrame.
    """
    prior = daily_df[daily_df.index.normalize() < pd.Timestamp(trade_date)]
    if prior.empty:
        return None
    row = prior.iloc[-1]
    return PrevDayLevels(
        date=prior.index[-1].date(),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        open=float(row["open"]),
    )


# ─── Judas Swing ──────────────────────────────────────────────────────────────

def detect_judas_swing(
    session_df: pd.DataFrame,
    pdl: PrevDayLevels,
    judas_window_bars: int = 8,
    min_raid_pts: float = 2.0,
) -> Optional[JudasSwing]:
    """
    Detect a Judas Swing in the first `judas_window_bars` bars of the session.

    A Judas Swing is when price initially raids a key liquidity level
    (prev day high or low) and then reverses — trapping early traders.

    Returns the detected JudasSwing or None.
    """
    if len(session_df) < judas_window_bars:
        return None

    window = session_df.iloc[:judas_window_bars]
    session_high = window["high"].max()
    session_low  = window["low"].min()

    # Bearish Judas: swept prev day HIGH then reversed down
    swept_high = session_high >= pdl.high - min_raid_pts
    if swept_high:
        raid_bar = window["high"].idxmax()
        raid_idx = session_df.index.get_loc(raid_bar)
        reversal = session_df["close"].iloc[raid_idx]
        return JudasSwing(
            idx=raid_idx,
            timestamp=raid_bar,
            direction="bearish",        # real move will be DOWN
            swept_level=pdl.high,
            reversal_price=reversal,
        )

    # Bullish Judas: swept prev day LOW then reversed up
    swept_low = session_low <= pdl.low + min_raid_pts
    if swept_low:
        raid_bar = window["low"].idxmin()
        raid_idx = session_df.index.get_loc(raid_bar)
        reversal = session_df["close"].iloc[raid_idx]
        return JudasSwing(
            idx=raid_idx,
            timestamp=raid_bar,
            direction="bullish",        # real move will be UP
            swept_level=pdl.low,
            reversal_price=reversal,
        )

    return None
