"""
TradeMastery Bot Daemon
========================
Runs 24/7 Mon-Fri. Four trading sessions covered each day:

  Asia Kill Zone   8:05 PM ET  (20:05) — ICT scan
  London Kill Zone 11:00 PM ET (23:00) — ICT scan  [2:00 AM ET next day]
  NY AM            9:25 AM ET         — ICT + IBS + ORB+VWAP scans
  NY PM            1:30 PM ET         — ICT + ORB+VWAP PM scans

Polling sessions (ORB+VWAP every 5 min):
  9:35–10:50 ET  (NY AM)
  13:00–15:30 ET (NY PM)

Schedule (PT times for `schedule` library):
  6:00 AM PT Mon–Fri → IBS mean reversion scan
  6:25 AM PT Mon–Fri → ICT NY Kill Zone scan
  17:05 PT Mon–Fri   → Asia Kill Zone ICT scan (8:05 PM ET)
  23:00 PT Mon–Fri   → London Kill Zone ICT scan (2:00 AM ET)
  10:30 AM PT Mon–Fri → NY PM ICT scan (1:30 PM ET)

Usage:
    python3 bot_daemon.py              # start daemon (blocks — use launchd to manage)
    python3 bot_daemon.py --now        # fire all scans immediately then keep running
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
from ict_scanner import scan_ict, scan_ict_all_sessions, run_ict_all_sessions
from orb_vwap_scanner import run_orb_vwap_scan, run_orb_vwap_pm_scan, reset_orb_vwap_state
from live.telegram_alerts import TelegramAlerter

# ── Timezone ──────────────────────────────────────────────────────────────────
PACIFIC  = ZoneInfo("America/Los_Angeles")
EASTERN  = ZoneInfo("America/New_York")

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

def run_ict_scan():
    """Run ICT NY Kill Zone scan at 9:25 AM ET and send Telegram alert."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() >= 5:
        return

    logger.info(f"=== ICT NY Kill Zone scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")

    for symbol in CONFIG.scan_symbols:
        try:
            sig, msg = scan_ict(symbol)
            alerter = TelegramAlerter(CONFIG.telegram)
            sent = alerter._send(msg)
            if sent:
                logger.info(f"ICT {symbol}: Telegram sent ✅")
            else:
                logger.warning(f"ICT {symbol}: Telegram failed")
                logger.info("\n" + msg)
        except Exception as e:
            logger.error(f"ICT scan error for {symbol}: {e}")


def run_ict_asia_scan():
    """Run ICT Asia Kill Zone scan at 8:05 PM ET (17:05 PT)."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() >= 5:
        return
    logger.info(f"=== ICT Asia Kill Zone scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")
    try:
        run_ict_all_sessions()
    except Exception as e:
        logger.error(f"ICT Asia scan error: {e}")


def run_ict_london_scan():
    """Run ICT London Kill Zone scan at 2:00 AM ET (23:00 PT previous night)."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() >= 5:
        return
    logger.info(f"=== ICT London Kill Zone scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")
    try:
        run_ict_all_sessions()
    except Exception as e:
        logger.error(f"ICT London scan error: {e}")


def run_ict_ny_pm_scan():
    """Run ICT NY PM session scan at 1:30 PM ET (10:30 AM PT)."""
    now_pt = datetime.now(PACIFIC)
    if now_pt.weekday() >= 5:
        return
    logger.info(f"=== ICT NY PM session scan [{now_pt.strftime('%a %b %d %I:%M %p PT')}] ===")
    try:
        run_ict_all_sessions()
    except Exception as e:
        logger.error(f"ICT NY PM scan error: {e}")


def setup_schedule():
    """
    Four session scan engines Mon–Fri:
      6:00 AM PT  — IBS mean reversion (overnight signal, next-day open entry)
      6:25 AM PT  — ICT NY Kill Zone   (= 9:25 AM ET, A+ intraday setups)
      10:30 AM PT — ICT NY PM session  (= 1:30 PM ET)
      17:05 PT    — ICT Asia Kill Zone (= 8:05 PM ET)
      23:00 PT    — ICT London Kill Zone (= 2:00 AM ET next day)
      Main loop   — ORB + VWAP MR polls every 5 min during 9:35–10:50 ET (AM)
                    and 13:00–15:30 ET (PM)
    """
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        getattr(schedule.every(), day).at("06:00").do(run_scan)
        getattr(schedule.every(), day).at("06:25").do(run_ict_scan)
        getattr(schedule.every(), day).at("10:30").do(run_ict_ny_pm_scan)
        getattr(schedule.every(), day).at("17:05").do(run_ict_asia_scan)
        getattr(schedule.every(), day).at("23:00").do(run_ict_london_scan)

    schedule.every().sunday.at("20:00").do(send_heartbeat)

    logger.info(
        "Schedule set:\n"
        "  6:00 AM PT Mon–Fri  → IBS mean reversion scan\n"
        "  6:25 AM PT Mon–Fri  → ICT NY Kill Zone scan\n"
        "  9:35–10:50 ET daily → ORB + VWAP MR AM polls (5-min loop)\n"
        "  10:30 AM PT Mon–Fri → ICT NY PM session scan (1:30 PM ET)\n"
        "  13:00–15:30 ET daily→ ORB + VWAP MR PM polls (5-min loop)\n"
        "  17:05 PT Mon–Fri    → ICT Asia Kill Zone scan (8:05 PM ET)\n"
        "  23:00 PT Mon–Fri    → ICT London Kill Zone scan (2:00 AM ET)\n"
        "  8:00 PM PT Sunday   → weekly heartbeat"
    )


# ── Intraday polling — ORB + VWAP MR ─────────────────────────────────────────

# Session windows in ET: (name, start_hour, start_min, end_hour, end_min)
_INTRADAY_SESSIONS_ET = [
    ("asia",   20,  5, 23, 55),
    ("london",  2,  5,  4, 55),
    ("ny_am",   9, 35, 10, 50),
    ("ny_pm",  13, 35, 15, 25),
]

_last_poll_key: str = ""   # track last (session, minute) we ran the intraday scan


def maybe_run_intraday_scan():
    """
    Called from the main loop every 30 s.
    Fires ORB + VWAP MR scanner every 5 minutes within each session window.
    AM session (9:35–10:50 ET) uses run_orb_vwap_scan().
    PM session (13:35–15:25 ET) uses run_orb_vwap_pm_scan().
    """
    global _last_poll_key

    now_et = datetime.now(EASTERN)

    # Weekday only
    if now_et.weekday() >= 5:
        return

    # Reset dedup state at market open each morning
    if now_et.hour == 9 and now_et.minute == 30 and now_et.second < 35:
        reset_orb_vwap_state()
        return

    # Check all session windows
    for sess_name, sh, sm, eh, em in _INTRADAY_SESSIONS_ET:
        sess_open  = now_et.replace(hour=sh, minute=sm, second=0, microsecond=0)
        sess_close = now_et.replace(hour=eh, minute=em, second=0, microsecond=0)
        if not (sess_open <= now_et <= sess_close):
            continue

        # Fire on every 5th minute within the window
        if now_et.minute % 5 != 0:
            continue

        poll_key = f"{sess_name}:{now_et.minute}"
        if poll_key == _last_poll_key:
            continue
        _last_poll_key = poll_key

        logger.info(f"=== ORB+VWAP MR poll [{sess_name}] [{now_et.strftime('%I:%M %p ET')}] ===")
        try:
            if sess_name == "ny_pm":
                run_orb_vwap_pm_scan()
            else:
                run_orb_vwap_scan()
        except Exception as e:
            logger.error(f"ORB+VWAP scan error [{sess_name}]: {e}")
        break  # only fire one session per iteration


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TradeMastery Bot Daemon")
    parser.add_argument("--now", action="store_true", help="Run all scans immediately then keep running")
    parser.add_argument("--test", action="store_true", help="Send test Telegram message and exit")
    args = parser.parse_args()

    if args.test:
        send_test()

    logger.info("=" * 55)
    logger.info("  TradeMastery Bot Daemon starting")
    logger.info(f"  Plan    : {CONFIG.plan.display_name}")
    logger.info(f"  Symbols : {', '.join(CONFIG.scan_symbols)}")
    logger.info(f"  Sessions: Asia KZ (20:05 ET) | London KZ (02:05 ET) | NY AM (09:25 ET) | NY PM (13:30 ET)")
    logger.info(f"  ORB+VWAP: AM polls 9:35-10:50 ET | PM polls 13:35-15:25 ET")
    if CONFIG.sprint_mode:
        logger.info(f"  SPRINT MODE  ICT min score: {CONFIG.ict_min_score}/10  Daily cap: ${CONFIG.sprint_daily_loss_cap:,.0f}")
    logger.info("=" * 55)

    setup_schedule()

    if args.now:
        logger.info("--now flag: running immediate IBS + ICT + ORB+VWAP scans...")
        run_scan()
        run_ict_scan()
        run_orb_vwap_scan()

    # Main loop — schedule checks every 30 s, intraday poll wired in
    while True:
        schedule.run_pending()
        maybe_run_intraday_scan()
        time.sleep(30)


if __name__ == "__main__":
    main()
