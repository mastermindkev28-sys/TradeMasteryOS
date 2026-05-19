"""
Walk-Forward Optimization
--------------------------
Splits data into N in-sample (IS) + out-of-sample (OOS) windows.
Optimises selected parameters on IS, evaluates on OOS.
Produces WF efficiency score: OOS Sharpe / IS Sharpe.

A WF efficiency > 0.5 suggests the strategy is not heavily curve-fit.
"""

import itertools
import logging
import numpy as np
import pandas as pd
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)


def _run_backtest_with_params(df: pd.DataFrame, cfg, param_overrides: dict) -> dict:
    """Apply param overrides and run backtest. Returns metrics dict."""
    from backtest.backtest_engine import Backtester
    cfg_copy = deepcopy(cfg)
    strat_cfg = cfg_copy.ibs if cfg_copy.active_strategy == "ibs" else cfg_copy.dual_thrust
    for k, v in param_overrides.items():
        if hasattr(strat_cfg, k):
            setattr(strat_cfg, k, v)
    bt = Backtester(cfg_copy)
    result = bt.run(df)
    return result


def walk_forward_analysis(
    df: pd.DataFrame,
    cfg,
    param_grid: dict,
    n_splits: int = 5,
    is_pct: float = 0.70,      # 70% in-sample, 30% OOS per window
    metric: str = "sharpe",
) -> dict:
    """
    param_grid example:
        {"ibs_entry_threshold": [0.25, 0.30, 0.35], "band_multiplier": [2.0, 2.5, 3.0]}

    Returns summary with per-window IS/OOS metrics and WF efficiency.
    """
    n = len(df)
    window_size = n // n_splits
    results = []

    logger.info(f"Walk-forward: {n_splits} windows, IS={is_pct*100:.0f}%, OOS={(1-is_pct)*100:.0f}%")

    for i in range(n_splits):
        start = i * window_size
        end = start + window_size
        if i == n_splits - 1:
            end = n

        split_df = df.iloc[start:end]
        is_len = int(len(split_df) * is_pct)
        is_df = split_df.iloc[:is_len]
        oos_df = split_df.iloc[is_len:]

        if len(oos_df) < 20:
            logger.warning(f"Window {i+1}: OOS too small ({len(oos_df)} bars), skipping")
            continue

        # Grid search on IS
        best_params = {}
        best_score = -np.inf
        keys = list(param_grid.keys())
        for combo in itertools.product(*param_grid.values()):
            params = dict(zip(keys, combo))
            try:
                res = _run_backtest_with_params(is_df.copy(), cfg, params)
                from utils.metrics import sharpe_ratio
                ret = res["equity_curve"].pct_change().dropna()
                score = sharpe_ratio(ret) if metric == "sharpe" else float(res["metrics"].get(metric, 0))
                if score > best_score:
                    best_score = score
                    best_params = params
            except Exception as e:
                logger.debug(f"Param combo {params} failed: {e}")

        # Evaluate best params on OOS
        oos_result = _run_backtest_with_params(oos_df.copy(), cfg, best_params)
        from utils.metrics import sharpe_ratio
        oos_ret = oos_result["equity_curve"].pct_change().dropna()
        oos_sharpe = sharpe_ratio(oos_ret)

        results.append({
            "window": i + 1,
            "is_start": df.index[start].date(),
            "is_end": df.index[start + is_len - 1].date(),
            "oos_start": df.index[start + is_len].date(),
            "oos_end": df.index[end - 1].date(),
            "best_params": best_params,
            "is_sharpe": round(best_score, 3),
            "oos_sharpe": round(oos_sharpe, 3),
            "oos_trades": len(oos_result["trade_log"]),
            "oos_net_pnl": round(oos_result["trade_log"]["net_pnl"].sum() if len(oos_result["trade_log"]) else 0, 2),
        })

        logger.info(f"  Window {i+1}: IS Sharpe={best_score:.2f}, OOS Sharpe={oos_sharpe:.2f}, params={best_params}")

    if not results:
        return {"error": "All windows failed"}

    result_df = pd.DataFrame(results)
    wf_efficiency = result_df["oos_sharpe"].mean() / result_df["is_sharpe"].mean() if result_df["is_sharpe"].mean() != 0 else 0
    combined_oos_pnl = result_df["oos_net_pnl"].sum()

    logger.info(f"WF Efficiency: {wf_efficiency:.2f} (>0.5 = acceptable, >0.7 = robust)")

    return {
        "windows": result_df.to_dict("records"),
        "wf_efficiency": round(wf_efficiency, 3),
        "combined_oos_pnl": combined_oos_pnl,
        "avg_oos_sharpe": round(result_df["oos_sharpe"].mean(), 3),
        "interpretation": (
            "ROBUST" if wf_efficiency >= 0.7 else
            "ACCEPTABLE" if wf_efficiency >= 0.5 else
            "LIKELY OVERFIT — revisit strategy parameters"
        ),
    }
