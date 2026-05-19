"""
GoldMaster Pro — Configuration
Central config for all modules.
"""
import os
from dataclasses import dataclass, field
from typing import List

# ─────────────────────────────────────────────
# ACCOUNT & RISK
# ─────────────────────────────────────────────
ACCOUNT_SIZE         = float(os.getenv("ACCOUNT_SIZE",        "100000"))
RISK_PER_TRADE_PCT   = float(os.getenv("RISK_PER_TRADE_PCT",  "0.75"))    # 0.75% = $750 on $100K
MAX_DAILY_LOSS_PCT   = float(os.getenv("MAX_DAILY_LOSS_PCT",  "3.0"))     # 3% = $3,000
MAX_TOTAL_DD_PCT     = float(os.getenv("MAX_TOTAL_DD_PCT",    "6.0"))     # 6% = $6,000
MIN_RR               = float(os.getenv("MIN_RR",              "2.0"))
MAX_TRADES_PER_DAY   = int(os.getenv("MAX_TRADES_PER_DAY",    "3"))
PROP_FIRM_MODE       = os.getenv("PROP_FIRM_MODE", "true").lower() == "true"

# Weekly targets
WEEKLY_TARGET_LOW    = 1000.0   # $1,000 per week minimum
WEEKLY_TARGET_HIGH   = 1500.0   # $1,500 per week target

# ─────────────────────────────────────────────
# SYMBOL
# ─────────────────────────────────────────────
SYMBOL               = "XAUUSD"
PIP_VALUE_PER_LOT    = 1.0      # $1 per pip per standard lot for XAUUSD
PIP_SIZE             = 0.01     # 1 pip = $0.01 for XAUUSD

# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
ATR_PERIOD           = 14
SL_ATR_MULT          = 1.5
TP_ATR_MULT          = 3.5
EMA_FAST             = 9
EMA_MID              = 21
EMA_SLOW             = 50
EMA_TREND            = 200
RSI_PERIOD           = 14
RSI_OB               = 70
RSI_OS               = 30
ADX_PERIOD           = 14
ADX_MIN              = 20
VOL_FILTER_MULT      = 1.3
MIN_SIGNAL_SCORE     = 65

# ─────────────────────────────────────────────
# SESSION HOURS (UTC)
# ─────────────────────────────────────────────
LONDON_OPEN_UTC      = 7
LONDON_CLOSE_UTC     = 16
NY_OPEN_UTC          = 13
NY_CLOSE_UTC         = 20
ASIAN_OPEN_UTC       = 0
ASIAN_CLOSE_UTC      = 7
LB_RANGE_START_UTC   = 4       # Pre-London range start
LB_RANGE_END_UTC     = 7       # London open

# ─────────────────────────────────────────────
# ML MODEL
# ─────────────────────────────────────────────
ML_MODEL_PATH        = os.getenv("ML_MODEL_PATH", "models/gold_model.pkl")
ML_SCALER_PATH       = os.getenv("ML_SCALER_PATH","models/gold_scaler.pkl")
ML_CONFIDENCE_MIN    = float(os.getenv("ML_CONFIDENCE_MIN", "0.62"))  # 62%+ confidence required
ML_LOOKBACK          = 500      # Bars of history for features
ML_RETRAIN_INTERVAL  = 7        # Retrain every 7 days
FEATURE_WINDOW       = 20       # Rolling window for statistical features
TRAIN_SPLIT          = 0.75     # 75% train / 25% test

# ─────────────────────────────────────────────
# DATA PROVIDER
# ─────────────────────────────────────────────
# Option 1: MT4 CSV export (simplest)
MT4_DATA_PATH        = os.getenv("MT4_DATA_PATH", "data/XAUUSD_M15.csv")
MT4_H4_DATA_PATH     = os.getenv("MT4_H4_DATA_PATH", "data/XAUUSD_H4.csv")

# Option 2: OANDA API (for live data)
OANDA_API_KEY        = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID     = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_API_URL        = "https://api-fxtrade.oanda.com"

# Option 3: Yahoo Finance (free, for backtesting)
USE_YFINANCE         = os.getenv("USE_YFINANCE", "true").lower() == "true"
YFINANCE_SYMBOL      = "GC=F"   # Gold futures

# ─────────────────────────────────────────────
# WEBHOOK SERVER
# ─────────────────────────────────────────────
WEBHOOK_HOST         = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT         = int(os.getenv("WEBHOOK_PORT", "5000"))
WEBHOOK_SECRET       = os.getenv("WEBHOOK_SECRET", "your-secret-key-change-this")
WEBHOOK_SIGNAL_FILE  = os.getenv("WEBHOOK_SIGNAL_FILE", "signals/latest_signal.json")

# ─────────────────────────────────────────────
# MT4 BRIDGE (file-based communication)
# ─────────────────────────────────────────────
MT4_SIGNALS_DIR      = os.getenv("MT4_SIGNALS_DIR", "signals/")
MT4_ORDERS_FILE      = os.getenv("MT4_ORDERS_FILE", "signals/orders.json")
MT4_STATUS_FILE      = os.getenv("MT4_STATUS_FILE", "signals/mt4_status.json")

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE             = os.getenv("LOG_FILE", "logs/goldmaster.log")
TRADE_LOG_FILE       = os.getenv("TRADE_LOG_FILE", "logs/trades.csv")

# ─────────────────────────────────────────────
# NEWS FILTER — HIGH-IMPACT EVENTS TO AVOID
# ─────────────────────────────────────────────
HIGH_IMPACT_EVENTS = [
    "Non-Farm Payrolls",
    "FOMC",
    "CPI",
    "PPI",
    "GDP",
    "Unemployment",
    "Fed Chair Speech",
    "ECB Rate Decision",
    "US Jobs",
    "Retail Sales",
    "PMI",
]
NEWS_BUFFER_MINUTES  = 30  # No trading 30 min before/after high-impact news
