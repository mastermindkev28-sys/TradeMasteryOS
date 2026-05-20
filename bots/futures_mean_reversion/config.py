"""
TradeMasteryOS — Bot Configuration
Tuned for: Lucid 25K Evaluation | MNQ + MGC | Telegram alerts
"""

from dataclasses import dataclass, field
from typing import Optional
import os


# ─── Contract Presets ─────────────────────────────────────────────────────────

@dataclass
class ContractConfig:
    symbol: str = "MNQ"
    exchange: str = "CME"
    tick_size: float = 0.25
    tick_value: float = 0.50        # MNQ = $0.50/tick
    point_value: float = 2.0        # MNQ = $2/point
    margin_per_contract: float = 2_200.0
    data_timeframe: str = "1D"
    session_start: str = "09:30"
    session_end: str = "16:00"


# Preset contract specs — used by the multi-symbol scanner
CONTRACT_SPECS = {
    "MNQ": ContractConfig(
        symbol="MNQ",
        tick_size=0.25,
        tick_value=0.50,
        point_value=2.0,
        margin_per_contract=2_200.0,
    ),
    "MGC": ContractConfig(
        symbol="MGC",
        tick_size=0.10,
        tick_value=1.00,            # MGC = $1/tick, $10/point
        point_value=10.0,
        margin_per_contract=800.0,
    ),
}

# yfinance tickers for each symbol
YFINANCE_MAP = {
    "MNQ": "NQ=F",    # E-mini Nasdaq-100 continuous
    "MGC": "GC=F",    # Gold continuous
    "MES": "ES=F",
    "MCL": "CL=F",
}


# ─── IBS Strategy ─────────────────────────────────────────────────────────────

@dataclass
class IBSStrategyConfig:
    atr_period: int = 14
    sma_period: int = 25
    band_lookback: int = 10
    band_multiplier: float = 2.5
    ibs_entry_threshold: float = 0.30
    ibs_exit_threshold: float = 0.70
    trend_filter_sma: int = 300
    exit_above_prev_high: bool = True
    exit_below_trend: bool = True
    max_hold_bars: int = 20
    intraday_mode: bool = False
    intraday_reset_daily: bool = True


# ─── Dual Thrust (alternative) ────────────────────────────────────────────────

@dataclass
class DualThrustConfig:
    lookback: int = 1
    k_long: float = 0.5
    k_short: float = 0.5
    session_open_offset_min: int = 15
    reverse_intraday: bool = False


# ─── Risk — Lucid 25K Evaluation ──────────────────────────────────────────────

@dataclass
class RiskConfig:
    # Per-trade: 0.5% of $25K = $125 max risk per trade (conservative for eval)
    risk_pct_per_trade: float = 0.005
    atr_stop_multiplier: float = 1.5
    max_contracts: int = 2                  # stay small during eval

    # Lucid 25K hard limits
    daily_loss_limit_pct: float = 0.02      # $500/day max loss
    trailing_drawdown_pct: float = 0.04     # $1,000 trailing DD limit
    max_position_pct_of_margin: float = 0.50

    # Consistency (Lucid flags single-day dominance)
    max_profit_single_day_pct: float = 0.40  # no single day > 40% of $1,500 target
    profit_target: float = 1_500.0           # Lucid 25K profit target
    min_trading_days: int = 10
    no_overnight_hold: bool = False

    use_kelly: bool = False
    kelly_fraction: float = 0.25

    # Realistic fill costs (Lucid uses Rithmic/Tradovate, ~$2.25/side MNQ)
    commission_per_side: float = 2.25
    slippage_ticks: int = 1


# ─── Backtest ─────────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    start_date: str = "2015-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 25_000.0      # Lucid 25K
    data_source: str = "yfinance"
    csv_path: Optional[str] = None
    walk_forward_splits: int = 5
    monte_carlo_runs: int = 5_000
    output_dir: str = "outputs"


# ─── Live / Broker ────────────────────────────────────────────────────────────

@dataclass
class LiveConfig:
    broker: str = "tradovate"
    paper_trade: bool = True                # flip to False only after eval passes
    tradovate_base_url: str = "https://demo.tradovateapi.com/v1"
    # Credentials loaded from environment variables (never hardcode)
    tradovate_user: str = os.getenv("TRADOVATE_USER", "")
    tradovate_password: str = os.getenv("TRADOVATE_PASS", "")
    tradovate_app_id: str = os.getenv("TRADOVATE_APP_ID", "")
    tradovate_app_version: str = "1.0"
    rithmic_user: str = os.getenv("RITHMIC_USER", "")
    rithmic_password: str = os.getenv("RITHMIC_PASS", "")
    poll_interval_sec: int = 3_600          # check once per hour (daily strategy)


# ─── Telegram ─────────────────────────────────────────────────────────────────

@dataclass
class TelegramConfig:
    enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    alert_on_entry: bool = True
    alert_on_exit: bool = True
    alert_on_daily_loss_limit: bool = True
    alert_on_error: bool = True


# ─── Master Config ────────────────────────────────────────────────────────────

@dataclass
class Config:
    contract: ContractConfig = field(default_factory=ContractConfig)
    ibs: IBSStrategyConfig = field(default_factory=IBSStrategyConfig)
    dual_thrust: DualThrustConfig = field(default_factory=DualThrustConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    live: LiveConfig = field(default_factory=LiveConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    active_strategy: str = "ibs"
    # Symbols to scan — bot checks both and alerts on whichever fires
    scan_symbols: list = field(default_factory=lambda: ["MNQ", "MGC"])
    log_level: str = "INFO"


CONFIG = Config()
