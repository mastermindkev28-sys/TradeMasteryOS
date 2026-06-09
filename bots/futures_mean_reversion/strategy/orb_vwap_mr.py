"""
ORB + VWAP Mean Reversion Strategy
=====================================
Two complementary intraday signals for the NY session (9:00–10:50 ET).

Signal 1 — Opening Range Breakout (ORB)
  Range window : 9:00–9:30 ET  (pre-market range, captures overnight structure)
  Trade window : 9:30–10:50 ET
  Filters      : VWAP side + EMA20 alignment + RSI 45–55 (neutral) + volume spike
  Targets      : TP1 @ 1.5R (50% exit), TP2 @ 2.5R (let rest run)

Signal 2 — VWAP Mean Reversion (VWAP_MR)
  Condition    : Price ≥ 2×ATR from VWAP in a low-trend environment
  Filters      : ADX < 22 (ranging) + RSI extreme (<45 long / >55 short)
  Target       : Return to VWAP  |  SL = 1×ATR from entry
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ORBVWAPConfig:
    # Opening range window
    or_start: str          = "09:00"
    or_end: str            = "09:30"
    trade_end: str         = "10:50"
    or_min_range_pts: float = 1.5

    # ORB entry filters
    rsi_low: int           = 45     # RSI must be between these (not overbought)
    rsi_high: int          = 55
    volume_mult: float     = 1.2    # current bar volume > 1.2× 20-bar avg
    ema_period: int        = 20
    rsi_period: int        = 14
    atr_period: int        = 14
    adx_period: int        = 14

    # VWAP MR filters
    vwap_deviation_atr: float = 2.0  # must be ≥ 2×ATR from VWAP
    adx_max: float            = 22.0
    rsi_mr_long: int          = 45   # RSI < 45 for long MR
    rsi_mr_short: int         = 55   # RSI > 55 for short MR

    # Stop / target ratios
    stop_atr_mult: float  = 1.0
    tp1_r: float          = 1.5
    tp2_r: float          = 2.5


@dataclass
class ORBSignal:
    direction: str          # "long" | "short" | "no_signal"
    entry: float    = 0.0
    stop: float     = 0.0
    target1: float  = 0.0   # 1.5R — scale 50% out
    target2: float  = 0.0   # 2.5R — let rest run
    r_r1: float     = 0.0
    r_r2: float     = 0.0
    or_high: float  = 0.0
    or_low: float   = 0.0
    atr: float      = 0.0
    vwap: float     = 0.0
    rsi: float      = 0.0
    reason: str     = ""

    @property
    def is_valid(self) -> bool:
        return self.direction in ("long", "short") and self.entry > 0


@dataclass
class VWAPMRSignal:
    direction: str          # "long" | "short" | "no_signal"
    entry: float         = 0.0
    stop: float          = 0.0
    target: float        = 0.0   # VWAP level
    vwap: float          = 0.0
    deviation_pts: float = 0.0
    atr: float           = 0.0
    adx: float           = 0.0
    rsi: float           = 0.0
    reason: str          = ""

    @property
    def is_valid(self) -> bool:
        return self.direction in ("long", "short") and self.entry > 0


class ORBVWAPStrategy:

    def __init__(self, cfg: ORBVWAPConfig | None = None):
        self.cfg = cfg or ORBVWAPConfig()

    # ── Indicators ─────────────────────────────────────────────────────

    @staticmethod
    def _vwap(df: pd.DataFrame) -> pd.Series:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        vol = df["volume"].replace(0, np.nan)
        return (tp * vol).cumsum() / vol.cumsum()

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain  = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
        return 100 - 100 / (1 + gain / (loss + 1e-9))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"]  - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        hl  = df["high"] - df["low"]
        hc  = (df["high"] - df["close"].shift()).abs()
        lc  = (df["low"]  - df["close"].shift()).abs()
        tr  = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        up  = df["high"] - df["high"].shift()
        dn  = df["low"].shift() - df["low"]
        pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
        ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
        atr_s = tr.ewm(span=period, adjust=False).mean()
        pdi   = 100 * pdm.ewm(span=period, adjust=False).mean() / (atr_s + 1e-9)
        ndi   = 100 * ndm.ewm(span=period, adjust=False).mean() / (atr_s + 1e-9)
        dx    = 100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)
        return dx.ewm(span=period, adjust=False).mean()

    # ── Opening Range ──────────────────────────────────────────────────

    def get_opening_range(
        self,
        df: pd.DataFrame,
        trade_date,
    ) -> tuple[float, float] | None:
        """Return (or_high, or_low) for the 9:00–9:30 ET window, or None."""
        day  = df[df.index.date == trade_date]
        bars = day.between_time(self.cfg.or_start, self.cfg.or_end)
        if len(bars) < 2:
            return None
        orh = float(bars["high"].max())
        orl = float(bars["low"].min())
        if (orh - orl) < self.cfg.or_min_range_pts:
            return None
        return orh, orl

    # ── ORB Signal ─────────────────────────────────────────────────────

    def get_orb_signal(
        self,
        df: pd.DataFrame,
        or_high: float,
        or_low: float,
        trade_date,
    ) -> ORBSignal:
        cfg = self.cfg
        day        = df[df.index.date == trade_date]
        trade_bars = day.between_time(cfg.or_end, cfg.trade_end)
        if trade_bars.empty:
            return ORBSignal(direction="no_signal", reason="No bars in trade window")

        vwap    = self._vwap(day)
        rsi     = self._rsi(day["close"], cfg.rsi_period)
        atr     = self._atr(day, cfg.atr_period)
        ema20   = day["close"].ewm(span=cfg.ema_period, adjust=False).mean()
        vol_avg = day["volume"].rolling(20, min_periods=5).mean()

        for ts, row in trade_bars.iterrows():
            c      = float(row["close"])
            v      = float(vwap.get(ts, 0) or 0)
            r      = float(rsi.get(ts, 50) or 50)
            e20    = float(ema20.get(ts, 0) or 0)
            a      = float(atr.get(ts, 0) or 0)
            vol    = float(row["volume"])
            va     = float(vol_avg.get(ts, 0) or 0)
            v_ok   = vol > va * cfg.volume_mult if va > 0 else False

            if a <= 0:
                continue

            # Long: break above OR high
            if (c > or_high and v > 0 and c > v and c > e20
                    and cfg.rsi_low <= r <= cfg.rsi_high and v_ok):
                stop = or_high - a * cfg.stop_atr_mult
                risk = c - stop
                if risk <= 0:
                    continue
                return ORBSignal(
                    direction="long",
                    entry=round(c, 2), stop=round(stop, 2),
                    target1=round(c + risk * cfg.tp1_r, 2),
                    target2=round(c + risk * cfg.tp2_r, 2),
                    r_r1=cfg.tp1_r, r_r2=cfg.tp2_r,
                    or_high=or_high, or_low=or_low,
                    atr=round(a, 2), vwap=round(v, 2), rsi=round(r, 1),
                    reason=f"ORB long — broke above {or_high:.2f}",
                )

            # Short: break below OR low
            if (c < or_low and v > 0 and c < v and c < e20
                    and cfg.rsi_low <= r <= cfg.rsi_high and v_ok):
                stop = or_low + a * cfg.stop_atr_mult
                risk = stop - c
                if risk <= 0:
                    continue
                return ORBSignal(
                    direction="short",
                    entry=round(c, 2), stop=round(stop, 2),
                    target1=round(c - risk * cfg.tp1_r, 2),
                    target2=round(c - risk * cfg.tp2_r, 2),
                    r_r1=cfg.tp1_r, r_r2=cfg.tp2_r,
                    or_high=or_high, or_low=or_low,
                    atr=round(a, 2), vwap=round(v, 2), rsi=round(r, 1),
                    reason=f"ORB short — broke below {or_low:.2f}",
                )

        return ORBSignal(
            direction="no_signal", or_high=or_high, or_low=or_low,
            reason="No valid ORB breakout — filters not satisfied",
        )

    # ── VWAP MR Signal ─────────────────────────────────────────────────

    def get_vwap_mr_signal(
        self,
        df: pd.DataFrame,
        trade_date,
    ) -> VWAPMRSignal:
        cfg  = self.cfg
        day  = df[df.index.date == trade_date]
        bars = day.between_time(cfg.or_end, cfg.trade_end)
        if len(bars) < 5:
            return VWAPMRSignal(direction="no_signal", reason="Insufficient bars in window")

        vwap = self._vwap(day)
        rsi  = self._rsi(day["close"], cfg.rsi_period)
        atr  = self._atr(day, cfg.atr_period)
        adx  = self._adx(day, cfg.adx_period)

        ts  = bars.index[-1]
        c   = float(bars["close"].iloc[-1])
        v   = float(vwap.get(ts, 0) or 0)
        r   = float(rsi.get(ts, 50) or 50)
        a   = float(atr.get(ts, 0) or 0)
        dx  = float(adx.get(ts, 100) or 100)

        if a <= 0 or v <= 0:
            return VWAPMRSignal(direction="no_signal", reason="Indicators unavailable")

        deviation = c - v
        dev_pts   = abs(deviation)
        threshold = cfg.vwap_deviation_atr * a

        if dev_pts < threshold:
            return VWAPMRSignal(
                direction="no_signal", vwap=round(v, 2), adx=round(dx, 1),
                rsi=round(r, 1), atr=round(a, 2), deviation_pts=round(dev_pts, 1),
                reason=f"Deviation {dev_pts:.1f} pts < {threshold:.1f} threshold ({cfg.vwap_deviation_atr}×ATR)",
            )

        if dx >= cfg.adx_max:
            return VWAPMRSignal(
                direction="no_signal", vwap=round(v, 2), adx=round(dx, 1),
                reason=f"ADX {dx:.1f} ≥ {cfg.adx_max} — trending market, skip MR",
            )

        if deviation < 0 and r < cfg.rsi_mr_long:
            stop = c - a * cfg.stop_atr_mult
            return VWAPMRSignal(
                direction="long",
                entry=round(c, 2), stop=round(stop, 2), target=round(v, 2),
                vwap=round(v, 2), deviation_pts=round(dev_pts, 1),
                atr=round(a, 2), adx=round(dx, 1), rsi=round(r, 1),
                reason=f"VWAP MR long — {dev_pts:.1f} pts below VWAP, RSI {r:.0f}, ADX {dx:.0f}",
            )

        if deviation > 0 and r > cfg.rsi_mr_short:
            stop = c + a * cfg.stop_atr_mult
            return VWAPMRSignal(
                direction="short",
                entry=round(c, 2), stop=round(stop, 2), target=round(v, 2),
                vwap=round(v, 2), deviation_pts=round(dev_pts, 1),
                atr=round(a, 2), adx=round(dx, 1), rsi=round(r, 1),
                reason=f"VWAP MR short — {dev_pts:.1f} pts above VWAP, RSI {r:.0f}, ADX {dx:.0f}",
            )

        return VWAPMRSignal(
            direction="no_signal", vwap=round(v, 2), adx=round(dx, 1),
            rsi=round(r, 1), atr=round(a, 2), deviation_pts=round(dev_pts, 1),
            reason=f"Stretched from VWAP but RSI {r:.0f} not extreme enough",
        )
