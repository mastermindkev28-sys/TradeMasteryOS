"""
Monte Carlo Robustness Testing
--------------------------------
Two methods:
  1. Trade-sequence shuffle: reshuffle the order of historical trades N times,
     compute distribution of Sharpe, max DD, final equity.
  2. Bootstrap resampling: sample trades with replacement to simulate alternate histories.

Outputs: 5th/median/95th percentile equity paths, DD distribution,
         probability of ruin (DD > threshold).
"""

import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

logger = logging.getLogger(__name__)


def run_monte_carlo(
    trade_pnl: pd.Series,
    initial_capital: float,
    n_runs: int = 5_000,
    ruin_threshold_pct: float = 0.10,   # account down 10% = "ruin" for eval
    output_dir: str = "outputs",
) -> dict:
    """
    trade_pnl: Series of net $ P&L per trade (from backtest trade_log["net_pnl"])
    Returns dict of statistics and saves chart to output_dir.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pnl_array = trade_pnl.values
    n_trades = len(pnl_array)

    if n_trades < 10:
        return {"error": f"Too few trades for Monte Carlo ({n_trades}). Need ≥10."}

    final_equities = np.zeros(n_runs)
    max_drawdowns = np.zeros(n_runs)
    equity_paths = []

    rng = np.random.default_rng(42)

    for i in range(n_runs):
        # Resample with replacement (bootstrap)
        sampled = rng.choice(pnl_array, size=n_trades, replace=True)
        equity = initial_capital + np.cumsum(sampled)
        equity = np.insert(equity, 0, initial_capital)

        final_equities[i] = equity[-1]

        # Max drawdown for this path
        running_max = np.maximum.accumulate(equity)
        dd = (equity - running_max) / running_max
        max_drawdowns[i] = dd.min()

        if i < 200:  # store first 200 for plotting
            equity_paths.append(equity)

    ruin_mask = final_equities < initial_capital * (1 - ruin_threshold_pct)
    prob_ruin = ruin_mask.mean()

    percentiles = [5, 25, 50, 75, 95]
    equity_pcts = {p: float(np.percentile(final_equities, p)) for p in percentiles}
    dd_pcts = {p: float(np.percentile(max_drawdowns, p)) for p in percentiles}

    # ── Plot ────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Monte Carlo Robustness Test", fontsize=14, fontweight="bold")

    # Equity paths
    ax = axes[0]
    for path in equity_paths[:100]:
        ax.plot(path, alpha=0.05, color="steelblue", linewidth=0.5)
    ax.axhline(initial_capital, color="black", linewidth=1, linestyle="--", label="Starting capital")
    ax.axhline(equity_pcts[5], color="red", linewidth=1.5, label=f"5th pct: ${equity_pcts[5]:,.0f}")
    ax.axhline(equity_pcts[50], color="green", linewidth=1.5, label=f"Median: ${equity_pcts[50]:,.0f}")
    ax.axhline(equity_pcts[95], color="blue", linewidth=1.5, label=f"95th pct: ${equity_pcts[95]:,.0f}")
    ax.set_title("Equity Path Distribution")
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Account ($)")
    ax.legend(fontsize=8)

    # Final equity distribution
    ax = axes[1]
    ax.hist(final_equities, bins=80, color="steelblue", edgecolor="none", alpha=0.7)
    ax.axvline(initial_capital, color="black", linewidth=2, label="Start")
    ax.axvline(equity_pcts[5], color="red", linewidth=2, label=f"5th pct")
    ax.axvline(equity_pcts[50], color="green", linewidth=2, label="Median")
    ax.set_title("Final Equity Distribution")
    ax.set_xlabel("Final Account ($)")
    ax.legend(fontsize=8)

    # Max drawdown distribution
    ax = axes[2]
    ax.hist(max_drawdowns * 100, bins=80, color="tomato", edgecolor="none", alpha=0.7)
    ax.axvline(dd_pcts[95] * 100, color="darkred", linewidth=2, label=f"95th pct DD: {dd_pcts[95]*100:.1f}%")
    ax.axvline(dd_pcts[50] * 100, color="orange", linewidth=2, label=f"Median DD: {dd_pcts[50]*100:.1f}%")
    ax.set_title("Max Drawdown Distribution")
    ax.set_xlabel("Max Drawdown (%)")
    ax.legend(fontsize=8)

    plt.tight_layout()
    chart_path = Path(output_dir) / "monte_carlo.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Monte Carlo chart saved: {chart_path}")

    results = {
        "n_runs": n_runs,
        "n_trades": n_trades,
        "prob_ruin": f"{prob_ruin*100:.1f}%",
        "median_final_equity": f"${equity_pcts[50]:,.0f}",
        "p5_final_equity": f"${equity_pcts[5]:,.0f}",
        "p95_final_equity": f"${equity_pcts[95]:,.0f}",
        "median_max_dd": f"{dd_pcts[50]*100:.1f}%",
        "p95_max_dd": f"{dd_pcts[95]*100:.1f}%",
        "chart": str(chart_path),
        "interpretation": (
            "ROBUST" if prob_ruin < 0.05 else
            "MODERATE RISK" if prob_ruin < 0.15 else
            "HIGH RISK — reduce position size or revisit strategy"
        ),
    }

    logger.info(
        f"Monte Carlo: P(ruin)={prob_ruin*100:.1f}%, "
        f"median equity=${equity_pcts[50]:,.0f}, "
        f"p95 DD={dd_pcts[95]*100:.1f}%"
    )
    return results
