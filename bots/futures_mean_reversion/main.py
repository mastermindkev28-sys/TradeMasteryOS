"""
TradeMasteryOS — Futures Mean Reversion Bot
============================================
Entry points:
  python main.py backtest          → full backtest + charts
  python main.py backtest --wf     → with walk-forward optimization
  python main.py backtest --mc     → with Monte Carlo simulation
  python main.py live              → live/paper trading loop
  python main.py signal            → print today's signal and exit

Quick start:
  pip install -r requirements.txt
  python main.py backtest --wf --mc
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

# ── Bootstrap path so sub-packages resolve correctly ─────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG
from data.loader import load_data
from backtest.backtest_engine import Backtester
from backtest.monte_carlo import run_monte_carlo
from backtest.walk_forward import walk_forward_analysis
from backtest.plotter import plot_backtest, plot_walk_forward
from strategy.ibs_mean_reversion import IBSMeanReversion


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_backtest(args):
    cfg = CONFIG
    logger = logging.getLogger("main")
    logger.info(f"=== Backtest: {cfg.contract.symbol} | {cfg.backtest.start_date} → {cfg.backtest.end_date} ===")

    # Load data
    df = load_data(cfg)

    # Run backtest
    bt = Backtester(cfg)
    result = bt.run(df)
    equity = result["equity_curve"]
    trades = result["trade_log"]
    metrics = result["metrics"]

    # Print metrics
    print("\n" + "=" * 55)
    print(f"  {cfg.contract.symbol} IBS Mean Reversion — Results")
    print("=" * 55)
    for k, v in metrics.items():
        print(f"  {k:<30} {v}")
    print("=" * 55)

    # Save trade log
    out_dir = cfg.backtest.output_dir
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    if len(trades) > 0:
        trades.to_csv(f"{out_dir}/trade_log.csv", index=False)
        print(f"\n  Trade log → {out_dir}/trade_log.csv")

    # Charts
    chart_path = plot_backtest(equity, result["feature_df"], trades, metrics, out_dir)
    print(f"  Backtest chart → {chart_path}")

    # Walk-forward
    if args.wf:
        print("\n[Walk-Forward Optimization]")
        param_grid = {
            "ibs_entry_threshold": [0.25, 0.30, 0.35],
            "band_multiplier": [2.0, 2.5, 3.0],
        }
        wf = walk_forward_analysis(df, cfg, param_grid, n_splits=cfg.backtest.walk_forward_splits)
        print(f"  WF Efficiency: {wf.get('wf_efficiency', 'N/A')} — {wf.get('interpretation', '')}")
        print(f"  Avg OOS Sharpe: {wf.get('avg_oos_sharpe', 'N/A')}")
        wf_chart = plot_walk_forward(wf, out_dir)
        if wf_chart:
            print(f"  Walk-forward chart → {wf_chart}")
        with open(f"{out_dir}/walk_forward.json", "w") as f:
            json.dump(wf, f, indent=2, default=str)

    # Monte Carlo
    if args.mc and len(trades) > 0:
        print("\n[Monte Carlo Robustness Test]")
        mc = run_monte_carlo(
            trades["net_pnl"],
            cfg.backtest.initial_capital,
            n_runs=cfg.backtest.monte_carlo_runs,
            output_dir=out_dir,
        )
        for k, v in mc.items():
            if k not in ("chart",):
                print(f"  {k:<30} {v}")
        print(f"  Monte Carlo chart → {mc.get('chart', 'N/A')}")

    print(f"\n  All outputs saved to: {out_dir}/")


def cmd_signal(args):
    cfg = CONFIG
    df = load_data(cfg)
    strat = IBSMeanReversion(cfg.ibs)
    sig = strat.latest_signal(df)
    print(f"\nLatest signal for {cfg.contract.symbol}:")
    print(f"  Direction : {sig.direction.upper()}")
    print(f"  IBS       : {sig.ibs:.3f} (threshold {cfg.ibs.ibs_entry_threshold})")
    print(f"  Lower band: {sig.lower_band:.2f}")
    print(f"  Trend SMA : {sig.trend_filter:.2f}")
    print(f"  ATR       : {sig.atr:.2f}")
    print(f"  Reason    : {sig.reason}")


def cmd_live(args):
    from live.live_engine import LiveEngine
    engine = LiveEngine(CONFIG)
    engine.start()


def main():
    parser = argparse.ArgumentParser(
        description="TradeMasteryOS — Futures Mean Reversion Bot"
    )
    sub = parser.add_subparsers(dest="command")

    bt_parser = sub.add_parser("backtest", help="Run historical backtest")
    bt_parser.add_argument("--wf", action="store_true", help="Include walk-forward optimization")
    bt_parser.add_argument("--mc", action="store_true", help="Include Monte Carlo simulation")

    sub.add_parser("signal", help="Print today's trading signal")
    sub.add_parser("live", help="Start live/paper trading loop")

    args = parser.parse_args()
    setup_logging(CONFIG.log_level)

    if args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "signal":
        cmd_signal(args)
    elif args.command == "live":
        cmd_live(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
