"""
ORB + VWAP Mean Reversion Scanner
====================================
Polls every 5 minutes during the NY session (9:35–10:50 ET).
Sends one Telegram alert per signal type per day — no duplicate blasts.

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
_sent: dict[str, dict[str, bool]] = {}   # {symbol: {"orb": bool, "vwap_mr": bool}}
_sent_date: date | None = None


def _reset_if_new_day():
    global _sent, _sent_date
    today = date.today()
    if _sent_date != today:
        _sent = {}
        _sent_date = today


def _already_sent(symbol: str, signal_type: str) -> bool:
    _reset_if_new_day()
    return _sent.get(symbol, {}).get(signal_type, False)


def _mark_sent(symbol: str, signal_type: str):
    _reset_if_new_day()
    _sent.setdefault(symbol, {})[signal_type] = True


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
        "⚠️ _TP1 = scale 50% out. Move stop to breakeven. Let TP2 run._",
    ]
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
        "⚠️ _Mean reversion — exit AT VWAP. Do not hold through._",
    ]
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
    Check for ORB and VWAP MR signals on `symbol`.
    Returns list of (signal_type, formatted_message) for new signals only.
    Signals already sent today are skipped.
    """
    df = fetch_intraday(symbol)
    if df is None or df.empty:
        logger.warning(f"{symbol}: data fetch failed")
        return []

    trade_date = df.index[-1].date()
    strategy   = ORBVWAPStrategy(ORBVWAPConfig())
    results    = []

    # ── ORB ──
    if not _already_sent(symbol, "orb"):
        or_range = strategy.get_opening_range(df, trade_date)
        if or_range:
            or_high, or_low = or_range
            sig = strategy.get_orb_signal(df, or_high, or_low, trade_date)
            if sig.is_valid:
                msg = format_orb_signal(symbol, sig, CONFIG)
                results.append(("orb", msg))
                if not dry_run:
                    _mark_sent(symbol, "orb")
                logger.info(f"{symbol} ORB: {sig.direction} entry={sig.entry} stop={sig.stop}")
            else:
                logger.info(f"{symbol} ORB: {sig.reason}")
        else:
            logger.info(f"{symbol}: OR not yet available or too narrow")

    # ── VWAP MR ──
    if not _already_sent(symbol, "vwap_mr"):
        sig = strategy.get_vwap_mr_signal(df, trade_date)
        if sig.is_valid:
            msg = format_vwap_mr_signal(symbol, sig, CONFIG)
            results.append(("vwap_mr", msg))
            if not dry_run:
                _mark_sent(symbol, "vwap_mr")
            logger.info(f"{symbol} VWAP MR: {sig.direction} dev={sig.deviation_pts:.1f}pts ADX={sig.adx:.1f}")
        else:
            logger.info(f"{symbol} VWAP MR: {sig.reason}")

    return results


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
