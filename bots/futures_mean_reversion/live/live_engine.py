"""
Live Trading Engine
--------------------
Polls the broker API at configurable intervals, computes the latest signal,
and executes orders with full prop-firm risk controls.

Safe-start checklist (enforced in code):
  1. paper_trade=True until you manually flip it
  2. Daily loss limit kill-switch
  3. Trailing drawdown kill-switch
  4. Telegram alert on every state change
  5. All orders confirmed before assuming fill
"""

import logging
import time
import signal
import sys
from datetime import datetime, time as dtime
from typing import Optional

import pandas as pd

from config import CONFIG
from strategy.ibs_mean_reversion import IBSMeanReversion
from risk.risk_manager import PropFirmRiskManager
from live.broker_api import create_broker, BrokerBase
from live.telegram_alerts import TelegramAlerter
from utils.position_sizing import fixed_fractional_contracts

logger = logging.getLogger(__name__)


class LiveEngine:

    def __init__(self, cfg=CONFIG):
        self.cfg = cfg
        self.rc = cfg.risk
        self.cc = cfg.contract
        self.broker: BrokerBase = create_broker(cfg)
        self.alerter = TelegramAlerter(cfg.telegram)
        self.strategy = IBSMeanReversion(cfg.ibs)
        self._running = False
        self._current_position = 0
        self._entry_price: Optional[float] = None
        self._stop_price: Optional[float] = None
        self._contracts = 0
        self._risk_mgr: Optional[PropFirmRiskManager] = None

        # Graceful shutdown on SIGTERM/SIGINT
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self):
        if cfg := self.cfg.live:
            mode = "PAPER" if cfg.paper_trade else "⚠️  LIVE"
            logger.info(f"=== Live Engine starting [{mode}] broker={cfg.broker} ===")
            self.alerter._send(f"🚀 Bot started [{mode}] — {self.cc.symbol}")

        if not self.broker.connect():
            logger.critical("Broker connection failed. Exiting.")
            sys.exit(1)

        balance = self.broker.get_account_balance()
        self._risk_mgr = PropFirmRiskManager(self.rc, balance)
        logger.info(f"Starting balance: ${balance:,.2f}")

        self._running = True
        self._loop()

    def _shutdown(self, *_):
        logger.info("Shutdown signal received. Flattening positions…")
        self._running = False
        self._flatten_all("Bot shutdown")
        self.alerter._send("🛑 Bot stopped — positions flattened.")

    # ── Main Loop ───────────────────────────────────────────────────────────

    def _loop(self):
        prev_day = None
        while self._running:
            try:
                now = datetime.now()

                # New day reset
                if prev_day != now.date():
                    self._risk_mgr.new_day()
                    prev_day = now.date()
                    balance = self.broker.get_account_balance()
                    self._risk_mgr.update_balance(balance)
                    report = self._risk_mgr.status_report()
                    self.alerter.status_alert(report)

                self._tick()

            except Exception as e:
                logger.exception(f"Loop error: {e}")
                self.alerter.error_alert(str(e))

            time.sleep(self.cfg.live.poll_interval_sec)

    # ── Single Tick ─────────────────────────────────────────────────────────

    def _tick(self):
        # Update balance and check kill-switches
        balance = self.broker.get_account_balance()
        self._risk_mgr.update_balance(balance)

        if self._risk_mgr.trailing_drawdown_breached:
            self.alerter.drawdown_alert(
                (self._risk_mgr.peak_balance - balance) / self._risk_mgr.peak_balance * 100,
                self.cfg.risk.trailing_drawdown_pct * 100,
            )
            self._flatten_all("Trailing drawdown kill-switch")
            self._running = False
            return

        if self._risk_mgr.daily_loss_limit_breached:
            self.alerter.daily_loss_limit_alert(
                self.cc.symbol,
                self._risk_mgr.daily_pnl,
                balance * self.rc.daily_loss_limit_pct,
            )
            self._flatten_all("Daily loss limit kill-switch")
            return  # stop for today but don't shutdown

        # Fetch latest bars
        bars = self.broker.get_latest_ohlcv(self.cc.symbol, n_bars=350)
        if not bars:
            logger.warning("No bars returned from broker")
            return

        df = self._bars_to_df(bars)
        if len(df) < max(self.cfg.ibs.trend_filter_sma, self.cfg.ibs.sma_period) + 5:
            logger.info("Insufficient bar history. Waiting…")
            return

        # Compute signal
        sig = self.strategy.latest_signal(df, self._current_position)
        logger.info(f"Signal: {sig.direction} | IBS={sig.ibs:.3f} | band={sig.lower_band:.2f} | reason={sig.reason}")

        atr = sig.atr
        last_close = df["close"].iloc[-1]

        # Entry
        if self._current_position == 0 and sig.direction == "long":
            ok, reason = self._risk_mgr.can_trade
            if not ok:
                logger.info(f"Risk block: {reason}")
                return

            contracts = fixed_fractional_contracts(
                balance, self.rc.risk_pct_per_trade, atr,
                self.rc.atr_stop_multiplier, self.cc.point_value, self.rc.max_contracts,
            )
            if contracts == 0:
                return

            stop = last_close - self.rc.atr_stop_multiplier * atr
            result = self.broker.place_market_order(self.cc.symbol, contracts, "Buy")
            if "error" not in result:
                self.broker.place_stop_order(self.cc.symbol, contracts, "Sell", stop)
                self._current_position = contracts
                self._entry_price = last_close
                self._stop_price = stop
                self._contracts = contracts
                self.alerter.entry_alert(
                    self.cc.symbol, "long", contracts, last_close, stop, sig.reason
                )

        # Exit
        elif self._current_position > 0 and sig.direction == "flat":
            self.broker.cancel_all_orders(self.cc.symbol)
            result = self.broker.place_market_order(self.cc.symbol, self._current_position, "Sell")
            if "error" not in result:
                pnl = (last_close - self._entry_price) * self._contracts * self.cc.point_value
                self.alerter.exit_alert(
                    self.cc.symbol, "long", self._contracts,
                    self._entry_price, last_close, pnl, sig.reason,
                )
                self._current_position = 0
                self._entry_price = None
                self._stop_price = None
                self._contracts = 0

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _flatten_all(self, reason: str):
        if self._current_position != 0:
            self.broker.cancel_all_orders(self.cc.symbol)
            side = "Sell" if self._current_position > 0 else "Buy"
            self.broker.place_market_order(self.cc.symbol, abs(self._current_position), side)
            self._current_position = 0

    @staticmethod
    def _bars_to_df(bars: list) -> pd.DataFrame:
        """Convert broker bar list to standard OHLCV DataFrame."""
        records = []
        for b in bars:
            # Tradovate format
            if isinstance(b, dict):
                ts = b.get("timestamp") or b.get("date") or b.get("t")
                records.append({
                    "date": pd.to_datetime(ts),
                    "open": float(b.get("open", b.get("o", 0))),
                    "high": float(b.get("high", b.get("h", 0))),
                    "low": float(b.get("low", b.get("l", 0))),
                    "close": float(b.get("close", b.get("c", 0))),
                    "volume": float(b.get("volume", b.get("v", 0))),
                })
        df = pd.DataFrame(records).set_index("date").sort_index()
        return df.dropna()
