"""
ICT Core Concepts — Detection Engine
======================================
Implements ICT market concepts as pure detection functions on OHLC DataFrames.

Concepts:
  - Fair Value Gap (FVG)
  - Order Block (OB)
  - Market Structure Shift (MSS) / Change of Character
  - Swing High / Swing Low detection
  - Previous Day Levels (liquidity targets)
  - Judas Swing (liquidity raid + reversal)
  - Displacement detection
  - SMT Divergence (inter-market correlation divergence)
  - Premium / Discount zones
  - Higher Timeframe (HTF) trend alignment
  - Setup scoring (A+ filter — 8+/10 required)
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class FairValueGap:
    idx: int
    timestamp: pd.Timestamp
    top: float
    bottom: float
    midpoint: float
    direction: str          # "bullish" | "bearish"
    size_pts: float
    touched: bool = False   # True = price has revisited but not filled
    filled: bool = False    # True = price traded through midpoint


@dataclass
class OrderBlock:
    idx: int
    timestamp: pd.Timestamp
    top: float
    bottom: float
    midpoint: float
    direction: str
    displaced: bool = False


@dataclass
class SwingPoint:
    idx: int
    timestamp: pd.Timestamp
    price: float
    kind: str               # "high" | "low"
    taken: bool = False


@dataclass
class MarketStructureShift:
    idx: int
    timestamp: pd.Timestamp
    direction: str
    broken_level: float
    displacement: bool
    fvg: Optional[FairValueGap] = None


@dataclass
class JudasSwing:
    idx: int
    timestamp: pd.Timestamp
    direction: str          # "bullish" = swept lows, real move UP
    swept_level: float
    reversal_price: float
    confirmed: bool = False


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


@dataclass
class SetupScore:
    """
    A+ Setup Scoring — 10 points total.
    Minimum 8/10 required to take the trade.

    Points breakdown:
      judas_confirmed      +2   liquidity swept + reversal detected
      mss_displaced        +2   MSS with impulsive displacement candle
      fvg_entry            +1   FVG entry (vs lower-quality OB)
      smt_divergence       +2   inter-market divergence at swept level
      htf_aligned          +1   15-min trend agrees with trade direction
      in_optimal_zone      +1   entry in discount (long) or premium (short)
      fvg_first_touch      +1   FVG has never been touched before
    """
    judas_confirmed: bool = False       # +2
    mss_displaced: bool = False         # +2
    fvg_entry: bool = False             # +1
    smt_divergence: bool = False        # +2
    htf_aligned: bool = False           # +1
    in_optimal_zone: bool = False       # +1
    fvg_first_touch: bool = False       # +1
    total: int = 0
    grade: str = "F"

    _WEIGHTS = {
        "judas_confirmed": 2,
        "mss_displaced": 2,
        "fvg_entry": 1,
        "smt_divergence": 2,
        "htf_aligned": 1,
        "in_optimal_zone": 1,
        "fvg_first_touch": 1,
    }

    def compute(self) -> int:
        score = sum(
            w for k, w in self._WEIGHTS.items() if getattr(self, k)
        )
        self.total = score
        if score >= 9:
            self.grade = "A+"
        elif score >= 8:
            self.grade = "A"
        elif score >= 6:
            self.grade = "B"
        elif score >= 4:
            self.grade = "C"
        else:
            self.grade = "F"
        return score

    @property
    def is_aplus(self) -> bool:
        return self.total >= 8

    def breakdown(self) -> str:
        lines = [f"Score: {self.total}/10 ({self.grade})"]
        for k, w in self._WEIGHTS.items():
            val = getattr(self, k)
            tick = "✅" if val else "❌"
            lines.append(f"  {tick} {k.replace('_', ' ').title():<22} +{w}")
        return "\n".join(lines)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _avg_range(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return (df["high"] - df["low"]).rolling(period, min_periods=5).mean()


def _is_displaced(df: pd.DataFrame, idx: int, mult: float = 1.5, period: int = 20) -> bool:
    avg = _avg_range(df, period).iloc[idx]
    if pd.isna(avg) or avg == 0:
        return False
    return (df["high"].iloc[idx] - df["low"].iloc[idx]) > mult * avg


def resample_to_htf(df: pd.DataFrame, rule: str = "15min") -> pd.DataFrame:
    """Resample 5-min bars to higher timeframe (15-min default)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    htf = df.resample(rule).agg(agg).dropna()
    return htf


# ─── Swing Points ─────────────────────────────────────────────────────────────

def detect_swing_points(df: pd.DataFrame, lookback: int = 3) -> list:
    points = []
    n = lookback
    for i in range(n, len(df) - n):
        h  = df["high"].iloc[i]
        lo = df["low"].iloc[i]
        is_sh = (all(h  >= df["high"].iloc[i - j] for j in range(1, n + 1)) and
                 all(h  >= df["high"].iloc[i + j] for j in range(1, n + 1)))
        is_sl = (all(lo <= df["low"].iloc[i - j]  for j in range(1, n + 1)) and
                 all(lo <= df["low"].iloc[i + j]   for j in range(1, n + 1)))
        if is_sh:
            points.append(SwingPoint(i, df.index[i], h,  "high"))
        if is_sl:
            points.append(SwingPoint(i, df.index[i], lo, "low"))
    return points


# ─── Fair Value Gaps ──────────────────────────────────────────────────────────

def detect_fvg(
    df: pd.DataFrame,
    min_gap_pts: float = 2.0,
    require_displacement: bool = True,
) -> list:
    fvgs = []
    for i in range(2, len(df)):
        c0_high = df["high"].iloc[i - 2]
        c0_low  = df["low"].iloc[i - 2]
        c2_high = df["high"].iloc[i]
        c2_low  = df["low"].iloc[i]

        if c2_low > c0_high:
            gap = c2_low - c0_high
            if gap >= min_gap_pts:
                if require_displacement and not _is_displaced(df, i - 1):
                    continue
                fvgs.append(FairValueGap(
                    idx=i, timestamp=df.index[i],
                    top=c2_low, bottom=c0_high,
                    midpoint=(c2_low + c0_high) / 2,
                    direction="bullish", size_pts=gap,
                ))
        elif c2_high < c0_low:
            gap = c0_low - c2_high
            if gap >= min_gap_pts:
                if require_displacement and not _is_displaced(df, i - 1):
                    continue
                fvgs.append(FairValueGap(
                    idx=i, timestamp=df.index[i],
                    top=c0_low, bottom=c2_high,
                    midpoint=(c0_low + c2_high) / 2,
                    direction="bearish", size_pts=gap,
                ))
    return fvgs


def mark_fvg_touches(fvgs: list, df: pd.DataFrame) -> None:
    """Mark FVGs as touched (visited but not filled) or filled."""
    for fvg in fvgs:
        subsequent = df.iloc[fvg.idx + 1:]
        if fvg.direction == "bullish":
            if (subsequent["low"] <= fvg.bottom).any():
                fvg.filled = True
            elif (subsequent["low"] <= fvg.midpoint).any():
                fvg.touched = True
        else:
            if (subsequent["high"] >= fvg.top).any():
                fvg.filled = True
            elif (subsequent["high"] >= fvg.midpoint).any():
                fvg.touched = True


# ─── Order Blocks ─────────────────────────────────────────────────────────────

def detect_order_blocks(df: pd.DataFrame, displacement_mult: float = 1.5) -> list:
    obs = []
    for i in range(1, len(df) - 1):
        curr = df.iloc[i]
        nxt  = df.iloc[i + 1]
        displaced = _is_displaced(df, i + 1, displacement_mult)
        if curr["close"] < curr["open"] and nxt["close"] > nxt["open"] and displaced:
            obs.append(OrderBlock(
                idx=i, timestamp=df.index[i],
                top=max(curr["open"], curr["close"]),
                bottom=curr["low"],
                midpoint=(max(curr["open"], curr["close"]) + curr["low"]) / 2,
                direction="bullish", displaced=True,
            ))
        elif curr["close"] > curr["open"] and nxt["close"] < nxt["open"] and displaced:
            obs.append(OrderBlock(
                idx=i, timestamp=df.index[i],
                top=curr["high"],
                bottom=min(curr["open"], curr["close"]),
                midpoint=(curr["high"] + min(curr["open"], curr["close"])) / 2,
                direction="bearish", displaced=True,
            ))
    return obs


# ─── Market Structure Shift ───────────────────────────────────────────────────

def detect_mss(
    df: pd.DataFrame,
    swing_lookback: int = 3,
    require_displacement: bool = True,
) -> list:
    msses = []
    swings = detect_swing_points(df, swing_lookback)
    fvgs   = detect_fvg(df, require_displacement=False)
    sh_list = [(s.idx, s.price) for s in swings if s.kind == "high"]
    sl_list = [(s.idx, s.price) for s in swings if s.kind == "low"]

    for i in range(swing_lookback * 2 + 2, len(df)):
        close      = df["close"].iloc[i]
        prev_close = df["close"].iloc[i - 1]
        recent_sh  = [p for idx, p in sh_list if idx < i]
        recent_sl  = [p for idx, p in sl_list if idx < i]
        if not recent_sh or not recent_sl:
            continue
        last_sh = recent_sh[-1]
        last_sl = recent_sl[-1]
        displaced = _is_displaced(df, i) if require_displacement else True

        if close > last_sh and prev_close <= last_sh:
            rel_fvg = next(
                (f for f in reversed(fvgs)
                 if f.direction == "bullish" and f.idx < i and not f.filled), None)
            msses.append(MarketStructureShift(
                idx=i, timestamp=df.index[i],
                direction="bullish", broken_level=last_sh,
                displacement=displaced, fvg=rel_fvg,
            ))
        elif close < last_sl and prev_close >= last_sl:
            rel_fvg = next(
                (f for f in reversed(fvgs)
                 if f.direction == "bearish" and f.idx < i and not f.filled), None)
            msses.append(MarketStructureShift(
                idx=i, timestamp=df.index[i],
                direction="bearish", broken_level=last_sl,
                displacement=displaced, fvg=rel_fvg,
            ))
    return msses


# ─── Previous Day Levels ──────────────────────────────────────────────────────

def get_prev_day_levels(daily_df: pd.DataFrame, trade_date) -> Optional[PrevDayLevels]:
    prior = daily_df[daily_df.index.normalize() < pd.Timestamp(trade_date).normalize()]
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
    if len(session_df) < judas_window_bars:
        return None
    window       = session_df.iloc[:judas_window_bars]
    session_high = window["high"].max()
    session_low  = window["low"].min()

    # Bearish Judas — swept PDH, real move DOWN
    if session_high >= pdl.high - min_raid_pts:
        raid_bar = window["high"].idxmax()
        raid_idx = session_df.index.get_loc(raid_bar)
        return JudasSwing(
            idx=raid_idx, timestamp=raid_bar,
            direction="bearish",
            swept_level=pdl.high,
            reversal_price=float(session_df["close"].iloc[raid_idx]),
        )

    # Bullish Judas — swept PDL, real move UP
    if session_low <= pdl.low + min_raid_pts:
        raid_bar = window["low"].idxmin()
        raid_idx = session_df.index.get_loc(raid_bar)
        return JudasSwing(
            idx=raid_idx, timestamp=raid_bar,
            direction="bullish",
            swept_level=pdl.low,
            reversal_price=float(session_df["close"].iloc[raid_idx]),
        )

    return None


# ─── SMT Divergence ───────────────────────────────────────────────────────────

def detect_smt_divergence(
    primary_df: pd.DataFrame,
    secondary_df: pd.DataFrame,
    pdl: PrevDayLevels,
    window_bars: int = 12,
    min_divergence_pts: float = 3.0,
) -> bool:
    """
    SMT (Smart Money Technique) Divergence — compare two correlated instruments.

    Bullish SMT : primary makes LOWER low near PDL but secondary does NOT
                  → institutions defending primary, expect rally
    Bearish SMT : primary makes HIGHER high near PDH but secondary does NOT
                  → institutions distributing primary, expect selloff

    Typically: primary=MNQ, secondary=ES  (or primary=MGC, secondary=GC)
    """
    if secondary_df is None or secondary_df.empty:
        return False

    try:
        # Align both DataFrames to common timestamps
        common_idx = primary_df.index.intersection(secondary_df.index)
        if len(common_idx) < 4:
            return False

        p = primary_df.loc[common_idx].tail(window_bars)
        s = secondary_df.loc[common_idx].tail(window_bars)

        p_low  = p["low"].min()
        p_high = p["high"].max()
        s_low  = s["low"].min()
        s_high = s["high"].max()

        # Bearish SMT: primary makes new high near PDH, secondary fails to
        near_pdh = abs(p_high - pdl.high) / max(pdl.range_pts, 1) < 0.15
        if near_pdh:
            # Normalize to % range to compare across instruments
            p_high_pct = (p_high - p["close"].iloc[0]) / (p["high"].max() - p["low"].min() + 1e-9)
            s_high_pct = (s_high - s["close"].iloc[0]) / (s["high"].max() - s["low"].min() + 1e-9)
            if p_high_pct > s_high_pct + 0.05:    # primary extended, secondary lagging
                return True

        # Bullish SMT: primary makes new low near PDL, secondary holds higher
        near_pdl = abs(p_low - pdl.low) / max(pdl.range_pts, 1) < 0.15
        if near_pdl:
            p_low_pct = (p["close"].iloc[0] - p_low) / (p["high"].max() - p["low"].min() + 1e-9)
            s_low_pct = (s["close"].iloc[0] - s_low) / (s["high"].max() - s["low"].min() + 1e-9)
            if p_low_pct > s_low_pct + 0.05:      # primary weaker, secondary holding
                return True

    except Exception:
        return False

    return False


# ─── Premium / Discount Zone ──────────────────────────────────────────────────

def is_in_optimal_zone(
    entry_price: float,
    swing_high: float,
    swing_low: float,
    direction: str,
) -> bool:
    """
    Premium / Discount:
      Discount zone = below 50% of the range  → optimal for LONGS
      Premium zone  = above 50% of the range  → optimal for SHORTS
    """
    if swing_high <= swing_low:
        return False
    equilibrium = (swing_high + swing_low) / 2
    if direction == "long":
        return entry_price <= equilibrium      # in discount
    else:
        return entry_price >= equilibrium      # in premium


# ─── Higher Timeframe Alignment ───────────────────────────────────────────────

def is_htf_aligned(
    intraday_df: pd.DataFrame,
    direction: str,
    ema_period: int = 50,
    htf_rule: str = "15min",
) -> bool:
    """
    Resample 5-min bars to 15-min and check if price is on the correct
    side of the 50-EMA.

    Long  : close > 50-EMA on 15-min  (bullish trend)
    Short : close < 50-EMA on 15-min  (bearish trend)
    """
    try:
        htf = resample_to_htf(intraday_df, htf_rule)
        if len(htf) < ema_period:
            return True                        # not enough data — don't penalize
        ema = htf["close"].ewm(span=ema_period, adjust=False).mean()
        last_close = htf["close"].iloc[-1]
        last_ema   = ema.iloc[-1]
        if direction == "long":
            return last_close > last_ema
        else:
            return last_close < last_ema
    except Exception:
        return True                            # fail open


# ─── Setup Scoring ────────────────────────────────────────────────────────────

def score_setup(
    judas: Optional[JudasSwing],
    mss: Optional[MarketStructureShift],
    fvg: Optional[FairValueGap],
    entry_price: float,
    direction: str,
    intraday_df: pd.DataFrame,
    secondary_df: Optional[pd.DataFrame],
    pdl: Optional[PrevDayLevels],
    swing_high: float,
    swing_low: float,
) -> SetupScore:
    """
    Score an ICT setup 0–10. Returns SetupScore with .total and .grade.
    Minimum 8/10 = A+ trade (take it). Below 8 = skip.
    """
    s = SetupScore()

    # +2 Judas confirmed
    s.judas_confirmed = judas is not None

    # +2 MSS with displacement
    s.mss_displaced = (mss is not None and mss.displacement)

    # +1 FVG entry (not OB)
    s.fvg_entry = fvg is not None

    # +2 SMT divergence
    if pdl and secondary_df is not None:
        s.smt_divergence = detect_smt_divergence(
            intraday_df, secondary_df, pdl
        )

    # +1 HTF alignment
    s.htf_aligned = is_htf_aligned(intraday_df, direction)

    # +1 Entry in optimal zone (discount/premium)
    if swing_high > swing_low:
        s.in_optimal_zone = is_in_optimal_zone(
            entry_price, swing_high, swing_low, direction
        )

    # +1 FVG is first touch (never touched before)
    if fvg is not None:
        s.fvg_first_touch = not fvg.touched and not fvg.filled

    s.compute()
    return s
