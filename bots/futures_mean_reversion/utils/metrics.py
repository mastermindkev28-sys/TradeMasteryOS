"""
Performance metrics: Sharpe, Sortino, Calmar, profit factor, win rate, CAGR, max DD.
All functions accept a pd.Series of daily returns or a trade log DataFrame.
"""

import numpy as np
import pandas as pd
from typing import Optional


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.05, periods: int = 252) -> float:
    """Annualised Sharpe ratio from daily returns."""
    excess = returns - risk_free / periods
    if returns.std() == 0:
        return 0.0
    return float(np.sqrt(periods) * excess.mean() / excess.std())


def sortino_ratio(returns: pd.Series, risk_free: float = 0.05, periods: int = 252) -> float:
    excess = returns - risk_free / periods
    downside = excess[excess < 0].std()
    if downside == 0:
        return 0.0
    return float(np.sqrt(periods) * excess.mean() / downside)


def max_drawdown(equity_curve: pd.Series) -> tuple[float, pd.Timestamp, pd.Timestamp]:
    """Returns (max_dd_pct, peak_date, trough_date)."""
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve - roll_max) / roll_max
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    peak_idx = equity_curve[:trough_idx].idxmax()
    return float(max_dd), peak_idx, trough_idx


def calmar_ratio(equity_curve: pd.Series, periods: int = 252) -> float:
    """CAGR / |max drawdown|."""
    cagr = compute_cagr(equity_curve, periods)
    dd, _, _ = max_drawdown(equity_curve)
    if dd == 0:
        return 0.0
    return float(cagr / abs(dd))


def compute_cagr(equity_curve: pd.Series, periods: int = 252) -> float:
    n_years = len(equity_curve) / periods
    if n_years == 0 or equity_curve.iloc[0] == 0:
        return 0.0
    return float((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / n_years) - 1)


def profit_factor(trade_pnl: pd.Series) -> float:
    gross_wins = trade_pnl[trade_pnl > 0].sum()
    gross_losses = abs(trade_pnl[trade_pnl < 0].sum())
    if gross_losses == 0:
        return float("inf")
    return float(gross_wins / gross_losses)


def win_rate(trade_pnl: pd.Series) -> float:
    if len(trade_pnl) == 0:
        return 0.0
    return float((trade_pnl > 0).mean())


def avg_win_loss_ratio(trade_pnl: pd.Series) -> float:
    wins = trade_pnl[trade_pnl > 0]
    losses = trade_pnl[trade_pnl < 0]
    if len(losses) == 0 or losses.mean() == 0:
        return float("inf")
    return float(wins.mean() / abs(losses.mean()))


def expectancy(trade_pnl: pd.Series) -> float:
    """Average $ per trade."""
    return float(trade_pnl.mean()) if len(trade_pnl) else 0.0


def compute_all_metrics(
    equity_curve: pd.Series,
    trade_pnl: pd.Series,
    initial_capital: float,
    periods_per_year: int = 252,
) -> dict:
    returns = equity_curve.pct_change().dropna()
    dd, peak_dt, trough_dt = max_drawdown(equity_curve)

    return {
        "total_trades": len(trade_pnl),
        "win_rate": f"{win_rate(trade_pnl)*100:.1f}%",
        "profit_factor": f"{profit_factor(trade_pnl):.2f}",
        "avg_win_loss_ratio": f"{avg_win_loss_ratio(trade_pnl):.2f}",
        "expectancy_per_trade": f"${expectancy(trade_pnl):.2f}",
        "net_pnl": f"${trade_pnl.sum():,.2f}",
        "cagr": f"{compute_cagr(equity_curve, periods_per_year)*100:.1f}%",
        "sharpe": f"{sharpe_ratio(returns, periods=periods_per_year):.2f}",
        "sortino": f"{sortino_ratio(returns, periods=periods_per_year):.2f}",
        "calmar": f"{calmar_ratio(equity_curve, periods_per_year):.2f}",
        "max_drawdown": f"{dd*100:.1f}%",
        "max_dd_peak": str(peak_dt)[:10],
        "max_dd_trough": str(trough_dt)[:10],
        "final_equity": f"${equity_curve.iloc[-1]:,.2f}",
        "return_on_capital": f"{(equity_curve.iloc[-1]/initial_capital - 1)*100:.1f}%",
    }
