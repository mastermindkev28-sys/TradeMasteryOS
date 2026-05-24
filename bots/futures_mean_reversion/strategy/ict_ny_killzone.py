"""
ICT New York Kill Zone Strategy
=================================
Timeframe : 5-minute bars
Session   : 9:25 AM – 11:00 AM ET  (pre-market setup + NY Kill Zone)

Entry Logic
-----------
1. Pre-market  : fetch previous day H/L as liquidity targets
2. 9:30–9:50  : detect Judas Swing (liquidity raid on prev day H or L)
3. Post-Judas  : detect MSS with displacement confirming reversal
4. Entry       : limit order at FVG midpoint (or OB midpoint as fallback)
5. Stop        : 2 ticks beyond FVG/OB extreme (hard stop)
6. Target 1    : 50% of previous day range from entry  (scale out 50%)
7. Target 2    : opposite prev day H/L                 (runner 50%)

Signal output (for Telegram)
-----------------------------
  direction   : "long" | "short" | "no_setup"
  entry       : limit price
  stop        : stop loss price
  target1     : first partial target
  target2     : final target
  r_r         : reward:risk ratio
  reason      : human-readable setup description
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .ict_concepts import (
    FairValueGap,
    OrderBlock,
    JudasSwing,
    MarketStructureShift,
    PrevDayLevels,
    detect_fvg,
    detect_order_blocks,
    detect_mss,
    detect_judas_swing,
    get_prev_day_levels,
)

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

@dataclass
class ICTNYKillzoneConfig:
    # Session window (ET)
    session_start_hour: int = 9
    session_start_min: int = 25     # pre-market load
    killzone_start_hour: int = 9
    killzone_start_min: int = 30
    killzone_end_hour: int = 11
    killzone_end_min: int = 0

    # Judas detection
    judas_window_bars: int = 8       # first 40 min on 5-min chart
    min_raid_pts: float = 2.0        # min points beyond prev level

    # FVG / OB settings
    min_fvg_pts: float = 2.0
    displacement_mult: float = 1.5

    # Risk / R:R
    stop_ticks_beyond: int = 2       # ticks beyond FVG extreme for stop
    tick_size: float = 0.25          # MNQ tick size
    target1_rr: float = 2.0          # Target 1 R:R (scale 50%)
    target2_rr: float = 4.0          # Target 2 R:R (runner 50%)

    # Filters
    require_displacement_mss: bool = True
    skip_if_no_judas: bool = True    # only trade after confirmed Judas
    max_signals_per_day: int = 1     # 1 trade per day — ICT discipline


# ─── Signal Output ────────────────────────────────────────────────────────────

@dataclass
class ICTSignal:
    direction: str                   # "long" | "short" | "no_setup"
    entry: float = 0.0
    stop: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    r_r1: float = 0.0
    r_r2: float = 0.0
    stop_pts: float = 0.0
    setup_type: str = ""             # "fvg" | "ob" | "none"
    judas: Optional[JudasSwing] = None
    mss: Optional[MarketStructureShift] = None
    fvg: Optional[FairValueGap] = None
    pdl: Optional[PrevDayLevels] = None
    reason: str = "No setup today"
    timestamp: Optional[pd.Timestamp] = None

    @property
    def is_valid(self) -> bool:
        return self.direction in ("long", "short") and self.entry > 0


# ─── Strategy ─────────────────────────────────────────────────────────────────

class ICTNYKillzone:
    """
    Stateless ICT New York Kill Zone signal generator.
    Call `get_signal(intraday_5m_df, daily_df)` to get today's signal.
    """

    def __init__(self, cfg: ICTNYKillzoneConfig | None = None):
        self.cfg = cfg or ICTNYKillzoneConfig()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_signal(
        self,
        intraday_df: pd.DataFrame,
        daily_df: pd.DataFrame,
        trade_date=None,
    ) -> ICTSignal:
        """
        Analyse today's 5-min bars and return an ICTSignal.

        Parameters
        ----------
        intraday_df : 5-min OHLCV with DatetimeIndex (UTC or ET)
        daily_df    : daily OHLCV for prev-day levels
        trade_date  : date to analyse (defaults to latest date in intraday_df)
        """
        cfg = self.cfg

        if trade_date is None:
            trade_date = intraday_df.index[-1].date()

        # ── 1. Previous day levels ─────────────────────────────────────────────
        pdl = get_prev_day_levels(daily_df, trade_date)
        if pdl is None:
            return ICTSignal(direction="no_setup", reason="No previous day data")

        # ── 2. Slice today's session ──────────────────────────────────────────
        today_bars = intraday_df[intraday_df.index.date == trade_date].copy()
        if today_bars.empty:
            return ICTSignal(direction="no_setup", reason="No intraday data for today")

        # Kill zone slice only
        kz = today_bars.between_time(
            f"{cfg.killzone_start_hour:02d}:{cfg.killzone_start_min:02d}",
            f"{cfg.killzone_end_hour:02d}:{cfg.killzone_end_min:02d}",
        )
        if len(kz) < 4:
            return ICTSignal(direction="no_setup", reason="Insufficient kill zone bars")

        # ── 3. Judas Swing ────────────────────────────────────────────────────
        judas = detect_judas_swing(kz, pdl, cfg.judas_window_bars, cfg.min_raid_pts)

        if judas is None and cfg.skip_if_no_judas:
            return ICTSignal(
                direction="no_setup",
                pdl=pdl,
                reason=f"No Judas Swing detected  |  PDH: {pdl.high:.2f}  PDL: {pdl.low:.2f}",
            )

        # ── 4. Post-Judas bars (where MSS should form) ───────────────────────
        if judas:
            post_judas = kz.iloc[judas.idx:]
        else:
            post_judas = kz

        if len(post_judas) < 3:
            return ICTSignal(direction="no_setup", pdl=pdl, reason="Judas detected but no post-Judas bars yet")

        # ── 5. MSS Detection ──────────────────────────────────────────────────
        msses = detect_mss(post_judas, require_displacement=cfg.require_displacement_mss)

        # Filter: MSS direction must align with Judas (Judas bearish → MSS bearish, etc.)
        if judas:
            msses = [m for m in msses if m.direction == judas.direction]

        if not msses:
            return ICTSignal(
                direction="no_setup",
                pdl=pdl,
                judas=judas,
                reason=(
                    f"Judas {'⬆️' if judas and judas.direction=='bearish' else '⬇️'} detected"
                    f" at {judas.swept_level:.2f} — waiting for MSS"
                    if judas else "No MSS yet"
                ),
            )

        mss = msses[-1]  # most recent MSS

        # ── 6. FVG entry ──────────────────────────────────────────────────────
        fvgs = detect_fvg(post_judas, min_gap_pts=cfg.min_fvg_pts, require_displacement=True)
        # FVG must be in same direction as MSS and appear before MSS
        valid_fvgs = [
            f for f in fvgs
            if f.direction == mss.direction and f.idx < mss.idx and not f.filled
        ]

        # Fallback to Order Blocks if no FVG
        obs = detect_order_blocks(post_judas, cfg.displacement_mult)
        valid_obs = [
            o for o in obs
            if o.direction == mss.direction and o.idx < mss.idx
        ]

        # Pick best entry zone (FVG preferred, OB fallback)
        entry_zone = None
        setup_type = "none"

        if valid_fvgs:
            entry_zone = valid_fvgs[-1]   # most recent unfilled FVG
            setup_type = "fvg"
        elif valid_obs:
            entry_zone = valid_obs[-1]
            setup_type = "ob"

        if entry_zone is None:
            return ICTSignal(
                direction="no_setup",
                pdl=pdl,
                judas=judas,
                mss=mss,
                reason=f"MSS {'🟢' if mss.direction=='bullish' else '🔴'} confirmed — no FVG/OB entry zone yet",
            )

        # ── 7. Build trade levels ─────────────────────────────────────────────
        tick = cfg.tick_size
        stop_buffer = cfg.stop_ticks_beyond * tick

        if mss.direction == "bullish":
            direction  = "long"
            entry      = entry_zone.midpoint
            stop       = entry_zone.bottom - stop_buffer
            stop_pts   = entry - stop
            target1    = entry + stop_pts * cfg.target1_rr
            target2    = pdl.high   # opposite liquidity
            # Prefer prev day high as T2 if it gives better R:R
            t2_pts = pdl.high - entry
            if t2_pts < stop_pts:       # PDH too close — use R:R based target
                target2 = entry + stop_pts * cfg.target2_rr
        else:
            direction  = "short"
            entry      = entry_zone.midpoint
            stop       = entry_zone.top + stop_buffer
            stop_pts   = stop - entry
            target1    = entry - stop_pts * cfg.target1_rr
            target2    = pdl.low    # opposite liquidity
            t2_pts = entry - pdl.low
            if t2_pts < stop_pts:
                target2 = entry - stop_pts * cfg.target2_rr

        r_r1 = round(abs(target1 - entry) / stop_pts, 2) if stop_pts > 0 else 0
        r_r2 = round(abs(target2 - entry) / stop_pts, 2) if stop_pts > 0 else 0

        emoji = "🟢" if direction == "long" else "🔴"
        reason = (
            f"{emoji} {direction.upper()} | {setup_type.upper()} entry\n"
            f"Judas swept {'PDH' if judas and judas.direction == 'bearish' else 'PDL'} "
            f"@ {judas.swept_level:.2f} → MSS {mss.direction} confirmed\n"
            f"Entry zone: {entry_zone.bottom:.2f} – {entry_zone.top:.2f} "
            f"({'FVG' if setup_type == 'fvg' else 'OB'})"
        )

        return ICTSignal(
            direction=direction,
            entry=round(entry, 2),
            stop=round(stop, 2),
            target1=round(target1, 2),
            target2=round(target2, 2),
            r_r1=r_r1,
            r_r2=r_r2,
            stop_pts=round(stop_pts, 2),
            setup_type=setup_type,
            judas=judas,
            mss=mss,
            fvg=entry_zone if setup_type == "fvg" else None,
            pdl=pdl,
            reason=reason,
            timestamp=post_judas.index[mss.idx] if mss.idx < len(post_judas) else None,
        )

    # ── Backtesting helper ────────────────────────────────────────────────────

    def generate_daily_signals(
        self,
        intraday_df: pd.DataFrame,
        daily_df: pd.DataFrame,
    ) -> list[ICTSignal]:
        """Generate one signal per trading day for backtesting."""
        signals = []
        trading_days = sorted(set(intraday_df.index.date))

        for day in trading_days:
            sig = self.get_signal(intraday_df, daily_df, day)
            signals.append(sig)

        return signals
