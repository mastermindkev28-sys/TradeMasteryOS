"""
Backtest visualisation: equity curve, drawdown, trade markers, indicator overlays.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path


def plot_backtest(
    equity_curve: pd.Series,
    feature_df: pd.DataFrame,
    trade_log: pd.DataFrame,
    metrics: dict,
    output_dir: str = "outputs",
    title: str = "IBS Mean Reversion — Backtest Results",
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 14))
    fig.suptitle(title, fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.45, wspace=0.3)

    # ── 1. Price + Bands + Trades ─────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(feature_df.index, feature_df["close"], color="black", linewidth=0.8, label="Close")
    if "lower_band" in feature_df.columns:
        ax1.plot(feature_df.index, feature_df["lower_band"], color="royalblue", linewidth=0.8,
                 linestyle="--", label="Lower Band")
    if "trend_sma" in feature_df.columns:
        ax1.plot(feature_df.index, feature_df["trend_sma"], color="orange", linewidth=0.8,
                 linestyle=":", label="300 SMA")

    if len(trade_log) > 0:
        entries = trade_log.dropna(subset=["entry_date", "entry_price"])
        exits = trade_log.dropna(subset=["exit_date", "exit_price"])
        ax1.scatter(entries["entry_date"], entries["entry_price"],
                    marker="^", color="green", zorder=5, s=40, label="Long entry")
        stops = exits[exits["exit_reason"] == "stop"]
        normal_exits = exits[exits["exit_reason"] != "stop"]
        ax1.scatter(stops["exit_date"], stops["exit_price"],
                    marker="x", color="red", zorder=5, s=60, label="Stop exit")
        ax1.scatter(normal_exits["exit_date"], normal_exits["exit_price"],
                    marker="v", color="purple", zorder=5, s=40, label="Signal exit")

    ax1.set_title("Price with Strategy Signals")
    ax1.legend(loc="upper left", fontsize=7)
    ax1.set_ylabel("Price")

    # ── 2. Equity Curve ───────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(equity_curve.index, equity_curve.values, color="steelblue", linewidth=1.2)
    ax2.fill_between(equity_curve.index, equity_curve.min(), equity_curve.values, alpha=0.1, color="steelblue")
    ax2.set_title("Equity Curve")
    ax2.set_ylabel("Account ($)")

    # ── 3. Drawdown ───────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[2, :])
    roll_max = equity_curve.cummax()
    dd = (equity_curve - roll_max) / roll_max * 100
    ax3.fill_between(dd.index, dd.values, 0, alpha=0.6, color="tomato")
    ax3.set_title("Drawdown (%)")
    ax3.set_ylabel("DD %")

    # ── 4. IBS Indicator ─────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[3, 0])
    if "ibs" in feature_df.columns:
        ax4.plot(feature_df.index, feature_df["ibs"], color="purple", linewidth=0.7)
        ax4.axhline(0.30, color="red", linewidth=0.8, linestyle="--", label="Entry threshold 0.30")
        ax4.axhline(0.70, color="green", linewidth=0.8, linestyle="--", label="Exit threshold 0.70")
        ax4.set_ylim(0, 1)
        ax4.set_title("IBS (Internal Bar Strength)")
        ax4.legend(fontsize=7)

    # ── 5. Metrics Table ─────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[3, 1])
    ax5.axis("off")
    rows = [[k, v] for k, v in metrics.items()]
    table = ax5.table(
        cellText=rows,
        colLabels=["Metric", "Value"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.4)
    ax5.set_title("Performance Summary", pad=12)

    out_path = Path(output_dir) / "backtest_results.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return str(out_path)


def plot_walk_forward(wf_results: dict, output_dir: str = "outputs") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    windows = wf_results.get("windows", [])
    if not windows:
        return ""

    df = pd.DataFrame(windows)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Walk-Forward Analysis", fontsize=13, fontweight="bold")

    # IS vs OOS Sharpe per window
    x = df["window"]
    ax = axes[0]
    ax.bar(x - 0.2, df["is_sharpe"], 0.4, label="IS Sharpe", color="steelblue")
    ax.bar(x + 0.2, df["oos_sharpe"], 0.4, label="OOS Sharpe", color="orange")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Window")
    ax.set_ylabel("Sharpe Ratio")
    ax.set_title("In-Sample vs Out-of-Sample Sharpe")
    ax.legend()

    # OOS P&L per window
    ax2 = axes[1]
    colors = ["green" if v >= 0 else "red" for v in df["oos_net_pnl"]]
    ax2.bar(x, df["oos_net_pnl"], color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xlabel("Window")
    ax2.set_ylabel("Net P&L ($)")
    ax2.set_title("Out-of-Sample Net P&L by Window")

    efficiency = wf_results.get("wf_efficiency", 0)
    interpretation = wf_results.get("interpretation", "")
    fig.text(0.5, -0.02, f"WF Efficiency: {efficiency:.2f} — {interpretation}",
             ha="center", fontsize=10, color="darkgreen" if efficiency >= 0.5 else "red")

    out_path = Path(output_dir) / "walk_forward.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return str(out_path)
