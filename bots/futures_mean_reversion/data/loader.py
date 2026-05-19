"""
Data loading utilities.
Supports yfinance (free, good for daily bars), local CSV, and a stub for Rithmic/Tradovate tick data.

For production tick/minute data use:
  - Rithmic API (preferred for CME)
  - Tradovate WebSocket streaming
  - Databento (affordable historical tick data)
  - Norgate Data (daily, futures-adjusted)
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Map friendly symbols to yfinance tickers for daily data
YFINANCE_MAP = {
    "MES": "ES=F",   # E-mini S&P 500 (continuous)
    "ES":  "ES=F",
    "MNQ": "NQ=F",   # E-mini NASDAQ-100
    "NQ":  "NQ=F",
    "MYM": "YM=F",   # E-mini Dow
    "MCL": "CL=F",   # Crude Oil
    "MGC": "GC=F",   # Gold
    "MBT": "BTC=F",  # Bitcoin futures (CME)
}


def load_yfinance(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """
    Pull OHLCV from Yahoo Finance.
    interval: "1d" | "1h" | "30m" | "15m" | "5m"
    Note: intraday only goes back ~60 days on free tier.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("Run: pip install yfinance")

    ticker = YFINANCE_MAP.get(symbol.upper(), symbol)
    logger.info(f"Downloading {ticker} ({interval}) {start} → {end}")
    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)

    if df.empty:
        raise ValueError(f"No data returned for {ticker}. Check symbol/dates.")

    df.index = pd.to_datetime(df.index)
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    logger.info(f"Loaded {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
    return df


def load_csv(path: str, date_col: str = "date") -> pd.DataFrame:
    """
    Load OHLCV from a CSV file.
    Expected columns: date, open, high, low, close, volume
    Handles Norgate, Kinetick, and generic CSVs.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, parse_dates=[date_col], index_col=date_col)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    df = df.sort_index()
    df["volume"] = df.get("volume", 0).fillna(0)
    logger.info(f"Loaded {len(df)} bars from CSV: {path.name}")
    return df


def load_data(cfg) -> pd.DataFrame:
    """Main entry: route to correct loader based on config."""
    src = cfg.backtest.data_source.lower()

    if src == "yfinance":
        interval = "1d" if cfg.contract.data_timeframe == "1D" else "1h"
        return load_yfinance(
            cfg.contract.symbol,
            cfg.backtest.start_date,
            cfg.backtest.end_date,
            interval,
        )
    elif src == "csv":
        if not cfg.backtest.csv_path:
            raise ValueError("data_source='csv' requires backtest.csv_path to be set")
        return load_csv(cfg.backtest.csv_path)
    else:
        raise ValueError(f"Unknown data_source: {src}. Use 'yfinance' or 'csv'.")


def add_overnight_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark overnight gap bars — useful for filtering entries that occur
    right at open with a large gap (adverse slippage risk).
    """
    df = df.copy()
    df["overnight_gap"] = (df["open"] - df["close"].shift(1)).abs()
    df["gap_pct"] = df["overnight_gap"] / df["close"].shift(1)
    return df
