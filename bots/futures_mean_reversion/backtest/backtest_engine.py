"""
Event-driven backtester for the IBS Mean Reversion strategy.
Handles commissions, slippage, overnight gaps, and prop-firm risk limits.
Produces an equity curve, trade log, and full performance report.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from strategy.ibs_mean_reversion import IBSMeanReversion
from strategy.dual_thrust import DualThrust
from risk.risk_manager import PropFirmRiskManager
from utils.metrics import compute_all_metrics
from utils.position_sizing import fixed_fractional_contracts

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    contracts: int
    stop_price: float
    direction: int           # +1 long, -1 short
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    gross_pnl: float = 0.0
    commission: float = 0.0
    net_pnl: float = 0.0
    bars_held: int = 0

    def close(self, exit_date, exit_price, reason, point_value, commission_per_side):
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        pts = (exit_price - self.entry_price) * self.direction
        self.gross_pnl = pts * self.contracts * point_value
        self.commission = commission_per_side * self.contracts * 2  # round trip
        self.net_pnl = self.gross_pnl - self.commission
        return self.net_pnl


class Backtester:

    def __init__(self, cfg):
        self.cfg = cfg
        self.rc = cfg.risk            # RiskConfig
        self.cc = cfg.contract        # ContractConfig
        self.strat_cfg = cfg.ibs if cfg.active_strategy == "ibs" else cfg.dual_thrust

        if cfg.active_strategy == "ibs":
            self.strategy = IBSMeanReversion(self.strat_cfg)
        else:
            self.strategy = DualThrust(self.strat_cfg)

    def run(self, df: pd.DataFrame) -> dict:
        """
        Main backtest loop.
        Returns dict with: equity_curve, trade_log, metrics, daily_pnl.
        """
        df = self.strategy.generate_signals(df)
        df = df.dropna(subset=["signal"])

        balance = self.cfg.backtest.initial_capital
        risk_mgr = PropFirmRiskManager(self.rc, balance)

        equity = []
        trade_log: list[Trade] = []
        current_trade: Optional[Trade] = None
        prev_date = None

        for i, (dt, row) in enumerate(df.iterrows()):
            # New trading day reset
            if prev_date is None or dt.date() != prev_date:
                if prev_date is not None:
                    risk_mgr.new_day()
                prev_date = dt.date()

            risk_mgr.update_balance(balance)

            # ── Check open position for stop-out ────────────────────────
            if current_trade is not None:
                current_trade.bars_held += 1
                stop_hit = (
                    current_trade.direction == 1 and row["low"] <= current_trade.stop_price
                ) or (
                    current_trade.direction == -1 and row["high"] >= current_trade.stop_price
                )

                if stop_hit:
                    # Fill at stop price (one tick of additional slippage)
                    fill = current_trade.stop_price - self.cc.tick_size * self.rc.slippage_ticks * current_trade.direction
                    pnl = current_trade.close(dt, fill, "stop", self.cc.point_value, self.rc.commission_per_side)
                    balance += pnl
                    trade_log.append(current_trade)
                    current_trade = None
                    risk_mgr.update_balance(balance)
                    logger.debug(f"{dt.date()} STOP  pnl=${pnl:.2f} bal=${balance:,.0f}")
                    equity.append(balance)
                    continue

            # ── Strategy exit signal ─────────────────────────────────────
            if current_trade is not None and row["signal"] == 0:
                fill = row["close"] + self.cc.tick_size * self.rc.slippage_ticks * (-current_trade.direction)
                pnl = current_trade.close(dt, fill, "signal_exit", self.cc.point_value, self.rc.commission_per_side)
                balance += pnl
                trade_log.append(current_trade)
                current_trade = None
                risk_mgr.update_balance(balance)
                logger.debug(f"{dt.date()} EXIT  pnl=${pnl:.2f} bal=${balance:,.0f}")

            # ── Strategy entry signal ────────────────────────────────────
            if current_trade is None and row["signal"] != 0:
                ok, reason = risk_mgr.can_trade
                if not ok:
                    logger.info(f"{dt.date()} BLOCKED: {reason}")
                    equity.append(balance)
                    continue

                direction = int(np.sign(row["signal"]))
                atr = row.get("atr", row["high"] - row["low"])
                contracts = fixed_fractional_contracts(
                    balance,
                    self.rc.risk_pct_per_trade,
                    atr,
                    self.rc.atr_stop_multiplier,
                    self.cc.point_value,
                    self.rc.max_contracts,
                )
                if contracts == 0:
                    equity.append(balance)
                    continue

                fill = row["close"] + self.cc.tick_size * self.rc.slippage_ticks * direction
                stop = fill - direction * self.rc.atr_stop_multiplier * atr

                current_trade = Trade(
                    entry_date=dt,
                    entry_price=fill,
                    contracts=contracts,
                    stop_price=stop,
                    direction=direction,
                )
                logger.debug(
                    f"{dt.date()} ENTER {contracts}x @ {fill:.2f} stop={stop:.2f}"
                )

            equity.append(balance)

        # ── Force-close any open trade at end of data ────────────────────
        if current_trade is not None:
            last_row = df.iloc[-1]
            fill = last_row["close"]
            pnl = current_trade.close(
                df.index[-1], fill, "end_of_data",
                self.cc.point_value, self.rc.commission_per_side
            )
            balance += pnl
            trade_log.append(current_trade)
            equity[-1] = balance

        # ── Build results ────────────────────────────────────────────────
        equity_series = pd.Series(equity, index=df.index, name="equity")
        trade_df = self._trade_log_to_df(trade_log)
        metrics = compute_all_metrics(equity_series, trade_df["net_pnl"], self.cfg.backtest.initial_capital)

        return {
            "equity_curve": equity_series,
            "trade_log": trade_df,
            "metrics": metrics,
            "feature_df": df,
            "final_balance": balance,
        }

    @staticmethod
    def _trade_log_to_df(trade_log: list[Trade]) -> pd.DataFrame:
        if not trade_log:
            return pd.DataFrame()
        records = []
        for t in trade_log:
            records.append({
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "direction": "long" if t.direction == 1 else "short",
                "contracts": t.contracts,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "stop_price": t.stop_price,
                "bars_held": t.bars_held,
                "exit_reason": t.exit_reason,
                "gross_pnl": t.gross_pnl,
                "commission": t.commission,
                "net_pnl": t.net_pnl,
            })
        return pd.DataFrame(records)
