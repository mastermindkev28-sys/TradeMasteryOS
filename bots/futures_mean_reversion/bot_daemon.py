"""
TradeMastery Bot Daemon
========================
Runs 24/7 Mon-Fri. Sends a signal scan to Telegram every morning at 6:00 AM PST.
Also sends a heartbeat every Sunday night so you know it's alive.

Usage:
    python3 bot_daemon.py              # start daemon (blocks — use launchd to manage)
    python3 bot_daemon.py --now        # fire a scan immediately then keep running
    python3 bot_daemon.py --test       # send a test Telegram message and exit

Managed by launchd on Mac (see com.trademastery.bot.plist).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

try:
    from zoneinfo import ZoneInfo      # Python 3.9+ built-in
except ImportError:
    from backports.zoneinfo import ZoneInfo  # pip install backports.zoneinfo

import schedule

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG
from scanner import scan_symbol, format_telegram_message
from live.telegram_alerts import TelegramAlerter

# ── Timezone ──────────────────────────────────────────────────────────────────
PACIFIC = ZoneInfo("America/Los_Angeles")   # handles PST/PDT automatically

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "daemon.log"),
    ],
)
logger = logging.getLogger("daemon")


# ── Core scan job ─────────────────────────────────────────────────────────────

def run_scan():
    """Run signal scan for all symbols and send Telegram alert."""
    now_pt = datetime.now(PACIFIC)
    weekday = now_pt.weekday()          # 0=Mon, 4=Fri, 5=Sat, 6=Sun

    # Safety check — don't scan on weekends (schedule handles this but belt+suspenders)
    if weekday >= 5:
        logger.info(f"Weekend ({now_pt.strftime('%A')}) — skipping scan.")
        return

    logger.info(f"=== Starting scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")

    symbols = CONFIG.scan_symbols
    results = [scan_symbol(s) for s in symbols]

    for r in results:
        if r.get("error"):
            logger.warning(f"{r['symbol']}: {r['error']}")
        else:
            logger.info(
                f"{r['symbol']}: signal={r['signal'].upper()}  "
                f"IBS={r['ibs']:.3f}  close={r['last_close']:.2f}"
            )

    message = format_telegram_message(results)
    alerter = TelegramAlerter(CONFIG.telegram)
    sent = alerter._send(message)

    if sent:
        logger.info("Telegram alert sent ✅")
    else:
        logger.warning("Telegram send failed — check token/chat_id in .env")
        # Print to log so you can see it even if Telegram is down
        logger.info("\n" + message)


def send_heartbeat():
    """Weekly Sunday night heartbeat so you know the daemon is alive."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() != 6:          # only Sunday
        return
    alerter = TelegramAlerter(CONFIG.telegram)
    alerter._send(
        f"🟢 *TradeMastery Bot — Weekly Heartbeat*\n"
        f"Daemon is running. Next scan: Monday 6:00 AM PT.\n"
        f"Plan: *{CONFIG.plan.display_name}*"
    )
    logger.info("Heartbeat sent.")


def send_test():
    """Send a test Telegram message and exit."""
    alerter = TelegramAlerter(CONFIG.telegram)
    now_pt = datetime.now(PACIFIC)
    sent = alerter._send(
        f"✅ *TradeMastery Bot — Test Message*\n"
        f"Daemon is configured correctly.\n"
        f"Time (PT): `{now_pt.strftime('%a %b %d %I:%M %p')}`\n"
        f"Plan: *{CONFIG.plan.display_name}*\n"
        f"Symbols: `{', '.join(CONFIG.scan_symbols)}`\n"
        f"Daily scan scheduled: *6:00 AM PT Mon–Fri*"
    )
    if sent:
        print("✅ Test message sent to Telegram.")
    else:
        print("❌ Failed — check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    sys.exit(0 if sent else 1)


# ── Scheduler setup ───────────────────────────────────────────────────────────

def setup_schedule():
    """
    Schedule daily scan at 6:00 AM Pacific, Mon–Fri only.
    schedule library runs in local time; we convert 6am PT → local wall clock.
    Since launchd runs the process, we keep it simple: schedule at 06:00 and
    gate on weekday inside run_scan().
    """
    # Daily scan Mon–Fri at 06:00 AM PT
    # We schedule every day and skip weekends inside run_scan()
    schedule.every().monday.at("06:00").do(run_scan)
    schedule.every().tuesday.at("06:00").do(run_scan)
    schedule.every().wednesday.at("06:00").do(run_scan)
    schedule.every().thursday.at("06:00").do(run_scan)
    schedule.every().friday.at("06:00").do(run_scan)

    # Weekly heartbeat Sunday at 8:00 PM PT
    schedule.every().sunday.at("20:00").do(send_heartbeat)

    logger.info("Schedule set: scan Mon–Fri at 6:00 AM PT | heartbeat Sun 8:00 PM PT")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TradeMastery Bot Daemon")
    parser.add_argument("--now", action="store_true", help="Run a scan immediately then keep running")
    parser.add_argument("--test", action="store_true", help="Send test Telegram message and exit")
    args = parser.parse_args()

    if args.test:
        send_test()

    logger.info("=" * 55)
    logger.info("  TradeMastery Bot Daemon starting")
    logger.info(f"  Plan    : {CONFIG.plan.display_name}")
    logger.info(f"  Symbols : {', '.join(CONFIG.scan_symbols)}")
    logger.info(f"  Schedule: Mon–Fri 6:00 AM PT")
    logger.info("=" * 55)

    setup_schedule()

    if args.now:
        logger.info("--now flag: running immediate scan...")
        run_scan()

    # Main loop — check schedule every 30 seconds
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
