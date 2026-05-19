"""
Central configuration for the Futures Mean Reversion Bot.
Edit this file to switch symbols, tweak strategy params, and set risk limits.
"""

from dataclasses import dataclass, field
from typing import Optional


# ─── Symbol & Contract ────────────────────────────────────────────────────────

@dataclass
class ContractConfig:
    symbol: str = "MES"            # Micro E-mini S&P 500
    exchange: str = "CME"
    tick_size: float = 0.25
    tick_value: float = 1.25       # dollars per tick  (MES = $1.25, ES = $12.50)
    point_value: float = 5.0       # dollars per full point (MES)
    margin_per_contract: float = 1_320.0   # approximate, check broker
    data_timeframe: str = "1D"     # "1D" | "1H" | "15Min"
    session_start: str = "09:30"   # CT/ET – used for intraday filter
    session_end: str = "16:00"


# ─── IBS Mean Reversion Strategy ─────────────────────────────────────────────

@dataclass
class IBSStrategyConfig:
    # Core indicators
    atr_period: int = 14
    sma_period: int = 25           # rolling mean of (high - low)
    band_lookback: int = 10        # highest(high, N) for lower band
    band_multiplier: float = 2.5   # lower_band = highest_high - mult * rolling_mean
    ibs_entry_threshold: float = 0.30   # IBS < this → oversold
    ibs_exit_threshold: float = 0.70    # IBS > this → optional overbought exit
    trend_filter_sma: int = 300         # 300-bar SMA trend filter (daily)

    # Exit rules
    exit_above_prev_high: bool = True   # exit if close > prev bar's high
    exit_below_trend: bool = True       # exit if close < 300 SMA
    max_hold_bars: int = 20             # hard cap on open trade duration

    # Intraday variant (set data_timeframe="1H" or "15Min")
    intraday_mode: bool = False
    intraday_reset_daily: bool = True   # reset IBS calc at session open


# ─── Dual Thrust Breakout (alternative) ──────────────────────────────────────

@dataclass
class DualThrustConfig:
    lookback: int = 1              # N days for range calculation
    k_long: float = 0.5           # upper threshold coefficient
    k_short: float = 0.5          # lower threshold coefficient
    session_open_offset_min: int = 15  # minutes after open to enter
    reverse_intraday: bool = False      # flip long/short near close


# ─── Risk Management ─────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    # Per-trade risk
    risk_pct_per_trade: float = 0.01       # 1% of account per trade
    atr_stop_multiplier: float = 1.5       # stop = entry ± mult * ATR
    max_contracts: int = 5                 # hard cap regardless of sizing

    # Prop-firm daily limits (TopstepX / Lucid / Apex style)
    daily_loss_limit_pct: float = 0.02     # 2% of starting balance daily
    trailing_drawdown_pct: float = 0.04    # 4% trailing max drawdown (eval)
    max_position_pct_of_margin: float = 0.50  # never use >50% of buying power

    # Consistency rules
    max_profit_single_day_pct: float = 0.40   # no single day > 40% of target
    min_trading_days: int = 10                 # minimum days to pass eval
    no_overnight_hold: bool = False            # set True for intraday-only

    # Kelly / position sizing
    use_kelly: bool = False        # if False, uses fixed-fractional
    kelly_fraction: float = 0.25   # fractional Kelly multiplier (safety)

    # Slippage & commissions for backtesting realism
    commission_per_side: float = 2.25      # $ per contract per side
    slippage_ticks: int = 1               # ticks of slippage on fill


# ─── Backtest Settings ────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    start_date: str = "2015-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 50_000.0     # typical TopstepX 50K eval
    data_source: str = "yfinance"         # "yfinance" | "csv" | "rithmic"
    csv_path: Optional[str] = None
    walk_forward_splits: int = 5          # out-of-sample windows
    monte_carlo_runs: int = 5_000
    output_dir: str = "outputs"


# ─── Live / Broker Settings ───────────────────────────────────────────────────

@dataclass
class LiveConfig:
    broker: str = "tradovate"      # "tradovate" | "rithmic" | "topstepx"
    paper_trade: bool = True       # ALWAYS start in paper mode
    tradovate_base_url: str = "https://demo.tradovateapi.com/v1"
    tradovate_user: str = ""
    tradovate_password: str = ""
    tradovate_app_id: str = ""
    tradovate_app_version: str = "1.0"
    rithmic_server: str = "Rithmic Paper Trading"
    rithmic_user: str = ""
    rithmic_password: str = ""
    poll_interval_sec: int = 60    # live loop frequency


# ─── Telegram Alerts ──────────────────────────────────────────────────────────

@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""            # from @BotFather
    chat_id: str = ""              # your personal or group chat ID
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
    active_strategy: str = "ibs"   # "ibs" | "dual_thrust"
    log_level: str = "INFO"


# Singleton used throughout the project
CONFIG = Config()
