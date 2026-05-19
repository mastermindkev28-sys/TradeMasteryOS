"""
GoldMaster Pro — Risk Manager
Prop firm risk controls: daily loss limit, drawdown guard, position sizing.
"""
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from config import (
    ACCOUNT_SIZE, RISK_PER_TRADE_PCT, MAX_DAILY_LOSS_PCT,
    MAX_TOTAL_DD_PCT, MAX_TRADES_PER_DAY, MIN_RR, PROP_FIRM_MODE,
    WEEKLY_TARGET_LOW, WEEKLY_TARGET_HIGH, TRADE_LOG_FILE
)

log = logging.getLogger("GoldMaster.Risk")


class RiskState:
    """Persistent risk state tracking."""

    def __init__(self, state_file: str = "signals/risk_state.json"):
        self.state_file = state_file
        Path("signals").mkdir(exist_ok=True)
        self._state = self._load()

    def _load(self) -> dict:
        if Path(self.state_file).exists():
            with open(self.state_file) as f:
                return json.load(f)
        return self._default_state()

    def _default_state(self) -> dict:
        return {
            "account_start":     ACCOUNT_SIZE,
            "current_equity":    ACCOUNT_SIZE,
            "today_date":        str(date.today()),
            "today_start_equity":ACCOUNT_SIZE,
            "today_pnl":         0.0,
            "today_trade_count": 0,
            "week_start_equity": ACCOUNT_SIZE,
            "week_pnl":          0.0,
            "week_trade_count":  0,
            "total_trades":      0,
            "winning_trades":    0,
            "suspended":         False,
            "suspend_reason":    "",
            "last_updated":      datetime.utcnow().isoformat(),
        }

    def save(self):
        with open(self.state_file, "w") as f:
            json.dump(self._state, f, indent=2, default=str)

    def reset_daily(self):
        self._state["today_date"]         = str(date.today())
        self._state["today_start_equity"] = self._state["current_equity"]
        self._state["today_pnl"]          = 0.0
        self._state["today_trade_count"]  = 0
        self._state["suspended"]          = False
        self._state["suspend_reason"]     = ""
        self.save()
        log.info(f"Daily reset. Start equity: ${self._state['today_start_equity']:,.2f}")

    def reset_weekly(self):
        self._state["week_start_equity"]  = self._state["current_equity"]
        self._state["week_pnl"]           = 0.0
        self._state["week_trade_count"]   = 0
        self.save()

    @property
    def today_pnl(self) -> float:
        return self._state["today_pnl"]

    @property
    def today_trades(self) -> int:
        return self._state["today_trade_count"]

    @property
    def week_pnl(self) -> float:
        return self._state["week_pnl"]

    @property
    def current_equity(self) -> float:
        return self._state["current_equity"]

    @property
    def suspended(self) -> bool:
        return self._state["suspended"]

    @property
    def total_drawdown_pct(self) -> float:
        start = self._state["account_start"]
        if start == 0: return 0.0
        return (self._state["current_equity"] - start) / start * 100

    @property
    def daily_drawdown_pct(self) -> float:
        start = self._state["today_start_equity"]
        if start == 0: return 0.0
        return (self._state["current_equity"] - start) / start * 100

    @property
    def win_rate(self) -> float:
        total = self._state["total_trades"]
        if total == 0: return 0.0
        return self._state["winning_trades"] / total

    def update_after_trade(self, pnl: float, won: bool):
        self._state["current_equity"]    += pnl
        self._state["today_pnl"]         += pnl
        self._state["week_pnl"]          += pnl
        self._state["today_trade_count"] += 1
        self._state["week_trade_count"]  += 1
        self._state["total_trades"]      += 1
        if won:
            self._state["winning_trades"] += 1
        self._state["last_updated"] = datetime.utcnow().isoformat()
        self.save()


class RiskManager:
    """
    Prop-firm-safe risk manager.
    Hard stops on daily loss, total drawdown, and trade count.
    """

    def __init__(self):
        self.state = RiskState()
        self._check_daily_reset()
        log.info(f"RiskManager initialized. Equity: ${self.state.current_equity:,.2f}")

    def _check_daily_reset(self):
        if self.state._state["today_date"] != str(date.today()):
            self.state.reset_daily()

    # ─────────────────────────────────────────────
    # TRADE GATE
    # ─────────────────────────────────────────────
    def can_trade(self, hour_utc: int = None) -> tuple[bool, str]:
        """
        Returns (can_trade, reason).
        All prop firm safety checks in one place.
        """
        self._check_daily_reset()

        if self.state.suspended:
            return False, f"SUSPENDED: {self.state._state['suspend_reason']}"

        # Session check
        if hour_utc is not None:
            in_london = 7 <= hour_utc < 16
            in_ny     = 13 <= hour_utc < 20
            if not (in_london or in_ny):
                return False, "Outside trading sessions (London 07-16, NY 13-20 UTC)"

        if not PROP_FIRM_MODE:
            return True, "OK (prop firm mode OFF)"

        # Daily loss limit
        daily_dd = self.state.daily_drawdown_pct
        if daily_dd < -MAX_DAILY_LOSS_PCT:
            self.state._state["suspended"] = True
            self.state._state["suspend_reason"] = f"Daily loss {daily_dd:.2f}% exceeded limit {-MAX_DAILY_LOSS_PCT:.1f}%"
            self.state.save()
            log.warning(f"DAILY LOSS LIMIT HIT: {daily_dd:.2f}%")
            return False, self.state._state["suspend_reason"]

        # Total drawdown
        total_dd = self.state.total_drawdown_pct
        if total_dd < -MAX_TOTAL_DD_PCT:
            self.state._state["suspended"] = True
            self.state._state["suspend_reason"] = f"Total drawdown {total_dd:.2f}% exceeded limit {-MAX_TOTAL_DD_PCT:.1f}%"
            self.state.save()
            log.critical(f"MAX DRAWDOWN BREACHED: {total_dd:.2f}%")
            return False, self.state._state["suspend_reason"]

        # Daily trade count
        if self.state.today_trades >= MAX_TRADES_PER_DAY:
            return False, f"Max trades per day reached ({MAX_TRADES_PER_DAY})"

        # Pre-cautionary: stop at 80% of daily limit
        if daily_dd < -MAX_DAILY_LOSS_PCT * 0.8:
            return False, f"Approaching daily limit ({daily_dd:.2f}%), pausing for safety"

        return True, "OK"

    # ─────────────────────────────────────────────
    # POSITION SIZING
    # ─────────────────────────────────────────────
    def calculate_lot_size(self, sl_pips: float,
                            equity_override: Optional[float] = None) -> dict:
        """
        Risk-based position sizing for XAUUSD.
        Returns lot size and risk metrics.
        """
        equity    = equity_override or self.state.current_equity
        risk_usd  = equity * RISK_PER_TRADE_PCT / 100.0

        # XAUUSD: 1 lot = 100 oz, pip = $0.01
        # Pip value: for 1 lot, moving $0.01 = $1 per lot
        # So: lot_size = risk_usd / (sl_pips * 1.0)
        pip_value_per_lot = 1.0  # $1 per pip per standard lot
        lots = risk_usd / max(sl_pips * pip_value_per_lot, 1.0)

        # Round to 0.01 lot step
        lots = round(lots, 2)

        # Hard caps
        max_lots_by_equity = equity * 0.05 / max(sl_pips, 1.0)
        lots = min(lots, max_lots_by_equity, 10.0)
        lots = max(lots, 0.01)

        return {
            "lot_size":   round(lots, 2),
            "risk_usd":   round(risk_usd, 2),
            "risk_pct":   RISK_PER_TRADE_PCT,
            "sl_pips":    round(sl_pips, 1),
            "equity":     round(equity, 2),
        }

    # ─────────────────────────────────────────────
    # SIGNAL VALIDATION
    # ─────────────────────────────────────────────
    def validate_signal(self, signal: dict) -> tuple[bool, str]:
        """Full signal validation before execution."""
        if signal.get("action") == "HOLD":
            return False, "Signal is HOLD"

        # R:R check
        rr = signal.get("rr_ratio", 0)
        if rr < MIN_RR:
            return False, f"R:R {rr:.2f} below minimum {MIN_RR}"

        # Confidence check
        confidence = signal.get("confidence", 0)
        if confidence < 0.55:
            return False, f"Confidence {confidence:.1%} too low"

        # Score check
        score = signal.get("score", 0)
        if score < 60:
            return False, f"Signal score {score} too low"

        # Trade gate
        hour_now = datetime.utcnow().hour
        can, reason = self.can_trade(hour_now)
        if not can:
            return False, reason

        return True, "Signal validated"

    # ─────────────────────────────────────────────
    # STATUS REPORT
    # ─────────────────────────────────────────────
    def get_status(self) -> dict:
        self._check_daily_reset()
        can, reason = self.can_trade(datetime.utcnow().hour)
        return {
            "can_trade":         can,
            "reason":            reason,
            "equity":            round(self.state.current_equity, 2),
            "today_pnl":         round(self.state.today_pnl, 2),
            "today_trades":      self.state.today_trades,
            "week_pnl":          round(self.state.week_pnl, 2),
            "daily_dd_pct":      round(self.state.daily_drawdown_pct, 3),
            "total_dd_pct":      round(self.state.total_drawdown_pct, 3),
            "win_rate":          round(self.state.win_rate * 100, 1),
            "total_trades":      self.state._state["total_trades"],
            "weekly_target_low": WEEKLY_TARGET_LOW,
            "weekly_target_high":WEEKLY_TARGET_HIGH,
            "weekly_progress":   round(self.state.week_pnl / WEEKLY_TARGET_HIGH * 100, 1),
            "suspended":         self.state.suspended,
            "prop_firm_mode":    PROP_FIRM_MODE,
            "max_daily_loss":    f"-{MAX_DAILY_LOSS_PCT}%",
            "max_total_dd":      f"-{MAX_TOTAL_DD_PCT}%",
            "timestamp":         datetime.utcnow().isoformat(),
        }

    def record_trade(self, pnl: float, won: bool, signal: dict = None):
        """Record a completed trade."""
        self.state.update_after_trade(pnl, won)

        # Append to CSV log
        Path("logs").mkdir(exist_ok=True)
        header = not Path(TRADE_LOG_FILE).exists()
        with open(TRADE_LOG_FILE, "a") as f:
            if header:
                f.write("timestamp,action,price,sl,tp,pnl,won,confidence,score,equity\n")
            f.write(",".join([
                datetime.utcnow().isoformat(),
                signal.get("action", "") if signal else "",
                str(signal.get("price", "")) if signal else "",
                str(signal.get("sl", "")) if signal else "",
                str(signal.get("tp1", "")) if signal else "",
                f"{pnl:.2f}",
                str(won),
                f"{signal.get('confidence', 0):.4f}" if signal else "",
                f"{signal.get('score', 0):.1f}" if signal else "",
                f"{self.state.current_equity:.2f}",
            ]) + "\n")
        log.info(f"Trade recorded: P&L=${pnl:.2f} | {'WIN' if won else 'LOSS'} | Equity=${self.state.current_equity:,.2f}")
