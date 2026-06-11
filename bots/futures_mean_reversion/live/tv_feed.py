"""
Market data feed for CME futures.
Uses yfinance (Yahoo Finance) — futures tickers are real-time on Yahoo.
Interface is source-agnostic so the underlying feed can be swapped later.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Internal symbol → Yahoo Finance ticker
_YAHOO_MAP: dict[str, str] = {
    "MNQ": "NQ=F",
    "MES": "ES=F",
    "MGC": "GC=F",
    "MCL": "CL=F",
    "NQ":  "NQ=F",
    "ES":  "ES=F",
    "GC":  "GC=F",
}


def _clean(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def fetch_intraday(symbol: str, interval_minutes: int = 5, n_bars: int = 500) -> Optional[pd.DataFrame]:
    """Fetch intraday bars (default 5-min) for a futures symbol."""
    import yfinance as yf
    ticker = _YAHOO_MAP.get(symbol, symbol)
    interval_str = f"{interval_minutes}m"
    # yfinance max period for intraday: 60d for >=2m intervals
    period = "5d" if interval_minutes <= 30 else "1mo"
    try:
        df = yf.download(ticker, period=period, interval=interval_str,
                         auto_adjust=True, progress=False)
        return _clean(df)
    except Exception as e:
        logger.error(f"Intraday fetch failed for {symbol}: {e}")
        return None


def fetch_daily(symbol: str, n_bars: int = 120) -> Optional[pd.DataFrame]:
    """Fetch daily bars for a futures symbol."""
    import yfinance as yf
    ticker = _YAHOO_MAP.get(symbol, symbol)
    try:
        df = yf.download(ticker, period="1y", interval="1d",
                         auto_adjust=True, progress=False)
        result = _clean(df)
        return result.tail(n_bars) if result is not None else None
    except Exception as e:
        logger.error(f"Daily fetch failed for {symbol}: {e}")
        return None
