"""
Standalone position sizing utilities (used by backtester and live engine).
"""

import math
from typing import Optional


def fixed_fractional_contracts(
    account_balance: float,
    risk_pct: float,
    atr: float,
    atr_stop_mult: float,
    point_value: float,
    max_contracts: int = 10,
) -> int:
    """Risk exactly risk_pct% of balance on the trade."""
    risk_dollars = account_balance * risk_pct
    risk_per_contract = atr * atr_stop_mult * point_value
    if risk_per_contract <= 0:
        return 0
    contracts = math.floor(risk_dollars / risk_per_contract)
    return max(0, min(contracts, max_contracts))


def kelly_contracts(
    account_balance: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float,
    point_value: float,
    atr: float,
    atr_stop_mult: float,
    max_contracts: int = 10,
) -> int:
    """Fractional Kelly sizing."""
    if avg_loss == 0 or win_rate <= 0:
        return 0
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    kelly_f = max(0.0, (b * p - q) / b) * kelly_fraction
    risk_dollars = account_balance * kelly_f
    risk_per_contract = atr * atr_stop_mult * point_value
    if risk_per_contract <= 0:
        return 0
    contracts = math.floor(risk_dollars / risk_per_contract)
    return max(0, min(contracts, max_contracts))


def volatility_target_contracts(
    account_balance: float,
    target_volatility: float,     # annualised vol target e.g. 0.15
    daily_atr: float,
    point_value: float,
    trading_days: int = 252,
    max_contracts: int = 10,
) -> int:
    """
    Size so that the strategy's dollar vol ≈ target_volatility * balance.
    Useful for portfolio-level risk budgeting across multiple strategies.
    """
    daily_vol_target = account_balance * target_volatility / math.sqrt(trading_days)
    contract_daily_vol = daily_atr * point_value
    if contract_daily_vol <= 0:
        return 0
    contracts = math.floor(daily_vol_target / contract_daily_vol)
    return max(0, min(contracts, max_contracts))
