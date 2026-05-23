"""
TradeMasteryOS — Futures Mean Reversion Bot
Supports Lucid Trading, TopStep, Apex Trader Funding, MyFundedFutures,
Take Profit Trader, and Earn2Trade (Gauntlet) evaluation plans.

Select your plan via env var or CLI:
  PROP_FIRM_PLAN=apex_100k python scanner.py
  python scanner.py --plan topstep_150k
  python scanner.py --list-plans

⚠️  Rules change — always verify at each firm's website before trading.
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
    tick_value: float = 0.50
    point_value: float = 2.0
    margin_per_contract: float = 2_200.0
    data_timeframe: str = "1D"
    session_start: str = "09:30"
    session_end: str = "16:00"


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
        tick_value=1.00,
        point_value=10.0,
        margin_per_contract=800.0,
    ),
    "MES": ContractConfig(
        symbol="MES",
        tick_size=0.25,
        tick_value=1.25,
        point_value=5.0,
        margin_per_contract=1_320.0,
    ),
    "MCL": ContractConfig(
        symbol="MCL",
        tick_size=0.01,
        tick_value=1.00,
        point_value=100.0,
        margin_per_contract=1_500.0,
    ),
}

YFINANCE_MAP = {
    "MNQ": "NQ=F",
    "MGC": "GC=F",
    "MES": "ES=F",
    "MCL": "CL=F",
}


# ─── Prop Firm Plan Registry ──────────────────────────────────────────────────

@dataclass
class PropFirmPlan:
    """One row per evaluation plan. All dollar amounts are absolute."""
    key: str                         # e.g. "lucid_25k"
    display_name: str                # e.g. "Lucid 25K"
    firm: str                        # "lucid" | "topstep"
    account_size: float              # starting balance
    profit_target: float             # dollars to pass eval
    daily_loss_limit: float          # max intraday loss before auto-flatten
    trailing_drawdown: float         # max drawdown from equity peak
    min_trading_days: int            # minimum days before passing
    max_contracts_default: int       # conservative cap for eval
    no_overnight_hold: bool = False  # some plans require flat at close


# ── Lucid Trading ─────────────────────────────────────────────────────────────
#    Rules as of 2025 — verify at lucidtrading.com before trading

_LUCID_PLANS = [
    PropFirmPlan(
        key="lucid_10k",
        display_name="Lucid 10K",
        firm="lucid",
        account_size=10_000,
        profit_target=700,
        daily_loss_limit=200,
        trailing_drawdown=500,
        min_trading_days=5,
        max_contracts_default=1,
    ),
    PropFirmPlan(
        key="lucid_25k",
        display_name="Lucid 25K",
        firm="lucid",
        account_size=25_000,
        profit_target=1_500,
        daily_loss_limit=500,
        trailing_drawdown=1_000,
        min_trading_days=10,
        max_contracts_default=2,
    ),
    PropFirmPlan(
        key="lucid_50k",
        display_name="Lucid 50K",
        firm="lucid",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=10,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="lucid_100k",
        display_name="Lucid 100K",
        firm="lucid",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=4_000,
        min_trading_days=10,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="lucid_150k",
        display_name="Lucid 150K",
        firm="lucid",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=6_000,
        min_trading_days=10,
        max_contracts_default=12,
    ),
]

# ── TopStep ───────────────────────────────────────────────────────────────────
#    Rules as of 2025 — verify at topstep.com before trading

_TOPSTEP_PLANS = [
    PropFirmPlan(
        key="topstep_50k",
        display_name="TopStep 50K",
        firm="topstep",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=10,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="topstep_100k",
        display_name="TopStep 100K",
        firm="topstep",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=3_000,
        min_trading_days=10,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="topstep_150k",
        display_name="TopStep 150K",
        firm="topstep",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=4_500,
        min_trading_days=10,
        max_contracts_default=12,
    ),
]

# ── Apex Trader Funding ───────────────────────────────────────────────────────
#    Rules as of 2025 — verify at apextraderfunding.com before trading
#    Note: Apex has NO daily loss limit in funded phase; using eval-phase limits here.

_APEX_PLANS = [
    PropFirmPlan(
        key="apex_25k",
        display_name="Apex 25K",
        firm="apex",
        account_size=25_000,
        profit_target=1_500,
        daily_loss_limit=500,
        trailing_drawdown=1_500,
        min_trading_days=7,
        max_contracts_default=2,
    ),
    PropFirmPlan(
        key="apex_50k",
        display_name="Apex 50K",
        firm="apex",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_500,
        min_trading_days=7,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="apex_75k",
        display_name="Apex 75K",
        firm="apex",
        account_size=75_000,
        profit_target=4_250,
        daily_loss_limit=1_500,
        trailing_drawdown=2_750,
        min_trading_days=7,
        max_contracts_default=6,
    ),
    PropFirmPlan(
        key="apex_100k",
        display_name="Apex 100K",
        firm="apex",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=3_000,
        min_trading_days=7,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="apex_150k",
        display_name="Apex 150K",
        firm="apex",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=5_000,
        min_trading_days=7,
        max_contracts_default=12,
    ),
    PropFirmPlan(
        key="apex_250k",
        display_name="Apex 250K",
        firm="apex",
        account_size=250_000,
        profit_target=15_000,
        daily_loss_limit=5_000,
        trailing_drawdown=6_500,
        min_trading_days=7,
        max_contracts_default=14,
    ),
    PropFirmPlan(
        key="apex_300k",
        display_name="Apex 300K",
        firm="apex",
        account_size=300_000,
        profit_target=20_000,
        daily_loss_limit=6_000,
        trailing_drawdown=7_500,
        min_trading_days=7,
        max_contracts_default=17,
    ),
]

# ── MyFundedFutures ───────────────────────────────────────────────────────────
#    Rules as of 2025 — verify at myfundedfutures.com before trading

_MFF_PLANS = [
    PropFirmPlan(
        key="mff_50k",
        display_name="MyFundedFutures 50K",
        firm="myfundedfutures",
        account_size=50_000,
        profit_target=4_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=10,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="mff_100k",
        display_name="MyFundedFutures 100K",
        firm="myfundedfutures",
        account_size=100_000,
        profit_target=8_000,
        daily_loss_limit=2_000,
        trailing_drawdown=4_000,
        min_trading_days=10,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="mff_150k",
        display_name="MyFundedFutures 150K",
        firm="myfundedfutures",
        account_size=150_000,
        profit_target=12_000,
        daily_loss_limit=3_000,
        trailing_drawdown=6_000,
        min_trading_days=10,
        max_contracts_default=12,
    ),
]

# ── Take Profit Trader ────────────────────────────────────────────────────────
#    Rules as of 2025 — verify at takeprofittrader.com before trading

_TPT_PLANS = [
    PropFirmPlan(
        key="tpt_50k",
        display_name="Take Profit Trader 50K",
        firm="takeprofittrader",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=10,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="tpt_100k",
        display_name="Take Profit Trader 100K",
        firm="takeprofittrader",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=3_500,
        min_trading_days=10,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="tpt_150k",
        display_name="Take Profit Trader 150K",
        firm="takeprofittrader",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=5_000,
        min_trading_days=10,
        max_contracts_default=12,
    ),
]

# ── Earn2Trade (Gauntlet Mini) ────────────────────────────────────────────────
#    Rules as of 2025 — verify at earn2trade.com before trading

_E2T_PLANS = [
    PropFirmPlan(
        key="e2t_25k",
        display_name="Earn2Trade Gauntlet 25K",
        firm="earn2trade",
        account_size=25_000,
        profit_target=1_500,
        daily_loss_limit=500,
        trailing_drawdown=1_500,
        min_trading_days=15,
        max_contracts_default=2,
    ),
    PropFirmPlan(
        key="e2t_50k",
        display_name="Earn2Trade Gauntlet 50K",
        firm="earn2trade",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=15,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="e2t_100k",
        display_name="Earn2Trade Gauntlet 100K",
        firm="earn2trade",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=4_000,
        min_trading_days=15,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="e2t_150k",
        display_name="Earn2Trade Gauntlet 150K",
        firm="earn2trade",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=6_000,
        min_trading_days=15,
        max_contracts_default=12,
    ),
]

# ── Bulenox ───────────────────────────────────────────────────────────────────
#    Rules as of 2025 — verify at bulenox.com before trading

_BULENOX_PLANS = [
    PropFirmPlan(
        key="bulenox_50k",
        display_name="Bulenox 50K",
        firm="bulenox",
        account_size=50_000,
        profit_target=3_000,
        daily_loss_limit=1_000,
        trailing_drawdown=2_000,
        min_trading_days=5,
        max_contracts_default=4,
    ),
    PropFirmPlan(
        key="bulenox_100k",
        display_name="Bulenox 100K",
        firm="bulenox",
        account_size=100_000,
        profit_target=6_000,
        daily_loss_limit=2_000,
        trailing_drawdown=4_000,
        min_trading_days=5,
        max_contracts_default=8,
    ),
    PropFirmPlan(
        key="bulenox_150k",
        display_name="Bulenox 150K",
        firm="bulenox",
        account_size=150_000,
        profit_target=9_000,
        daily_loss_limit=3_000,
        trailing_drawdown=6_000,
        min_trading_days=5,
        max_contracts_default=12,
    ),
]

PROP_FIRM_PLANS: dict[str, PropFirmPlan] = {
    p.key: p for p in (
        _LUCID_PLANS
        + _TOPSTEP_PLANS
        + _APEX_PLANS
        + _MFF_PLANS
        + _TPT_PLANS
        + _E2T_PLANS
        + _BULENOX_PLANS
    )
}

DEFAULT_PLAN_KEY = os.getenv("PROP_FIRM_PLAN", "lucid_25k")


def get_plan(key: str | None = None) -> PropFirmPlan:
    """Return a PropFirmPlan by key. Falls back to DEFAULT_PLAN_KEY."""
    k = (key or DEFAULT_PLAN_KEY).lower().replace("-", "_").replace(" ", "_")
    if k not in PROP_FIRM_PLANS:
        available = ", ".join(PROP_FIRM_PLANS)
        raise ValueError(f"Unknown plan '{k}'. Available: {available}")
    return PROP_FIRM_PLANS[k]


# ─── Strategy Config ──────────────────────────────────────────────────────────

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


@dataclass
class DualThrustConfig:
    lookback: int = 1
    k_long: float = 0.5
    k_short: float = 0.5
    session_open_offset_min: int = 15
    reverse_intraday: bool = False


# ─── Risk — loaded from the active PropFirmPlan ───────────────────────────────

def _build_risk(plan: PropFirmPlan) -> "RiskConfig":
    """Derive RiskConfig values from a PropFirmPlan."""
    return RiskConfig(
        risk_pct_per_trade=0.005,                                     # 0.5% per trade
        atr_stop_multiplier=1.5,
        max_contracts=plan.max_contracts_default,
        daily_loss_limit_pct=plan.daily_loss_limit / plan.account_size,
        trailing_drawdown_pct=plan.trailing_drawdown / plan.account_size,
        max_profit_single_day_pct=0.40,
        profit_target=plan.profit_target,
        min_trading_days=plan.min_trading_days,
        no_overnight_hold=plan.no_overnight_hold,
        commission_per_side=2.25,
        slippage_ticks=1,
    )


@dataclass
class RiskConfig:
    risk_pct_per_trade: float = 0.005
    atr_stop_multiplier: float = 1.5
    max_contracts: int = 2

    daily_loss_limit_pct: float = 0.02
    trailing_drawdown_pct: float = 0.04
    max_position_pct_of_margin: float = 0.50

    max_profit_single_day_pct: float = 0.40
    profit_target: float = 1_500.0
    min_trading_days: int = 10
    no_overnight_hold: bool = False

    use_kelly: bool = False
    kelly_fraction: float = 0.25

    commission_per_side: float = 2.25
    slippage_ticks: int = 1


# ─── Backtest ─────────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    start_date: str = "2015-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 25_000.0
    data_source: str = "yfinance"
    csv_path: Optional[str] = None
    walk_forward_splits: int = 5
    monte_carlo_runs: int = 5_000
    output_dir: str = "outputs"


# ─── Live / Broker ────────────────────────────────────────────────────────────

@dataclass
class LiveConfig:
    broker: str = "tradovate"
    paper_trade: bool = True
    tradovate_base_url: str = "https://demo.tradovateapi.com/v1"
    tradovate_user: str = os.getenv("TRADOVATE_USER", "")
    tradovate_password: str = os.getenv("TRADOVATE_PASS", "")
    tradovate_app_id: str = os.getenv("TRADOVATE_APP_ID", "")
    tradovate_app_version: str = "1.0"
    rithmic_user: str = os.getenv("RITHMIC_USER", "")
    rithmic_password: str = os.getenv("RITHMIC_PASS", "")
    poll_interval_sec: int = 3_600


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
    scan_symbols: list = field(default_factory=lambda: ["MNQ", "MGC"])
    log_level: str = "INFO"
    # Active plan — applied at startup
    plan: PropFirmPlan = field(default_factory=get_plan)

    def apply_plan(self, plan_key: str | None = None) -> "Config":
        """Swap to a different plan at runtime (e.g. from CLI --plan arg)."""
        self.plan = get_plan(plan_key)
        self.risk = _build_risk(self.plan)
        self.backtest.initial_capital = self.plan.account_size
        return self


# Singleton — call CONFIG.apply_plan("topstep_100k") if you need to override
CONFIG = Config()
CONFIG.apply_plan()   # applies DEFAULT_PLAN_KEY (env var or lucid_25k)
