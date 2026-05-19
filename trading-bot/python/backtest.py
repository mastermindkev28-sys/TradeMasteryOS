"""
GoldMaster Pro — Backtesting Engine
Realistic backtest with slippage, spreads, and prop firm risk rules.
Reports expected weekly P&L projections.
"""
import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
warnings.filterwarnings("ignore")

from config import (
    ACCOUNT_SIZE, RISK_PER_TRADE_PCT, MAX_DAILY_LOSS_PCT,
    MAX_TOTAL_DD_PCT, MAX_TRADES_PER_DAY, MIN_RR,
    SL_ATR_MULT, TP_ATR_MULT, ATR_PERIOD,
    WEEKLY_TARGET_LOW, WEEKLY_TARGET_HIGH
)
from feature_engineering import compute_features, create_labels, get_feature_columns

log = logging.getLogger("GoldMaster.Backtest")

# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────
@dataclass
class Trade:
    entry_time:  datetime
    exit_time:   Optional[datetime]
    direction:   int        # 1=BUY, -1=SELL
    entry_price: float
    sl_price:    float
    tp_price:    float
    lot_size:    float
    risk_usd:    float
    pnl:         float = 0.0
    outcome:     str   = ""  # WIN / LOSS / BE
    r_multiple:  float = 0.0
    score:       float = 0.0
    strategy:    str   = ""


@dataclass
class BacktestResult:
    initial_equity:  float
    final_equity:    float
    total_trades:    int
    winning_trades:  int
    losing_trades:   int
    win_rate:        float
    avg_win:         float
    avg_loss:        float
    profit_factor:   float
    max_drawdown:    float
    max_drawdown_pct:float
    sharpe_ratio:    float
    total_pnl:       float
    avg_weekly_pnl:  float
    best_week:       float
    worst_week:      float
    avg_r_multiple:  float
    avg_trades_week: float
    prop_pass:       bool  # Would pass prop firm challenge
    trades:          List[Trade] = field(default_factory=list)
    equity_curve:    List[float] = field(default_factory=list)


# ─────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────
class Backtester:

    SPREAD_PIPS    = 1.5    # XAUUSD typical spread (pips)
    SLIPPAGE_PIPS  = 0.5    # Execution slippage
    COMMISSION_LOT = 7.0    # Commission per round trip per lot ($7)

    def __init__(self, initial_equity: float = ACCOUNT_SIZE):
        self.initial_equity = initial_equity

    def fetch_data(self, period: str = "2y") -> pd.DataFrame:
        log.info(f"Fetching backtest data: {period}")
        ticker = yf.Ticker("GC=F")
        df = ticker.history(period=period, interval="15m")
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close", "volume"]].dropna()

    def run(self, df: Optional[pd.DataFrame] = None,
            use_ml: bool = False,
            show_progress: bool = True) -> BacktestResult:
        """
        Full backtest over historical data.
        """
        if df is None:
            df = self.fetch_data(period="2y")

        log.info(f"Building features on {len(df)} bars...")
        df_feat = compute_features(df.copy())
        df_feat["label"] = create_labels(df_feat, forward_bars=4,
                                          profit_target_atr=TP_ATR_MULT / 2,
                                          stop_loss_atr=SL_ATR_MULT)

        # If ML, load and apply model
        if use_ml:
            try:
                from ml_signal_generator import GoldMLSignalGenerator
                ml_gen = GoldMLSignalGenerator()
                ml_gen.load_model()
                feat_cols = get_feature_columns(df_feat)
                feat_cols = [f for f in feat_cols if f in df_feat.columns]
                X = df_feat[feat_cols].values
                X_scaled = ml_gen.scaler.transform(X)
                proba = ml_gen.model.predict_proba(X_scaled)
                df_feat["ml_buy_conf"]  = proba[:, 1]
                df_feat["ml_sell_conf"] = proba[:, 0]
                df_feat["ml_signal"]    = np.where(
                    (df_feat["ml_buy_conf"]  > 0.62) & (df_feat["bull_score"] >= 65), 1,
                    np.where(
                        (df_feat["ml_sell_conf"] > 0.62) & (df_feat["bear_score"] >= 65), -1, 0
                    )
                )
                signal_col = "ml_signal"
                log.info("Using ML signals for backtest")
            except Exception as e:
                log.warning(f"ML failed, falling back to rule-based: {e}")
                signal_col = "rule_signal"
                df_feat["rule_signal"] = self._generate_rule_signals(df_feat)
        else:
            df_feat["rule_signal"] = self._generate_rule_signals(df_feat)
            signal_col = "rule_signal"

        # ── Simulation ───────────────────────────────
        equity        = self.initial_equity
        trades        = []
        equity_curve  = [equity]
        daily_loss    = 0.0
        daily_trades  = 0
        last_day      = None
        peak_equity   = equity
        max_dd        = 0.0
        suspended     = False

        for i in range(len(df_feat)):
            bar = df_feat.iloc[i]
            bar_time = df_feat.index[i]

            # Daily reset
            if hasattr(bar_time, "date"):
                bar_date = bar_time.date()
            else:
                bar_date = None

            if bar_date != last_day:
                daily_loss   = 0.0
                daily_trades = 0
                last_day     = bar_date
                suspended    = False

            # Session filter
            if hasattr(bar_time, "hour"):
                hour = bar_time.hour
                in_london = 7 <= hour < 16
                in_ny     = 13 <= hour < 20
                if not (in_london or in_ny):
                    equity_curve.append(equity)
                    continue

            # Risk guards
            if suspended: continue
            if daily_trades >= MAX_TRADES_PER_DAY: continue

            # Get signal
            sig = int(bar.get(signal_col, 0))
            if sig == 0:
                equity_curve.append(equity)
                continue

            # Score filter
            score = float(bar.get("bull_score" if sig == 1 else "bear_score", 0))
            if score < 65: continue

            # Build trade
            atr      = float(bar.get("atr_14", 5.0))
            price    = float(bar["close"])
            spread   = self.SPREAD_PIPS * 0.01
            slip     = self.SLIPPAGE_PIPS * 0.01

            if sig == 1:  # BUY
                entry = price + spread / 2 + slip
                sl    = entry - atr * SL_ATR_MULT
                tp    = entry + atr * SL_ATR_MULT * MIN_RR
            else:         # SELL
                entry = price - spread / 2 - slip
                sl    = entry + atr * SL_ATR_MULT
                tp    = entry - atr * SL_ATR_MULT * MIN_RR

            # Validate R:R
            risk_pts  = abs(entry - sl)
            reward_pts= abs(tp - entry)
            if risk_pts <= 0 or reward_pts / risk_pts < MIN_RR:
                continue

            # Position sizing
            risk_usd = equity * RISK_PER_TRADE_PCT / 100.0
            sl_pips  = risk_pts / 0.01
            lot_size = risk_usd / max(sl_pips * 1.0, 1.0)
            lot_size = round(min(lot_size, 10.0), 2)

            # Commission
            commission = lot_size * self.COMMISSION_LOT

            # Simulate outcome using next bars
            pnl, outcome, exit_time = self._simulate_trade(
                df_feat, i, sig, entry, sl, tp, lot_size, commission
            )

            # Prop firm daily loss check
            if pnl < 0:
                daily_loss += pnl
                daily_loss_pct = abs(daily_loss / equity) * 100
                if daily_loss_pct > MAX_DAILY_LOSS_PCT:
                    suspended = True

            # Total DD check
            equity += pnl
            peak_equity = max(peak_equity, equity)
            dd = (peak_equity - equity) / peak_equity * 100
            if dd > max_dd: max_dd = dd

            equity_curve.append(equity)
            daily_trades += 1

            r_mult = pnl / risk_usd if risk_usd > 0 else 0

            trades.append(Trade(
                entry_time  = bar_time,
                exit_time   = exit_time,
                direction   = sig,
                entry_price = entry,
                sl_price    = sl,
                tp_price    = tp,
                lot_size    = lot_size,
                risk_usd    = risk_usd,
                pnl         = pnl,
                outcome     = outcome,
                r_multiple  = r_mult,
                score       = score,
                strategy    = signal_col,
            ))

        # ── Compute metrics ──────────────────────────
        return self._compute_metrics(trades, equity_curve, max_dd)

    def _generate_rule_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate rule-based signals (same logic as Pine Script)."""
        bull = (
            (df["micro_trend"] == 1) &
            (df.get("htf_bull", pd.Series(False, index=df.index)) == 1) &
            (df["rsi_14"] > 45) & (df["rsi_14"] < 68) &
            (df["adx"] > 20) & (df["di_spread"] > 0) &
            (df["vol_ratio"] > 1.2) & (df["bull_score"] >= 65)
        )
        bear = (
            (df["micro_trend"] == -1) &
            (df.get("htf_bear", pd.Series(False, index=df.index)) == 1) &
            (df["rsi_14"] < 55) & (df["rsi_14"] > 32) &
            (df["adx"] > 20) & (df["di_spread"] < 0) &
            (df["vol_ratio"] > 1.2) & (df["bear_score"] >= 65)
        )
        return pd.Series(np.where(bull, 1, np.where(bear, -1, 0)), index=df.index)

    def _simulate_trade(self, df, bar_idx, direction, entry, sl, tp,
                        lots, commission, max_bars_forward=40):
        """Simulate trade outcome by checking future price action."""
        pnl     = -commission
        outcome = "LOSS"
        exit_time = df.index[min(bar_idx + max_bars_forward, len(df) - 1)]

        for j in range(bar_idx + 1, min(bar_idx + max_bars_forward + 1, len(df))):
            f_high = df.iloc[j]["high"]
            f_low  = df.iloc[j]["low"]

            if direction == 1:  # LONG
                if f_low <= sl:
                    pnl += (sl - entry) * lots * 100  # loss
                    outcome = "LOSS"
                    exit_time = df.index[j]
                    break
                if f_high >= tp:
                    pnl += (tp - entry) * lots * 100  # win
                    outcome = "WIN"
                    exit_time = df.index[j]
                    break
            else:              # SHORT
                if f_high >= sl:
                    pnl += (entry - sl) * lots * 100
                    outcome = "LOSS"
                    exit_time = df.index[j]
                    break
                if f_low <= tp:
                    pnl += (entry - tp) * lots * 100
                    outcome = "WIN"
                    exit_time = df.index[j]
                    break
        else:
            # Timed out — close at last bar
            last_price = df.iloc[min(bar_idx + max_bars_forward, len(df)-1)]["close"]
            if direction == 1:
                pnl += (last_price - entry) * lots * 100
            else:
                pnl += (entry - last_price) * lots * 100
            outcome = "WIN" if pnl > 0 else "LOSS"

        if abs(pnl) < 1:
            outcome = "BE"

        return pnl, outcome, exit_time

    def _compute_metrics(self, trades: List[Trade], equity_curve: List[float],
                          max_dd: float) -> BacktestResult:
        if not trades:
            return BacktestResult(
                initial_equity=self.initial_equity,
                final_equity=self.initial_equity,
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, avg_win=0, avg_loss=0, profit_factor=0,
                max_drawdown=0, max_drawdown_pct=0, sharpe_ratio=0,
                total_pnl=0, avg_weekly_pnl=0, best_week=0, worst_week=0,
                avg_r_multiple=0, avg_trades_week=0, prop_pass=False
            )

        wins   = [t for t in trades if t.outcome == "WIN"]
        losses = [t for t in trades if t.outcome == "LOSS"]

        win_rate    = len(wins) / len(trades)
        avg_win     = np.mean([t.pnl for t in wins])    if wins   else 0
        avg_loss    = np.mean([t.pnl for t in losses])  if losses else 0
        total_pnl   = sum(t.pnl for t in trades)
        gross_profit= sum(t.pnl for t in wins)   if wins   else 0
        gross_loss  = abs(sum(t.pnl for t in losses)) if losses else 1

        profit_factor = gross_profit / max(gross_loss, 1.0)

        # Weekly P&L
        if trades:
            pnl_series = pd.Series(
                [t.pnl for t in trades],
                index=[t.entry_time for t in trades]
            )
            weekly = pnl_series.resample("W").sum()
            avg_weekly    = float(weekly.mean())
            best_week     = float(weekly.max())
            worst_week    = float(weekly.min())
            avg_trades_wk = len(trades) / max(len(weekly), 1)
        else:
            avg_weekly = best_week = worst_week = avg_trades_wk = 0

        # Sharpe ratio (annualized, risk-free = 0)
        pnl_arr = np.array([t.pnl for t in trades])
        sharpe  = (np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(252)) if np.std(pnl_arr) > 0 else 0

        avg_r = np.mean([t.r_multiple for t in trades])
        final_equity = equity_curve[-1] if equity_curve else self.initial_equity

        # Prop firm pass criteria
        prop_pass = (
            max_dd < MAX_TOTAL_DD_PCT and
            win_rate >= 0.50 and
            profit_factor >= 1.5 and
            avg_weekly >= WEEKLY_TARGET_LOW
        )

        result = BacktestResult(
            initial_equity   = self.initial_equity,
            final_equity     = final_equity,
            total_trades     = len(trades),
            winning_trades   = len(wins),
            losing_trades    = len(losses),
            win_rate         = win_rate,
            avg_win          = avg_win,
            avg_loss         = avg_loss,
            profit_factor    = profit_factor,
            max_drawdown     = self.initial_equity - min(equity_curve, default=self.initial_equity),
            max_drawdown_pct = max_dd,
            sharpe_ratio     = sharpe,
            total_pnl        = total_pnl,
            avg_weekly_pnl   = avg_weekly,
            best_week        = best_week,
            worst_week       = worst_week,
            avg_r_multiple   = avg_r,
            avg_trades_week  = avg_trades_wk,
            prop_pass        = prop_pass,
            trades           = trades,
            equity_curve     = equity_curve,
        )

        self._print_report(result)
        return result

    def _print_report(self, r: BacktestResult):
        print("\n" + "="*60)
        print("  GOLDMASTER PRO — BACKTEST REPORT")
        print("="*60)
        print(f"  Initial Equity:   ${r.initial_equity:>12,.2f}")
        print(f"  Final Equity:     ${r.final_equity:>12,.2f}")
        print(f"  Total P&L:        ${r.total_pnl:>12,.2f}")
        print(f"  Total Trades:     {r.total_trades:>12}")
        print(f"  Win Rate:         {r.win_rate:>12.1%}")
        print(f"  Avg Win:          ${r.avg_win:>12,.2f}")
        print(f"  Avg Loss:         ${r.avg_loss:>12,.2f}")
        print(f"  Profit Factor:    {r.profit_factor:>12.2f}")
        print(f"  Max Drawdown:     {r.max_drawdown_pct:>12.2f}%")
        print(f"  Sharpe Ratio:     {r.sharpe_ratio:>12.2f}")
        print(f"  Avg R Multiple:   {r.avg_r_multiple:>12.2f}R")
        print("-"*60)
        print(f"  Avg Weekly P&L:   ${r.avg_weekly_pnl:>12,.2f}")
        print(f"  Best Week:        ${r.best_week:>12,.2f}")
        print(f"  Worst Week:       ${r.worst_week:>12,.2f}")
        print(f"  Avg Trades/Week:  {r.avg_trades_week:>12.1f}")
        print("-"*60)
        target_low  = WEEKLY_TARGET_LOW
        target_high = WEEKLY_TARGET_HIGH
        target_met  = r.avg_weekly_pnl >= target_low
        print(f"  Weekly Target:    ${target_low:,.0f} - ${target_high:,.0f}")
        print(f"  Target Met:       {'✓ YES' if target_met else '✗ NO'} (${r.avg_weekly_pnl:,.0f}/wk avg)")
        print(f"  Prop Firm Pass:   {'✓ YES' if r.prop_pass else '✗ NO'}")
        print("="*60 + "\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GoldMaster Backtester")
    parser.add_argument("--period", default="2y", help="History period (e.g., 1y, 2y, 5y)")
    parser.add_argument("--ml",     action="store_true", help="Use ML signals")
    parser.add_argument("--equity", type=float, default=ACCOUNT_SIZE, help="Starting equity")
    args = parser.parse_args()

    bt = Backtester(initial_equity=args.equity)
    result = bt.run(use_ml=args.ml)
