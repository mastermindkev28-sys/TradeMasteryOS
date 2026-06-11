"""
Daily Signal Scanner — MNQ + MGC (multi-symbol, multi-plan)
------------------------------------------------------------
Run once after 4pm ET close (or schedule via cron/Task Scheduler).
Reads daily bars from yfinance — no broker API needed.

Usage:
  python scanner.py                          # uses PROP_FIRM_PLAN env var (default: lucid_25k)
  python scanner.py --plan topstep_100k      # override plan for this run
  python scanner.py --symbol MNQ             # single symbol
  python scanner.py --list-plans             # print all supported plans and exit
  python scanner.py --dry-run                # print message, skip Telegram send

Available plans (--list-plans for full table):
  Lucid:   lucid_10k, lucid_25k, lucid_50k, lucid_100k, lucid_150k
  TopStep: topstep_50k, topstep_100k, topstep_150k

Cron (4:15pm ET Mon-Fri):
  15 16 * * 1-5 cd /path/to/bot && source .env && python scanner.py >> logs/scanner.log 2>&1
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG, CONTRACT_SPECS, PROP_FIRM_PLANS
from strategy.ibs_mean_reversion import IBSMeanReversion
from live.telegram_alerts import TelegramAlerter
from live.tv_feed import fetch_daily as tv_fetch_daily
from utils.position_sizing import fixed_fractional_contracts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger("scanner")


def fetch_bars(symbol: str, n: int = 350):
    """Pull daily bars from TradingView. Returns DataFrame or None."""
    df = tv_fetch_daily(symbol, n_bars=n)
    if df is None:
        logger.error(f"Data fetch failed for {symbol}")
    return df


def scan_symbol(symbol: str, cfg=CONFIG) -> dict:
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
    plan = cfg.plan
    now = datetime.now().strftime("%a %b %d, %Y  %I:%M %p ET")
    lines = [f"📋 *Daily Signal Scan*  —  {now}", ""]

    any_signal = False
    for r in results:
        if r.get("error"):
            lines.append(f"⚠️  *{r['symbol']}* — {r['error']}")
            lines.append("")
            continue

        sym = r["symbol"]
        sig = r["signal"]

        if sig == "long":
            any_signal = True
            spec = CONTRACT_SPECS.get(sym)
            risk_dollars = (
                r["suggested_contracts"]
                * r["atr"]
                * cfg.risk.atr_stop_multiplier
                * (spec.point_value if spec else 1)
            )
            pct_of_daily = risk_dollars / plan.daily_loss_limit * 100

            lines += [
                f"🟢 *{sym} — LONG SIGNAL*",
                f"  Entry:      near `{r['last_close']:.2f}` at tomorrow's open",
                f"  Stop:       `{r['stop_price']:.2f}`  ({cfg.risk.atr_stop_multiplier}× ATR)",
                f"  Contracts:  `{r['suggested_contracts']}`  "
                f"(risk ≈ ${risk_dollars:.0f} = {pct_of_daily:.0f}% of daily limit)",
                f"  IBS:        `{r['ibs']:.3f}`  (threshold ≤ {cfg.ibs.ibs_entry_threshold})",
                f"  Band:       `{r['lower_band']:.2f}`  |  SMA300: `{r['trend_sma']:.2f}`",
                "",
            ]
        else:
            lines += [
                f"⚪ *{sym} — No signal*",
                f"  IBS: `{r['ibs']:.3f}`  |  Band: `{r['lower_band']:.2f}`"
                f"  |  Close: `{r['last_close']:.2f}`",
                "",
            ]

    if not any_signal:
        lines.append("_No actionable signals today. Stay patient._")
        lines.append("")

    progress_bar = _progress_bar(plan)
    lines += [
        "─────────────────────────────────────────",
        f"🏦  *{plan.display_name}*  |  Risk/trade: {cfg.risk.risk_pct_per_trade*100:.1f}%",
        f"📉  Daily loss limit: `${plan.daily_loss_limit:,.0f}`"
        f"  |  Trailing DD: `${plan.trailing_drawdown:,.0f}`",
        f"🎯  Profit target: `${plan.profit_target:,.0f}`"
        f"  |  Min days: `{plan.min_trading_days}`",
        f"📊  Max contracts: `{plan.max_contracts_default}`",
        progress_bar,
    ]

    return "\n".join(lines)


def _progress_bar(plan, width: int = 20) -> str:
    """Shows what % of profit target the daily limit represents (risk context)."""
    ratio = plan.daily_loss_limit / plan.profit_target
    filled = round(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"Daily limit is {ratio*100:.0f}% of target  [{bar}]"


def print_plans_table():
    header = f"{'Key':<20} {'Firm':<10} {'Account':>10} {'Target':>10} {'Daily Limit':>12} {'Trail DD':>10} {'Max Cts':>8}"
    print(header)
    print("-" * len(header))
    for p in PROP_FIRM_PLANS.values():
        print(
            f"{p.key:<20} {p.firm:<10} ${p.account_size:>9,.0f} "
            f"${p.profit_target:>9,.0f} ${p.daily_loss_limit:>11,.0f} "
            f"${p.trailing_drawdown:>9,.0f} {p.max_contracts_default:>8}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="TradeMastery Daily IBS Signal Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--plan", help="Prop firm plan key (e.g. topstep_100k, lucid_50k)")
    parser.add_argument("--symbol", help="Scan a single symbol (e.g. MNQ, MGC)")
    parser.add_argument("--list-plans", action="store_true", help="Print all supported plans and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print message without sending Telegram")
    args = parser.parse_args()

    if args.list_plans:
        print_plans_table()
        return

    # Apply plan (CLI arg overrides env var overrides default)
    if args.plan:
        try:
            CONFIG.apply_plan(args.plan)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    plan = CONFIG.plan
    logger.info(f"Plan: {plan.display_name}  "
                f"(target ${plan.profit_target:,.0f} | "
                f"daily limit ${plan.daily_loss_limit:,.0f} | "
                f"trailing DD ${plan.trailing_drawdown:,.0f})")

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
        print("\n[DRY RUN — Telegram not sent]")
        return

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
