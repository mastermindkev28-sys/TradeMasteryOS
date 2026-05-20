"""
Daily Signal Scanner — MNQ + MGC
----------------------------------
Run once after 4pm ET close (or schedule with cron).
Scans both symbols, formats a Telegram message, and sends it.
No broker connection required — uses yfinance for data.

Usage:
  python scanner.py                  # scan all symbols in config
  python scanner.py --symbol MNQ     # scan one symbol only
  python scanner.py --dry-run        # print message, don't send Telegram

Cron (run at 4:15pm ET Mon-Fri):
  15 16 * * 1-5 cd /path/to/bot && python scanner.py >> logs/scanner.log 2>&1
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG, CONTRACT_SPECS, YFINANCE_MAP
from strategy.ibs_mean_reversion import IBSMeanReversion
from live.telegram_alerts import TelegramAlerter
from utils.position_sizing import fixed_fractional_contracts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger("scanner")


def fetch_bars(symbol: str, n: int = 350):
    """Pull daily bars from yfinance. Returns DataFrame or None."""
    try:
        import yfinance as yf
        import pandas as pd
        ticker = YFINANCE_MAP.get(symbol, symbol)
        df = yf.download(ticker, period="5y", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close", "volume"]].dropna().tail(n)
    except Exception as e:
        logger.error(f"Data fetch failed for {symbol}: {e}")
        return None


def scan_symbol(symbol: str, cfg=CONFIG) -> dict:
    """
    Returns a result dict for one symbol:
      signal, ibs, lower_band, trend_sma, atr,
      suggested_contracts, stop_price, reason
    """
    spec = CONTRACT_SPECS.get(symbol)
    if not spec:
        return {"symbol": symbol, "error": f"No contract spec for {symbol}"}

    df = fetch_bars(symbol)
    if df is None or len(df) < cfg.ibs.trend_filter_sma + 5:
        return {"symbol": symbol, "error": "Insufficient data"}

    strat = IBSMeanReversion(cfg.ibs)
    sig = strat.latest_signal(df, current_position=0)

    contracts = 0
    stop_price = None
    if sig.direction == "long":
        contracts = fixed_fractional_contracts(
            account_balance=cfg.backtest.initial_capital,
            risk_pct=cfg.risk.risk_pct_per_trade,
            atr=sig.atr,
            atr_stop_mult=cfg.risk.atr_stop_multiplier,
            point_value=spec.point_value,
            max_contracts=cfg.risk.max_contracts,
        )
        last_close = float(df["close"].iloc[-1])
        stop_price = round(last_close - cfg.risk.atr_stop_multiplier * sig.atr, 2)

    return {
        "symbol": symbol,
        "signal": sig.direction,
        "ibs": sig.ibs,
        "lower_band": sig.lower_band,
        "trend_sma": sig.trend_filter,
        "atr": sig.atr,
        "last_close": float(df["close"].iloc[-1]),
        "last_date": str(df.index[-1].date()),
        "suggested_contracts": contracts,
        "stop_price": stop_price,
        "reason": sig.reason,
        "error": None,
    }


def format_telegram_message(results: list[dict], cfg=CONFIG) -> str:
    now = datetime.now().strftime("%a %b %d, %Y  %I:%M %p ET")
    lines = [f"📋 *Daily Signal Scan*  —  {now}", ""]

    any_signal = False
    for r in results:
        if r.get("error"):
            lines.append(f"⚠️  *{r['symbol']}* — {r['error']}")
            continue

        sym = r["symbol"]
        sig = r["signal"]

        if sig == "long":
            any_signal = True
            risk_dollars = r["suggested_contracts"] * r["atr"] * cfg.risk.atr_stop_multiplier
            spec = CONTRACT_SPECS.get(sym)
            risk_dollars *= spec.point_value if spec else 1

            lines += [
                f"🟢 *{sym} — LONG SIGNAL*",
                f"  Entry:      near `{r['last_close']:.2f}` at tomorrow's open",
                f"  Stop:       `{r['stop_price']:.2f}`  ({cfg.risk.atr_stop_multiplier}× ATR)",
                f"  Contracts:  `{r['suggested_contracts']}`  (risk ≈ ${risk_dollars:.0f})",
                f"  IBS:        `{r['ibs']:.3f}`  (threshold {cfg.ibs.ibs_entry_threshold})",
                f"  Band:       `{r['lower_band']:.2f}`  |  SMA300: `{r['trend_sma']:.2f}`",
                "",
            ]
        else:
            lines += [
                f"⚪ *{sym} — No signal*",
                f"  IBS: `{r['ibs']:.3f}`  |  Band: `{r['lower_band']:.2f}`  |  Close: `{r['last_close']:.2f}`",
                "",
            ]

    if not any_signal:
        lines.append("_No actionable signals today. Stay patient._")

    lines += [
        "─────────────────────────────",
        f"Account: Lucid 25K  |  Risk/trade: {cfg.risk.risk_pct_per_trade*100:.1f}%",
        f"Daily loss limit: ${cfg.backtest.initial_capital * cfg.risk.daily_loss_limit_pct:.0f}  "
        f"|  Trailing DD limit: ${cfg.backtest.initial_capital * cfg.risk.trailing_drawdown_pct:.0f}",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily IBS Signal Scanner")
    parser.add_argument("--symbol", help="Scan a single symbol (e.g. MNQ)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the Telegram message without sending")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else CONFIG.scan_symbols
    logger.info(f"Scanning: {symbols}")

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

    if args.dry_run:
        print("\n" + "=" * 50)
        print(message)
        print("=" * 50)
        print("\n[DRY RUN — message not sent]")
    else:
        alerter = TelegramAlerter(CONFIG.telegram)
        sent = alerter._send(message)
        if sent:
            logger.info("Telegram alert sent successfully.")
        else:
            logger.warning(
                "Telegram not configured or send failed. "
                "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars."
            )
            print("\n" + message)


if __name__ == "__main__":
    main()
