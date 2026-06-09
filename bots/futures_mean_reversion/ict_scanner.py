"""
ICT NY Kill Zone Daily Scanner
================================
Runs at 9:25 AM ET — fetches 5-min intraday data, detects ICT setups,
and sends a Telegram alert with full trade details.

Usage:
    python3 ict_scanner.py                     # scan all symbols
    python3 ict_scanner.py --symbol MNQ        # single symbol
    python3 ict_scanner.py --dry-run           # print without sending
    python3 ict_scanner.py --status            # send setup levels only (pre-market)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG, CONTRACT_SPECS, YFINANCE_MAP
from strategy.ict_ny_killzone import ICTNYKillzone, ICTNYKillzoneConfig, ICTSignal
from live.telegram_alerts import TelegramAlerter

# SMT divergence pairs: primary → secondary instrument for cross-market confirmation
SMT_PAIRS: dict[str, str] = {
    "MNQ": "MES",   # Nasdaq Mini → S&P500 Mini
    "MES": "MNQ",
    "MGC": "GC=F",  # Micro Gold → full Gold
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger("ict_scanner")


# ─── Data Fetcher ─────────────────────────────────────────────────────────────

def fetch_intraday(symbol: str, interval: str = "5m", period: str = "5d"):
    """Fetch intraday bars via yfinance."""
    try:
        import yfinance as yf
        ticker = YFINANCE_MAP.get(symbol, symbol)
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df.empty:
            return None
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        # Convert index to ET
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("America/New_York")
        return df
    except Exception as e:
        logger.error(f"Intraday fetch failed for {symbol}: {e}")
        return None


def fetch_daily(symbol: str, period: str = "60d"):
    """Fetch daily bars for prev-day levels."""
    try:
        import yfinance as yf
        ticker = YFINANCE_MAP.get(symbol, symbol)
        df = yf.download(ticker, period=period, interval="1d",
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
        logger.error(f"Daily fetch failed for {symbol}: {e}")
        return None


# ─── Telegram Formatter ───────────────────────────────────────────────────────

def format_ict_signal(symbol: str, sig: ICTSignal, cfg=CONFIG) -> str:
    """Format an ICTSignal as a Telegram Markdown message."""
    plan = cfg.plan
    spec = CONTRACT_SPECS.get(symbol)
    now  = datetime.now().strftime("%a %b %d  %I:%M %p ET")

    lines = [f"🎯 *ICT NY Kill Zone — {symbol}*  |  {now}", ""]

    if not sig.is_valid:
        lines += [
            f"⚪ *No Setup Today*",
            f"_{sig.reason}_",
        ]
        if sig.pdl:
            lines += [
                "",
                f"📌 *Key Levels*",
                f"  Prev Day High: `{sig.pdl.high:.2f}`",
                f"  Prev Day Low:  `{sig.pdl.low:.2f}`",
                f"  PDH–PDL Range: `{sig.pdl.range_pts:.0f} pts`",
            ]
        return "\n".join(lines)

    # Valid signal
    direction_emoji = "🟢" if sig.direction == "long" else "🔴"
    action = "BUY" if sig.direction == "long" else "SELL SHORT"

    # Dollar risk/reward per contract
    if spec:
        pv = spec.point_value
        risk_per_ct   = sig.stop_pts * pv
        profit1_per_ct = abs(sig.target1 - sig.entry) * pv
        profit2_per_ct = abs(sig.target2 - sig.entry) * pv
        contracts     = plan.max_contracts_default
        total_risk    = risk_per_ct   * contracts
        total_t1      = profit1_per_ct * contracts
        total_t2      = profit2_per_ct * contracts
        risk_str      = f"${total_risk:,.0f}  ({contracts} contracts × ${risk_per_ct:.0f})"
        t1_str        = f"${total_t1:,.0f}"
        t2_str        = f"${total_t2:,.0f}"
    else:
        risk_str = f"{sig.stop_pts:.1f} pts"
        t1_str = t2_str = "—"

    lines += [
        f"{direction_emoji} *{symbol} — {action}*",
        "",
        f"  Entry (limit):   `{sig.entry:.2f}`",
        f"  Stop loss:       `{sig.stop:.2f}`  ({sig.stop_pts:.1f} pts)",
        f"  Target 1 (50%):  `{sig.target1:.2f}`  → R:R `{sig.r_r1:.1f}:1`  ({t1_str})",
        f"  Target 2 (50%):  `{sig.target2:.2f}`  → R:R `{sig.r_r2:.1f}:1`  ({t2_str})",
        f"  Risk:            `{risk_str}`",
        "",
        f"📐 *Setup*",
        f"  Type:   `{sig.setup_type.upper()}`",
        f"  Score:  `{sig.score.total}/10` ({sig.score.grade})" if sig.score else "",
    ]

    if sig.score:
        lines.append(f"```\n{sig.score.breakdown()}\n```")

    if sig.judas:
        swept = "PDH" if sig.judas.direction == "bearish" else "PDL"
        lines.append(f"  Judas:  swept {swept} @ `{sig.judas.swept_level:.2f}`")

    if sig.mss:
        lines.append(f"  MSS:    {sig.mss.direction} @ `{sig.mss.broken_level:.2f}` {'(displaced ✅)' if sig.mss.displacement else ''}")

    if sig.fvg:
        lines.append(f"  FVG:    `{sig.fvg.bottom:.2f}` – `{sig.fvg.top:.2f}` ({sig.fvg.size_pts:.1f} pts)")

    if sig.pdl:
        lines += [
            "",
            f"📌 *Prev Day Levels*",
            f"  PDH: `{sig.pdl.high:.2f}`  |  PDL: `{sig.pdl.low:.2f}`  |  Range: `{sig.pdl.range_pts:.0f} pts`",
        ]

    lines += [
        "",
        "─────────────────────────────────────────",
        f"🏦 *{plan.display_name}*  |  Max: `{plan.max_contracts_default}` contracts",
        f"📉 Daily limit: `${plan.daily_loss_limit:,.0f}`  |  Trail DD: `${plan.trailing_drawdown:,.0f}`",
    ]

    if cfg.sprint_mode:
        lines += [
            "",
            f"⚡ *SPRINT MODE*  |  Score threshold: `{cfg.ict_min_score}/10`",
            f"⚠️ Hard daily loss cap: `${cfg.sprint_daily_loss_cap:,.0f}`  — stop ALL trading if hit",
        ]

    return "\n".join(lines)


# ─── Scan ─────────────────────────────────────────────────────────────────────

def scan_ict(symbol: str) -> tuple[ICTSignal, str]:
    """Run ICT scan for one symbol. Returns (signal, formatted_message)."""
    logger.info(f"Scanning {symbol}...")

    intraday = fetch_intraday(symbol)
    daily    = fetch_daily(symbol)

    if intraday is None or daily is None:
        from strategy.ict_ny_killzone import ICTSignal
        sig = ICTSignal(direction="no_setup", reason="Data fetch failed")
        return sig, f"⚠️ *{symbol}* — data fetch failed"

    # Fetch secondary instrument for SMT divergence
    secondary = None
    smt_partner = SMT_PAIRS.get(symbol)
    if smt_partner:
        secondary = fetch_intraday(smt_partner)
        if secondary is None:
            logger.warning(f"SMT secondary ({smt_partner}) unavailable — scoring without it")

    strategy = ICTNYKillzone(ICTNYKillzoneConfig(min_score=CONFIG.ict_min_score))
    sig = strategy.get_signal(intraday, daily, secondary_df=secondary)

    logger.info(
        f"{symbol}: direction={sig.direction}  "
        f"{'entry=' + str(sig.entry) + '  score=' + str(sig.score.total) + '/10' if sig.is_valid else sig.reason[:60]}"
    )

    msg = format_ict_signal(symbol, sig, CONFIG)
    return sig, msg


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ICT NY Kill Zone Scanner")
    parser.add_argument("--symbol", help="Single symbol to scan (e.g. MNQ)")
    parser.add_argument("--dry-run", action="store_true", help="Print without sending Telegram")
    parser.add_argument("--status", action="store_true", help="Pre-market levels only")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else CONFIG.scan_symbols

    for symbol in symbols:
        sig, msg = scan_ict(symbol)

        if args.dry_run:
            print("\n" + "=" * 55)
            print(msg)
            print("=" * 55)
            print("[DRY RUN — not sent]")
        else:
            alerter = TelegramAlerter(CONFIG.telegram)
            sent = alerter._send(msg)
            if sent:
                logger.info(f"{symbol}: Telegram sent ✅")
            else:
                logger.warning(f"{symbol}: Telegram failed")
                print(msg)


if __name__ == "__main__":
    main()
