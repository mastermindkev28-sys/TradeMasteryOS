"""
ICT New York Kill Zone Strategy — A+ Filter Edition
=====================================================
Timeframe : 5-minute bars
Sessions  : Asia Kill Zone   8:00 PM–midnight ET  (new)
            London Kill Zone 2:00–5:00 AM ET       (new)
            NY Kill Zone     9:30–11:00 AM ET       (primary)
            Silver Bullet    10:00–11:00 AM ET      (backup window 1)
            Silver Bullet    2:00– 3:00 PM ET       (backup window 2)
            NY Afternoon     1:30–4:00 PM ET        (new)

A+ Setup Requirements (8/10 minimum score)
-------------------------------------------
  judas_confirmed   +2   liquidity raid + reversal
  mss_displaced     +2   impulsive structure break
  fvg_entry         +1   FVG (not just OB)
  smt_divergence    +2   MNQ vs ES divergence at swept level
  htf_aligned       +1   15-min 50-EMA trend agreement
  in_optimal_zone   +1   entry in discount (long) or premium (short)
  fvg_first_touch   +1   FVG never previously touched

Only trades scoring 8+ are sent as signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .ict_concepts import (
    FairValueGap, OrderBlock, JudasSwing,
    MarketStructureShift, PrevDayLevels, SetupScore,
    detect_fvg, detect_order_blocks, detect_mss,
    detect_judas_swing, get_prev_day_levels,
    score_setup, detect_swing_points, mark_fvg_touches,
)

logger = logging.getLogger(__name__)


@dataclass
class ICTNYKillzoneConfig:
    # NY Kill Zone (primary)
    killzone_start: str        = "09:30"
    killzone_end: str          = "11:00"
    # Silver Bullet sessions
    silver_bullet_1_start: str = "10:00"
    silver_bullet_1_end: str   = "11:00"
    silver_bullet_2_start: str = "14:00"
    silver_bullet_2_end: str   = "15:00"
    # London Kill Zone (new)
    london_kz_start: str       = "02:00"
    london_kz_end: str         = "05:00"
    # NY Afternoon / PM session (new)
    ny_pm_start: str           = "13:30"
    ny_pm_end: str             = "16:00"
    # Asia Kill Zone (new)
    asia_kz_start: str         = "20:00"
    asia_kz_end: str           = "23:59"
    # Risk params (keep existing)
    judas_window_bars: int     = 8
    min_raid_pts: float        = 2.0
    min_fvg_pts: float         = 2.0
    displacement_mult: float   = 1.5
    stop_ticks_beyond: int     = 2
    tick_size: float           = 0.25
    target1_rr: float          = 2.0
    target2_rr: float          = 4.0
    min_score: int             = 8
    require_displacement_mss: bool = True
    max_signals_per_day: int   = 5


@dataclass
class ICTSignal:
    direction: str
    entry: float     = 0.0
    stop: float      = 0.0
    target1: float   = 0.0
    target2: float   = 0.0
    r_r1: float      = 0.0
    r_r2: float      = 0.0
    stop_pts: float  = 0.0
    setup_type: str  = ""
    window: str      = ""
    score: Optional[SetupScore] = None
    judas: Optional[JudasSwing] = None
    mss:   Optional[MarketStructureShift] = None
    fvg:   Optional[FairValueGap] = None
    pdl:   Optional[PrevDayLevels] = None
    reason: str      = "No setup today"
    timestamp: Optional[pd.Timestamp] = None

    @property
    def is_valid(self) -> bool:
        return self.direction in ("long", "short") and self.entry > 0

    @property
    def grade(self) -> str:
        return self.score.grade if self.score else "—"


class ICTNYKillzone:

    def __init__(self, cfg: ICTNYKillzoneConfig | None = None):
        self.cfg = cfg or ICTNYKillzoneConfig()

    def _all_windows(self) -> list:
        """All session windows ordered by time of day."""
        return [
            ("asia_killzone",   self.cfg.asia_kz_start,         self.cfg.asia_kz_end,         True),
            ("london_killzone", self.cfg.london_kz_start,       self.cfg.london_kz_end,       True),
            ("ny_killzone",     self.cfg.killzone_start,         self.cfg.killzone_end,        True),
            ("silver_bullet_1", self.cfg.silver_bullet_1_start, self.cfg.silver_bullet_1_end, False),
            ("silver_bullet_2", self.cfg.silver_bullet_2_start, self.cfg.silver_bullet_2_end, False),
            ("ny_pm",           self.cfg.ny_pm_start,           self.cfg.ny_pm_end,           False),
        ]

    def scan_all_windows(
        self,
        intraday_df: pd.DataFrame,
        daily_df: pd.DataFrame,
        secondary_df: Optional[pd.DataFrame] = None,
        trade_date=None,
    ) -> list:
        """Scan all session windows. Returns list of all valid A+ ICTSignals found."""
        if trade_date is None:
            trade_date = intraday_df.index[-1].date()

        pdl = get_prev_day_levels(daily_df, trade_date)
        if pdl is None:
            return []

        today = intraday_df[intraday_df.index.date == trade_date].copy()
        if today.empty:
            return []

        signals = []
        for win_name, start, end, use_judas in self._all_windows():
            try:
                wbars = today.between_time(start, end)
            except Exception:
                continue
            if len(wbars) < 4:
                continue
            sig = self._scan_window(wbars, pdl, today, secondary_df, win_name, use_judas)
            if sig.is_valid and sig.score and sig.score.is_aplus:
                sig.window = win_name
                signals.append(sig)
            if len(signals) >= self.cfg.max_signals_per_day:
                break

        return signals

    def get_signal(
        self,
        intraday_df: pd.DataFrame,
        daily_df: pd.DataFrame,
        secondary_df: Optional[pd.DataFrame] = None,
        trade_date=None,
    ) -> ICTSignal:
        if trade_date is None:
            trade_date = intraday_df.index[-1].date()

        pdl = get_prev_day_levels(daily_df, trade_date)
        if pdl is None:
            return ICTSignal(direction="no_setup", reason="No previous day data")

        today = intraday_df[intraday_df.index.date == trade_date].copy()
        if today.empty:
            return ICTSignal(direction="no_setup", reason="No intraday data for today")

        windows = self._all_windows()

        best: Optional[ICTSignal] = None

        for win_name, start, end, use_judas in windows:
            wbars = today.between_time(start, end)
            if len(wbars) < 4:
                continue
            sig = self._scan_window(wbars, pdl, today, secondary_df, win_name, use_judas)
            if sig.is_valid and sig.score and sig.score.is_aplus:
                sig.window = win_name
                return sig
            if sig.score and (best is None or sig.score.total > (best.score.total if best.score else 0)):
                best = sig

        if best:
            best.direction = "no_setup"
            sc = f"Score {best.score.total}/10 ({best.grade})" if best.score else ""
            best.reason = f"No A+ setup today — {sc}"
            return best

        return ICTSignal(
            direction="no_setup", pdl=pdl,
            reason=f"No setup in any window  |  PDH: {pdl.high:.2f}  PDL: {pdl.low:.2f}",
        )

    def _scan_window(self, window_df, pdl, full_today, secondary_df, win_name, use_judas):
        cfg = self.cfg

        judas = None
        if use_judas:
            judas = detect_judas_swing(window_df, pdl, cfg.judas_window_bars, cfg.min_raid_pts)
            if judas is None:
                return ICTSignal(direction="no_setup", window=win_name, pdl=pdl,
                                 reason=f"[{win_name}] No Judas Swing")

        analysis_df = window_df.iloc[judas.idx:] if judas else window_df
        if len(analysis_df) < 3:
            return ICTSignal(direction="no_setup", window=win_name, pdl=pdl,
                             reason=f"[{win_name}] Insufficient bars after Judas")

        msses = detect_mss(analysis_df, require_displacement=cfg.require_displacement_mss)
        if judas:
            msses = [m for m in msses if m.direction == judas.direction]
        if not msses:
            s = SetupScore(); s.judas_confirmed = judas is not None; s.compute()
            return ICTSignal(direction="no_setup", window=win_name, pdl=pdl,
                             score=s, judas=judas,
                             reason=f"[{win_name}] Judas ✅ — waiting for MSS")

        mss = msses[-1]
        fvgs = detect_fvg(analysis_df, min_gap_pts=cfg.min_fvg_pts, require_displacement=True)
        mark_fvg_touches(fvgs, analysis_df)
        valid_fvgs = [f for f in fvgs if f.direction == mss.direction and f.idx < mss.idx and not f.filled]
        obs = detect_order_blocks(analysis_df, cfg.displacement_mult)
        valid_obs  = [o for o in obs  if o.direction == mss.direction and o.idx < mss.idx]

        entry_zone = None
        setup_type = "none"
        if valid_fvgs:
            entry_zone = valid_fvgs[-1]; setup_type = "fvg"
        elif valid_obs:
            entry_zone = valid_obs[-1];  setup_type = "ob"

        if entry_zone is None:
            s = SetupScore(); s.judas_confirmed = judas is not None; s.mss_displaced = mss.displacement; s.compute()
            return ICTSignal(direction="no_setup", window=win_name, pdl=pdl,
                             score=s, judas=judas, mss=mss,
                             reason=f"[{win_name}] MSS ✅ — no FVG/OB yet")

        tick     = cfg.tick_size
        stop_buf = cfg.stop_ticks_beyond * tick
        fvg_obj  = entry_zone if setup_type == "fvg" else None

        if mss.direction == "bullish":
            direction = "long"
            entry    = entry_zone.midpoint
            stop     = entry_zone.bottom - stop_buf
            stop_pts = entry - stop
            target1  = entry + stop_pts * cfg.target1_rr
            target2  = pdl.high if (pdl.high - entry) > stop_pts else entry + stop_pts * cfg.target2_rr
        else:
            direction = "short"
            entry    = entry_zone.midpoint
            stop     = entry_zone.top + stop_buf
            stop_pts = stop - entry
            target1  = entry - stop_pts * cfg.target1_rr
            target2  = pdl.low  if (entry - pdl.low) > stop_pts  else entry - stop_pts * cfg.target2_rr

        r_r1 = round(abs(target1 - entry) / stop_pts, 2) if stop_pts > 0 else 0
        r_r2 = round(abs(target2 - entry) / stop_pts, 2) if stop_pts > 0 else 0

        swings     = detect_swing_points(analysis_df, 3)
        sh         = [s.price for s in swings if s.kind == "high"]
        sl         = [s.price for s in swings if s.kind == "low"]
        swing_high = max(sh) if sh else pdl.high
        swing_low  = min(sl) if sl else pdl.low

        setup_score = score_setup(
            judas=judas, mss=mss, fvg=fvg_obj,
            entry_price=entry, direction=direction,
            intraday_df=full_today, secondary_df=secondary_df,
            pdl=pdl, swing_high=swing_high, swing_low=swing_low,
        )

        emoji = "🟢" if direction == "long" else "🔴"
        if setup_score.is_aplus:
            reason = f"{emoji} {direction.upper()} | {setup_type.upper()} | Score {setup_score.total}/10 ({setup_score.grade})"
        else:
            reason = f"[{win_name}] Score {setup_score.total}/10 ({setup_score.grade}) — below minimum {cfg.min_score}"

        return ICTSignal(
            direction=direction if setup_score.is_aplus else "no_setup",
            entry=round(entry, 2), stop=round(stop, 2),
            target1=round(target1, 2), target2=round(target2, 2),
            r_r1=r_r1, r_r2=r_r2, stop_pts=round(stop_pts, 2),
            setup_type=setup_type, window=win_name,
            score=setup_score, judas=judas, mss=mss, fvg=fvg_obj, pdl=pdl,
            reason=reason,
            timestamp=analysis_df.index[mss.idx] if mss.idx < len(analysis_df) else None,
        )

    def generate_daily_signals(self, intraday_df, daily_df, secondary_df=None):
        return [
            self.get_signal(intraday_df, daily_df, secondary_df, day)
            for day in sorted(set(intraday_df.index.date))
        ]
