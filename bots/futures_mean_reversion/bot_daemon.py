"""
TradeMastery Bot Daemon
========================
Runs 24/7 Mon-Fri. Polls for A+ signals every 5 min during two daily windows:

  Morning : 6:00 AM – 9:30 AM PT  (9:00 AM – 12:30 PM ET)
  Evening : 5:00 PM – 10:00 PM PT (8:00 PM –  1:00 AM ET)

Fixed daily jobs:
  6:00 AM PT — IBS mean reversion scan (overnight context, next-day open entry)
  8:00 PM PT Sunday — weekly heartbeat

Usage:
    python3 bot_daemon.py              # start daemon (blocks — use launchd/nohup)
    python3 bot_daemon.py --now        # fire all scans immediately then keep running
    python3 bot_daemon.py --test       # send a test Telegram message and exit
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import schedule

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG
from scanner import scan_symbol, format_telegram_message
from ict_scanner import run_ict_all_sessions
from orb_vwap_scanner import run_orb_vwap_scan, run_orb_vwap_pm_scan, reset_orb_vwap_state
from live.telegram_alerts import TelegramAlerter

PACIFIC = ZoneInfo("America/Los_Angeles")
EASTERN = ZoneInfo("America/New_York")

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


# ── Scan windows (PT) ─────────────────────────────────────────────────────────
# (name, start_hour, start_min, end_hour, end_min)  — all Pacific Time
_SCAN_WINDOWS_PT = [
    ("morning",  6,  0,  9, 30),   # 6:00 AM – 9:30 AM PT
    ("evening", 17,  0, 22,  0),   # 5:00 PM – 10:00 PM PT
]


# ── IBS daily scan ────────────────────────────────────────────────────────────

def run_scan():
    """IBS mean reversion scan — runs once at 6:00 AM PT Mon-Fri."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() >= 5:
        return

    logger.info(f"=== IBS scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")

    results = [scan_symbol(s) for s in CONFIG.scan_symbols]
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
        logger.info("IBS Telegram alert sent ✅")
    else:
        logger.warning("Telegram send failed — check token/chat_id in .env")
        logger.info("\n" + message)


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def send_heartbeat():
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() != 6:
        return
    TelegramAlerter(CONFIG.telegram)._send(
        f"🟢 *TradeMastery Bot — Weekly Heartbeat*\n"
        f"Daemon is running. Scan windows: 6–9:30 AM PT and 5–10 PM PT.\n"
        f"Plan: *{CONFIG.plan.display_name}*"
    )
    logger.info("Heartbeat sent.")


# ── Test message ──────────────────────────────────────────────────────────────

def send_test():
    now_pt = datetime.now(PACIFIC)
    sent = TelegramAlerter(CONFIG.telegram)._send(
        f"✅ *TradeMastery Bot — Test Message*\n"
        f"Daemon is configured correctly.\n"
        f"Time (PT): `{now_pt.strftime('%a %b %d %I:%M %p')}`\n"
        f"Plan: *{CONFIG.plan.display_name}*\n"
        f"Symbols: `{', '.join(CONFIG.scan_symbols)}`\n"
        f"Scan windows: *6–9:30 AM PT* and *5–10 PM PT* (Mon–Fri)\n"
        f"Sprint mode: *{'ON' if CONFIG.sprint_mode else 'OFF'}*"
    )
    if sent:
        print("✅ Test message sent to Telegram.")
    else:
        print("❌ Failed — check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    sys.exit(0 if sent else 1)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def setup_schedule():
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        getattr(schedule.every(), day).at("06:00").do(run_scan)

    schedule.every().sunday.at("20:00").do(send_heartbeat)

    logger.info(
        "Schedule set:\n"
        "  6:00 AM PT Mon–Fri  → IBS mean reversion scan\n"
        "  6:00–9:30 AM PT     → ICT + ORB/VWAP polls every 5 min\n"
        "  5:00–10:00 PM PT    → ICT + ORB/VWAP polls every 5 min\n"
        "  8:00 PM PT Sunday   → weekly heartbeat"
    )


# ── Intraday polling ──────────────────────────────────────────────────────────

_last_poll_key: str = ""


def maybe_run_intraday_scan():
    """
    Called every 30 s from the main loop.
    Fires ICT all-sessions + ORB/VWAP scanner every 5 min while inside
    the morning (6:00–9:30 AM PT) or evening (5:00–10:00 PM PT) window.
    """
    global _last_poll_key

    now_pt = datetime.now(PACIFIC)

    if now_pt.weekday() >= 5:
        return

    # Reset ORB state at the top of each morning window
    if now_pt.hour == 6 and now_pt.minute == 0 and now_pt.second < 35:
        reset_orb_vwap_state()

    for sess_name, sh, sm, eh, em in _SCAN_WINDOWS_PT:
        sess_open  = now_pt.replace(hour=sh, minute=sm, second=0, microsecond=0)
        sess_close = now_pt.replace(hour=eh, minute=em, second=0, microsecond=0)
        if not (sess_open <= now_pt <= sess_close):
            continue

        # Fire on every 5th minute
        if now_pt.minute % 5 != 0:
            continue

        poll_key = f"{sess_name}:{now_pt.minute}"
        if poll_key == _last_poll_key:
            continue
        _last_poll_key = poll_key

        logger.info(f"=== Poll [{sess_name}] [{now_pt.strftime('%I:%M %p PT')}] ===")
        try:
            run_ict_all_sessions()
        except Exception as e:
            logger.error(f"ICT scan error [{sess_name}]: {e}")
        try:
            if sess_name == "evening":
                run_orb_vwap_pm_scan()
            else:
                run_orb_vwap_scan()
        except Exception as e:
            logger.error(f"ORB/VWAP scan error [{sess_name}]: {e}")
        break


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TradeMastery Bot Daemon")
    parser.add_argument("--now",  action="store_true", help="Run all scans immediately then keep running")
    parser.add_argument("--test", action="store_true", help="Send test Telegram message and exit")
    args = parser.parse_args()

    if args.test:
        send_test()

    logger.info("=" * 55)
    logger.info("  TradeMastery Bot Daemon starting")
    logger.info(f"  Plan    : {CONFIG.plan.display_name}")
    logger.info(f"  Symbols : {', '.join(CONFIG.scan_symbols)}")
    logger.info(f"  Windows : 6:00–9:30 AM PT  |  5:00–10:00 PM PT")
    if CONFIG.sprint_mode:
        logger.info(f"  ⚡ SPRINT MODE  ICT min score: {CONFIG.ict_min_score}/10  Daily cap: ${CONFIG.sprint_daily_loss_cap:,.0f}")
    logger.info("=" * 55)

    setup_schedule()

    if args.now:
        logger.info("--now flag: firing all scans immediately...")
        run_scan()
        run_ict_all_sessions()
        run_orb_vwap_scan()

    while True:
        schedule.run_pending()
        maybe_run_intraday_scan()
        time.sleep(30)


if __name__ == "__main__":
    main()
