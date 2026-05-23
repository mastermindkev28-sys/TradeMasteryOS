"""
Prop-Firm Risk Manager
----------------------
Enforces:
  - 1% per-trade ATR stop
  - Daily loss limit (2% of account)
  - Trailing max drawdown (4% eval, 6% funded)
  - Consistency rule: no single day > 40% of profit target
  - Max contracts cap
  - No overnight holds (optional)
  - Kelly-lite or fixed-fractional position sizing
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeAllocation:
    contracts: int
    stop_price: float
    stop_distance_pts: float
    risk_dollars: float
    approved: bool
    reason: str


class PropFirmRiskManager:

    def __init__(self, cfg, initial_balance: float):
        self.cfg = cfg
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.total_trades = 0
        self.trading_days = 0
        self._session_open = True
        self._dd_alerted = False
        self._daily_loss_alerted = False

    # ── Balance Updates ─────────────────────────────────────────────────────

    def update_balance(self, new_balance: float):
        self.current_balance = new_balance
        self.daily_pnl = new_balance - self.daily_start_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance

    def new_day(self):
        self.daily_start_balance = self.current_balance
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.trading_days += 1
        self._session_open = True
        self._daily_loss_alerted = False
        logger.info(f"New trading day. Balance: ${self.current_balance:,.2f}")

    def session_close(self):
        self._session_open = False

    # ── Kill Switches ───────────────────────────────────────────────────────

    @property
    def daily_loss_limit_breached(self) -> bool:
        # daily_loss_limit_pct == 0 means Flex/no-daily-limit account — never breach
        if self.cfg.daily_loss_limit_pct == 0:
            return False
        limit = self.daily_start_balance * self.cfg.daily_loss_limit_pct
        breached = self.daily_pnl <= -limit
        if breached and not self._daily_loss_alerted:
            logger.warning(f"DAILY LOSS LIMIT BREACHED: P&L={self.daily_pnl:.2f} limit={-limit:.2f}")
            self._daily_loss_alerted = True
        return breached

    @property
    def trailing_drawdown_breached(self) -> bool:
        dd = (self.peak_balance - self.current_balance) / self.peak_balance
        breached = dd >= self.cfg.trailing_drawdown_pct
        if breached and not self._dd_alerted:
            logger.critical(f"TRAILING DRAWDOWN BREACHED: {dd*100:.1f}% (limit {self.cfg.trailing_drawdown_pct*100:.0f}%)")
            self._dd_alerted = True
        return breached

    @property
    def can_trade(self) -> tuple[bool, str]:
        if self.daily_loss_limit_breached:
            return False, "Daily loss limit reached — stop trading today"
        if self.trailing_drawdown_breached:
            return False, "Trailing drawdown limit breached — account at risk"
        if self.cfg.no_overnight_hold and not self._session_open:
            return False, "Session closed — no overnight positions allowed"
        return True, "OK"

    # ── Position Sizing ─────────────────────────────────────────────────────

    def size_position(
        self,
        entry_price: float,
        atr: float,
        direction: int = 1,         # +1 long, -1 short
        win_rate: Optional[float] = None,
        avg_win_loss_ratio: Optional[float] = None,
    ) -> TradeAllocation:

        ok, reason = self.can_trade
        if not ok:
            return TradeAllocation(0, 0.0, 0.0, 0.0, False, reason)

        # ATR-based stop
        stop_distance_pts = self.cfg.atr_stop_multiplier * atr
        stop_price = entry_price - direction * stop_distance_pts

        # Dollar risk per contract
        risk_per_contract = stop_distance_pts * self.cfg.risk.point_value if hasattr(self.cfg, 'risk') else stop_distance_pts * 5.0

        # --- Sizing method ---
        if self.cfg.use_kelly and win_rate and avg_win_loss_ratio:
            # Fractional Kelly: f = (bp - q) / b  where b = win/loss ratio
            b = avg_win_loss_ratio
            p = win_rate
            q = 1 - p
            kelly_f = max(0.0, (b * p - q) / b)
            kelly_f *= self.cfg.kelly_fraction   # safety fraction
            risk_dollars = self.current_balance * kelly_f
        else:
            # Fixed fractional: risk 1% of account
            risk_dollars = self.current_balance * self.cfg.risk_pct_per_trade

        contracts = int(risk_dollars / max(risk_per_contract, 1e-6))
        contracts = min(contracts, self.cfg.max_contracts)
        contracts = max(contracts, 0)

        # Margin check
        required_margin = contracts * self._get_margin()
        if required_margin > self.current_balance * self.cfg.max_position_pct_of_margin:
            contracts = int(
                (self.current_balance * self.cfg.max_position_pct_of_margin)
                / max(self._get_margin(), 1.0)
            )
            contracts = min(contracts, self.cfg.max_contracts)

        if contracts == 0:
            return TradeAllocation(0, stop_price, stop_distance_pts, 0, False, "Zero contracts after sizing")

        actual_risk = contracts * risk_per_contract
        return TradeAllocation(
            contracts=contracts,
            stop_price=round(stop_price, 2),
            stop_distance_pts=stop_distance_pts,
            risk_dollars=actual_risk,
            approved=True,
            reason=f"{contracts} contract(s), risk ${actual_risk:.2f}",
        )

    def _get_margin(self) -> float:
        # Use contract config if available, else default MES margin
        return getattr(self.cfg, 'margin_per_contract', 1320.0)

    # ── Consistency Check ───────────────────────────────────────────────────

    def consistency_warning(self, profit_target: float) -> Optional[str]:
        """
        Warn if today's P&L is about to exceed 40% of total profit target.
        Many prop firms flag this as 'single-day dominance'.
        """
        if self.daily_pnl > profit_target * self.cfg.max_profit_single_day_pct:
            return (
                f"WARNING: Today's P&L (${self.daily_pnl:.0f}) exceeds "
                f"{self.cfg.max_profit_single_day_pct*100:.0f}% of profit target. "
                f"Consider stopping early to avoid consistency rule violation."
            )
        return None

    # ── Summary ─────────────────────────────────────────────────────────────

    def status_report(self) -> dict:
        dd = (self.peak_balance - self.current_balance) / self.peak_balance
        daily_used = abs(self.daily_pnl) / (self.daily_start_balance * self.cfg.daily_loss_limit_pct)
        return {
            "balance": self.current_balance,
            "daily_pnl": self.daily_pnl,
            "daily_limit_used_pct": daily_used * 100,
            "drawdown_pct": dd * 100,
            "peak_balance": self.peak_balance,
            "trading_days": self.trading_days,
            "can_trade": self.can_trade[0],
        }
