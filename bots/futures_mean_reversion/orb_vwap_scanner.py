"""
ORB + VWAP Mean Reversion Scanner
====================================
Polls every 5 minutes during NY AM (9:35–10:50 ET) and NY PM (13:00–15:30 ET).
Sends one Telegram alert per signal type per session per day — no duplicate blasts.

Usage:
    python3 orb_vwap_scanner.py                  # scan all symbols now
    python3 orb_vwap_scanner.py --symbol MNQ     # single symbol
    python3 orb_vwap_scanner.py --dry-run        # print, don't send
    python3 orb_vwap_scanner.py --status         # show OR levels only
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG, CONTRACT_SPECS, YFINANCE_MAP
from strategy.orb_vwap_mr import ORBVWAPStrategy, ORBVWAPConfig, ORBSignal, VWAPMRSignal
from live.telegram_alerts import TelegramAlerter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger("orb_vwap_scanner")

# ── Per-day dedup state ───────────────────────────────────────────────────────
# Tracks which signals have already been sent today (resets each calendar day).
# Key: (symbol, signal_type, session) where session is "am" or "pm".
_sent: dict[tuple, bool] = {}
_sent_date: date | None = None

# Afternoon OR config — opening range from 12:00–13:00 ET, trade until 15:30
AFTERNOON_CONFIG = ORBVWAPConfig(
    or_start="12:00",
    or_end="13:00",
    trade_end="15:30",
)


def _reset_if_new_day():
    global _sent, _sent_date
    today = date.today()
    if _sent_date != today:
        _sent = {}
        _sent_date = today


def _already_sent(symbol: str, signal_type: str, session: str = "am") -> bool:
    _reset_if_new_day()
    return _sent.get((symbol, signal_type, session), False)


def _mark_sent(symbol: str, signal_type: str, session: str = "am"):
    _reset_if_new_day()
    _sent[(symbol, signal_type, session)] = True


# ── Data Fetch ────────────────────────────────────────────────────────────────

def fetch_intraday(symbol: str, period: str = "2d") -> object:
    try:
        import yfinance as yf
        ticker = YFINANCE_MAP.get(symbol, symbol)
        df = yf.download(ticker, period=period, interval="5m",
                         auto_adjust=True, progress=False)
        if df.empty:
            return None
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("America/New_York")
        return df
    except Exception as e:
        logger.error(f"Intraday fetch failed for {symbol}: {e}")
        return None


# ── Telegram Formatters ───────────────────────────────────────────────────────

def format_orb_signal(symbol: str, sig: ORBSignal, cfg=CONFIG) -> str:
    plan = cfg.plan
    spec = CONTRACT_SPECS.get(symbol)
    now  = datetime.now().strftime("%a %b %d  %I:%M %p ET")

    direction_emoji = "🟢" if sig.direction == "long" else "🔴"
    action = "BUY" if sig.direction == "long" else "SELL SHORT"

    risk_str = t1_str = t2_str = "—"
    if spec and sig.is_valid:
        pv            = spec.point_value
        contracts     = plan.max_contracts_default
        risk_pts      = abs(sig.entry - sig.stop)
        risk_str      = f"${risk_pts * pv * contracts:,.0f}  ({contracts} cts × ${risk_pts * pv:.0f})"
        t1_str        = f"${abs(sig.target1 - sig.entry) * pv * contracts:,.0f}"
        t2_str        = f"${abs(sig.target2 - sig.entry) * pv * contracts:,.0f}"

    lines = [
        f"📊 *ORB Signal — {symbol}*  |  {now}",
        "",
        f"{direction_emoji} *{symbol} — {action}*",
        "",
        f"  Entry (market):  `{sig.entry:.2f}`",
        f"  Stop loss:       `{sig.stop:.2f}`",
        f"  Target 1 (50%):  `{sig.target1:.2f}`  → R:R `{sig.r_r1:.1f}:1`  ({t1_str})",
        f"  Target 2 (50%):  `{sig.target2:.2f}`  → R:R `{sig.r_r2:.1f}:1`  ({t2_str})",
        f"  Risk:            `{risk_str}`",
        "",
        f"📐 *Setup*",
        f"  OR High: `{sig.or_high:.2f}`  |  OR Low: `{sig.or_low:.2f}`",
        f"  VWAP:    `{sig.vwap:.2f}`  |  RSI: `{sig.rsi:.1f}`  |  ATR: `{sig.atr:.1f}`",
        f"  _{sig.reason}_",
        "",
        "─────────────────────────────────────────",
        f"🏦 *{plan.display_name}*  |  Max: `{plan.max_contracts_default}` contracts",
        f"📉 Daily limit: `${plan.daily_loss_limit:,.0f}`  |  Trail DD: `${plan.trailing_drawdown:,.0f}`",
        "",
    ]
    if cfg.sprint_mode:
        lines += [
            f"⚡ *SPRINT MODE* — run full `{plan.max_contracts_default}` contracts to TP2. No scale-out.",
            f"⚠️ Hard daily cap: `${cfg.sprint_daily_loss_cap:,.0f}` — stop ALL trading if hit today",
        ]
    else:
        lines.append("⚠️ _TP1 = scale 50% out. Move stop to breakeven. Let TP2 run._")
    return "\n".join(lines)


def format_vwap_mr_signal(symbol: str, sig: VWAPMRSignal, cfg=CONFIG) -> str:
    plan = cfg.plan
    spec = CONTRACT_SPECS.get(symbol)
    now  = datetime.now().strftime("%a %b %d  %I:%M %p ET")

    direction_emoji = "🟢" if sig.direction == "long" else "🔴"
    action = "BUY" if sig.direction == "long" else "SELL SHORT"

    risk_str = target_str = rr_str = "—"
    if spec and sig.is_valid:
        pv        = spec.point_value
        contracts = plan.max_contracts_default
        risk_pts  = abs(sig.entry - sig.stop)
        tgt_pts   = abs(sig.target - sig.entry)
        risk_str  = f"${risk_pts * pv * contracts:,.0f}"
        target_str= f"${tgt_pts * pv * contracts:,.0f}"
        rr_str    = f"{tgt_pts / risk_pts:.1f}:1" if risk_pts > 0 else "—"

    lines = [
        f"🎯 *VWAP Mean Reversion — {symbol}*  |  {now}",
        "",
        f"{direction_emoji} *{symbol} — {action}*",
        "",
        f"  Entry (market):  `{sig.entry:.2f}`",
        f"  Stop loss:       `{sig.stop:.2f}`  (1×ATR = {sig.atr:.1f} pts)",
        f"  Target (VWAP):   `{sig.target:.2f}`  → R:R `{rr_str}`  ({target_str})",
        f"  Risk:            `{risk_str}`",
        "",
        f"📐 *Conditions*",
        f"  VWAP:      `{sig.vwap:.2f}`",
        f"  Deviation: `{sig.deviation_pts:.1f} pts` from VWAP  (threshold: 2×ATR)",
        f"  ADX:       `{sig.adx:.1f}`  ({'✅ ranging' if sig.adx < 22 else '⚠️ trending'})",
        f"  RSI:       `{sig.rsi:.1f}`",
        f"  _{sig.reason}_",
        "",
        "─────────────────────────────────────────",
        f"🏦 *{plan.display_name}*  |  Max: `{plan.max_contracts_default}` contracts",
        f"📉 Daily limit: `${plan.daily_loss_limit:,.0f}`  |  Trail DD: `${plan.trailing_drawdown:,.0f}`",
        "",
    ]
    if cfg.sprint_mode:
        lines += [
            f"⚡ *SPRINT MODE* — `{plan.max_contracts_default}` contracts. Exit at VWAP.",
            f"⚠️ Hard daily cap: `${cfg.sprint_daily_loss_cap:,.0f}` — stop ALL trading if hit today",
        ]
    else:
        lines.append("⚠️ _Mean reversion — exit AT VWAP. Do not hold through._")
    return "\n".join(lines)


def format_no_signal(symbol: str, or_high: float, or_low: float) -> str:
    now = datetime.now().strftime("%a %b %d  %I:%M %p ET")
    return (
        f"📊 *ORB Status — {symbol}*  |  {now}\n\n"
        f"⚪ No signal yet\n"
        f"  OR High: `{or_high:.2f}`  |  OR Low: `{or_low:.2f}`"
    )


# ── Core Scan ─────────────────────────────────────────────────────────────────

def scan_orb_vwap(
    symbol: str,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """
    Check for ORB and VWAP MR signals on `symbol` (AM session).
    Returns list of (signal_type, formatted_message) for new signals only.
    Signals already sent today are skipped. Session key: "am".
    """
    df = fetch_intraday(symbol)
    if df is None or df.empty:
        logger.warning(f"{symbol}: data fetch failed")
        return []

    trade_date = df.index[-1].date()
    strategy   = ORBVWAPStrategy(ORBVWAPConfig())
    results    = []

    # ── ORB ──
    if not _already_sent(symbol, "orb", "am"):
        or_range = strategy.get_opening_range(df, trade_date)
        if or_range:
            or_high, or_low = or_range
            sig = strategy.get_orb_signal(df, or_high, or_low, trade_date)
            if sig.is_valid:
                msg = format_orb_signal(symbol, sig, CONFIG)
                results.append(("orb", msg))
                if not dry_run:
                    _mark_sent(symbol, "orb", "am")
                logger.info(f"{symbol} ORB [AM]: {sig.direction} entry={sig.entry} stop={sig.stop}")
            else:
                logger.info(f"{symbol} ORB [AM]: {sig.reason}")
        else:
            logger.info(f"{symbol}: OR not yet available or too narrow")

    # ── VWAP MR ──
    if not _already_sent(symbol, "vwap_mr", "am"):
        sig = strategy.get_vwap_mr_signal(df, trade_date)
        if sig.is_valid:
            msg = format_vwap_mr_signal(symbol, sig, CONFIG)
            results.append(("vwap_mr", msg))
            if not dry_run:
                _mark_sent(symbol, "vwap_mr", "am")
            logger.info(f"{symbol} VWAP MR [AM]: {sig.direction} dev={sig.deviation_pts:.1f}pts ADX={sig.adx:.1f}")
        else:
            logger.info(f"{symbol} VWAP MR [AM]: {sig.reason}")

    return results


def scan_orb_vwap_pm(
    symbol: str,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """
    Check for ORB and VWAP MR signals on `symbol` (NY PM session, 1:00–3:30 PM ET).
    Opening range defined as 12:00–13:00 ET; trades run until 15:30 ET.
    Returns list of (signal_type, formatted_message) for new signals only.
    Session key: "pm".
    """
    df = fetch_intraday(symbol)
    if df is None or df.empty:
        logger.warning(f"{symbol}: data fetch failed (PM scan)")
        return []

    trade_date = df.index[-1].date()
    strategy   = ORBVWAPStrategy(AFTERNOON_CONFIG)
    results    = []

    # ── ORB (PM) ──
    if not _already_sent(symbol, "orb", "pm"):
        or_range = strategy.get_opening_range(df, trade_date)
        if or_range:
            or_high, or_low = or_range
            sig = strategy.get_orb_signal(df, or_high, or_low, trade_date)
            if sig.is_valid:
                msg = format_orb_signal(symbol, sig, CONFIG)
                results.append(("orb_pm", msg))
                if not dry_run:
                    _mark_sent(symbol, "orb", "pm")
                logger.info(f"{symbol} ORB [PM]: {sig.direction} entry={sig.entry} stop={sig.stop}")
            else:
                logger.info(f"{symbol} ORB [PM]: {sig.reason}")
        else:
            logger.info(f"{symbol}: PM OR not yet available or too narrow")

    # ── VWAP MR (PM) ──
    if not _already_sent(symbol, "vwap_mr", "pm"):
        sig = strategy.get_vwap_mr_signal(df, trade_date)
        if sig.is_valid:
            msg = format_vwap_mr_signal(symbol, sig, CONFIG)
            results.append(("vwap_mr_pm", msg))
            if not dry_run:
                _mark_sent(symbol, "vwap_mr", "pm")
            logger.info(f"{symbol} VWAP MR [PM]: {sig.direction} dev={sig.deviation_pts:.1f}pts ADX={sig.adx:.1f}")
        else:
            logger.info(f"{symbol} VWAP MR [PM]: {sig.reason}")

    return results


def run_orb_vwap_pm_scan(dry_run: bool = False) -> None:
    """Called by bot_daemon every 5 min during NY PM session (13:00–15:30 ET). Sends new alerts."""
    symbols = CONFIG.scan_symbols
    alerter = TelegramAlerter(CONFIG.telegram)

    for symbol in symbols:
        alerts = scan_orb_vwap_pm(symbol, dry_run=dry_run)
        for signal_type, msg in alerts:
            if dry_run:
                print(f"\n{'='*55}")
                print(msg)
                print(f"{'='*55}")
                print(f"[DRY RUN — {signal_type.upper()} not sent]")
            else:
                sent = alerter._send(msg)
                if sent:
                    logger.info(f"{symbol} {signal_type.upper()}: Telegram sent ✅")
                else:
                    logger.warning(f"{symbol} {signal_type.upper()}: Telegram failed")
                    logger.info("\n" + msg)


def run_orb_vwap_scan(dry_run: bool = False) -> None:
    """Called by bot_daemon every 5 min during 9:35–10:50 ET. Sends new alerts."""
    symbols = CONFIG.scan_symbols
    alerter = TelegramAlerter(CONFIG.telegram)

    for symbol in symbols:
        alerts = scan_orb_vwap(symbol, dry_run=dry_run)
        for signal_type, msg in alerts:
            if dry_run:
                print(f"\n{'='*55}")
                print(msg)
                print(f"{'='*55}")
                print(f"[DRY RUN — {signal_type.upper()} not sent]")
            else:
                sent = alerter._send(msg)
                if sent:
                    logger.info(f"{symbol} {signal_type.upper()}: Telegram sent ✅")
                else:
                    logger.warning(f"{symbol} {signal_type.upper()}: Telegram failed")
                    logger.info("\n" + msg)


def reset_orb_vwap_state():
    """Force a state reset (called at start of each day by daemon)."""
    global _sent, _sent_date
    _sent = {}
    _sent_date = None


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ORB + VWAP MR Scanner")
    parser.add_argument("--symbol",  help="Single symbol (e.g. MNQ)")
    parser.add_argument("--dry-run", action="store_true", help="Print without Telegram")
    parser.add_argument("--status",  action="store_true", help="Show OR levels only")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else CONFIG.scan_symbols

    if args.status:
        for symbol in symbols:
            df = fetch_intraday(symbol)
            if df is None:
                print(f"{symbol}: data unavailable")
                continue
            trade_date = df.index[-1].date()
            strategy   = ORBVWAPStrategy()
            or_range   = strategy.get_opening_range(df, trade_date)
            if or_range:
                print(format_no_signal(symbol, *or_range))
            else:
                print(f"{symbol}: OR not yet formed")
        return

    for symbol in symbols:
        alerts = scan_orb_vwap(symbol, dry_run=args.dry_run)
        if not alerts:
            print(f"{symbol}: No new signals")
        if not args.dry_run and alerts:
            alerter = TelegramAlerter(CONFIG.telegram)
            for _, msg in alerts:
                alerter._send(msg)


if __name__ == "__main__":
    main()
