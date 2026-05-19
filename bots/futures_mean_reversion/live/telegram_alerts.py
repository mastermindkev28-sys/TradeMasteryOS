"""
Telegram alert system for live trading notifications.
Create your bot via @BotFather, get the chat_id via @userinfobot.
Set enabled=True and fill token/chat_id in config.py.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramAlerter:

    def __init__(self, cfg):
        self.cfg = cfg
        self._base = f"https://api.telegram.org/bot{cfg.bot_token}"

    def _send(self, text: str) -> bool:
        if not self.cfg.enabled or not self.cfg.bot_token:
            return False
        try:
            resp = requests.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self.cfg.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
            return False

    def entry_alert(self, symbol: str, direction: str, contracts: int,
                    price: float, stop: float, reason: str):
        if not self.cfg.alert_on_entry:
            return
        emoji = "🟢" if direction == "long" else "🔴"
        self._send(
            f"{emoji} *ENTRY* — {symbol}\n"
            f"Direction: {direction.upper()}\n"
            f"Contracts: {contracts}\n"
            f"Price: `{price:.2f}`\n"
            f"Stop: `{stop:.2f}`\n"
            f"Reason: {reason}"
        )

    def exit_alert(self, symbol: str, direction: str, contracts: int,
                   entry: float, exit_price: float, pnl: float, reason: str):
        if not self.cfg.alert_on_exit:
            return
        emoji = "✅" if pnl >= 0 else "❌"
        self._send(
            f"{emoji} *EXIT* — {symbol}\n"
            f"Direction: {direction.upper()} → FLAT\n"
            f"Contracts: {contracts}\n"
            f"Entry: `{entry:.2f}` → Exit: `{exit_price:.2f}`\n"
            f"P&L: `${pnl:+.2f}`\n"
            f"Reason: {reason}"
        )

    def daily_loss_limit_alert(self, symbol: str, daily_pnl: float, limit: float):
        if not self.cfg.alert_on_daily_loss_limit:
            return
        self._send(
            f"🚨 *DAILY LOSS LIMIT HIT* — {symbol}\n"
            f"Daily P&L: `${daily_pnl:+.2f}`\n"
            f"Limit: `${-limit:.2f}`\n"
            f"⛔ Trading HALTED for today."
        )

    def drawdown_alert(self, dd_pct: float, limit_pct: float):
        self._send(
            f"🚨 *TRAILING DRAWDOWN ALERT*\n"
            f"Current DD: `{dd_pct:.1f}%`\n"
            f"Limit: `{limit_pct:.0f}%`\n"
            f"⛔ Account protection activated."
        )

    def error_alert(self, error: str):
        if not self.cfg.alert_on_error:
            return
        self._send(f"⚠️ *BOT ERROR*\n```\n{error[:500]}\n```")

    def status_alert(self, report: dict):
        self._send(
            f"📊 *Daily Status Report*\n"
            f"Balance: `${report['balance']:,.2f}`\n"
            f"Daily P&L: `${report['daily_pnl']:+.2f}`\n"
            f"Daily limit used: `{report['daily_limit_used_pct']:.0f}%`\n"
            f"Drawdown: `{report['drawdown_pct']:.1f}%`\n"
            f"Trading days: `{report['trading_days']}`"
        )
