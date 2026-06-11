"""
TradingView data feed via tvDatafeed.
Provides intraday and daily OHLCV for CME futures — replaces yfinance.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# symbol key → (TradingView ticker, exchange)
TV_SYMBOL_MAP: dict[str, tuple[str, str]] = {
    "MNQ":  ("MNQ1!", "CME_MINI"),
    "MES":  ("MES1!", "CME_MINI"),
    "MGC":  ("MGC1!", "COMEX"),
    "MCL":  ("MCL1!", "NYMEX"),
    # Full contracts used as SMT divergence pairs
    "NQ":   ("NQ1!",  "CME_MINI"),
    "ES":   ("ES1!",  "CME_MINI"),
    "GC":   ("GC1!",  "COMEX"),
}

_tv_client = None


def _client():
    global _tv_client
    if _tv_client is None:
        from tvDatafeed import TvDatafeed
        # Anonymous login — no credentials needed for CME futures data
        _tv_client = TvDatafeed()
    return _tv_client


def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize tvDatafeed frame → standard lowercase OHLCV with ET DatetimeIndex."""
    if df is None or df.empty:
        return df
    df = df.drop(columns=["symbol"], errors="ignore")
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def fetch_intraday(symbol: str, interval_minutes: int = 5, n_bars: int = 500) -> Optional[pd.DataFrame]:
    """Fetch intraday bars from TradingView (defaults to 5-min, last 500 bars)."""
    from tvDatafeed import Interval
    _MAP = {
        1:  Interval.in_1_minute,
        3:  Interval.in_3_minute,
        5:  Interval.in_5_minute,
        15: Interval.in_15_minute,
        30: Interval.in_30_minute,
        60: Interval.in_1_hour,
    }
    tv_sym, exchange = TV_SYMBOL_MAP.get(symbol, (symbol, "CME_MINI"))
    try:
        df = _client().get_hist(tv_sym, exchange, interval=_MAP.get(interval_minutes, Interval.in_5_minute), n_bars=n_bars)
        return _to_et(df)
    except Exception as e:
        logger.error(f"TV intraday fetch failed for {symbol}: {e}")
        return None


def fetch_daily(symbol: str, n_bars: int = 120) -> Optional[pd.DataFrame]:
    """Fetch daily bars from TradingView (last 120 trading days)."""
    from tvDatafeed import Interval
    tv_sym, exchange = TV_SYMBOL_MAP.get(symbol, (symbol, "CME_MINI"))
    try:
        df = _client().get_hist(tv_sym, exchange, interval=Interval.in_daily, n_bars=n_bars)
        return _to_et(df)
    except Exception as e:
        logger.error(f"TV daily fetch failed for {symbol}: {e}")
        return None
