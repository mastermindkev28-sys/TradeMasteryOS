"""
GoldMaster Pro — Feature Engineering
50+ technical and statistical features for ML signal generation.
"""
import numpy as np
import pandas as pd
from typing import Tuple
import warnings
warnings.filterwarnings("ignore")

try:
    import ta
    TA_LIB = True
except ImportError:
    TA_LIB = False


def compute_features(df: pd.DataFrame, htf_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Build comprehensive feature matrix from OHLCV data.

    Args:
        df: M15 OHLCV dataframe with columns [open, high, low, close, volume]
        htf_df: H4 OHLCV dataframe for higher timeframe context

    Returns:
        DataFrame with 50+ features (NaN rows dropped)
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # ─── Price-based features ───────────────────────
    df["returns"]        = df["close"].pct_change()
    df["log_returns"]    = np.log(df["close"] / df["close"].shift(1))
    df["hl_range"]       = df["high"] - df["low"]
    df["oc_range"]       = (df["close"] - df["open"]).abs()
    df["body_ratio"]     = df["oc_range"] / df["hl_range"].replace(0, np.nan)
    df["upper_wick"]     = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"]     = df[["open", "close"]].min(axis=1) - df["low"]
    df["is_bullish"]     = (df["close"] > df["open"]).astype(int)

    # ─── EMAs ───────────────────────────────────────
    for period in [9, 21, 50, 100, 200]:
        df[f"ema_{period}"]  = df["close"].ewm(span=period, adjust=False).mean()
        df[f"ema_dist_{period}"] = (df["close"] - df[f"ema_{period}"]) / df[f"ema_{period}"]

    # EMA crossovers
    df["ema9_21_cross"]  = np.where(df["ema_9"] > df["ema_21"], 1, -1)
    df["ema21_50_cross"] = np.where(df["ema_21"] > df["ema_50"], 1, -1)
    df["micro_trend"]    = np.where((df["ema_9"] > df["ema_21"]) & (df["ema_21"] > df["ema_50"]), 1,
                           np.where((df["ema_9"] < df["ema_21"]) & (df["ema_21"] < df["ema_50"]), -1, 0))

    # ─── ATR ────────────────────────────────────────
    df["atr_14"]         = _compute_atr(df, 14)
    df["atr_7"]          = _compute_atr(df, 7)
    df["atr_norm"]       = df["atr_14"] / df["close"]
    df["atr_ratio"]      = df["atr_7"] / df["atr_14"]  # volatility regime

    # ─── RSI ────────────────────────────────────────
    df["rsi_14"]         = _compute_rsi(df["close"], 14)
    df["rsi_7"]          = _compute_rsi(df["close"], 7)
    df["rsi_slope"]      = df["rsi_14"].diff(3)
    df["rsi_ob"]         = (df["rsi_14"] > 70).astype(int)
    df["rsi_os"]         = (df["rsi_14"] < 30).astype(int)

    # ─── MACD ───────────────────────────────────────
    ema12                = df["close"].ewm(span=12, adjust=False).mean()
    ema26                = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]           = ema12 - ema26
    df["macd_signal"]    = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]      = df["macd"] - df["macd_signal"]
    df["macd_cross"]     = np.where(df["macd"] > df["macd_signal"], 1, -1)
    df["macd_hist_slope"]= df["macd_hist"].diff(2)

    # ─── Bollinger Bands ────────────────────────────
    bb_mid               = df["close"].rolling(20).mean()
    bb_std               = df["close"].rolling(20).std()
    df["bb_upper"]       = bb_mid + 2 * bb_std
    df["bb_lower"]       = bb_mid - 2 * bb_std
    df["bb_width"]       = (df["bb_upper"] - df["bb_lower"]) / bb_mid
    df["bb_pct"]         = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    df["bb_squeeze"]     = (df["bb_width"] < df["bb_width"].rolling(50).mean() * 0.8).astype(int)

    # ─── ADX / DI ───────────────────────────────────
    adx_data             = _compute_adx(df, 14)
    df["adx"]            = adx_data["adx"]
    df["di_plus"]        = adx_data["di_plus"]
    df["di_minus"]       = adx_data["di_minus"]
    df["di_spread"]      = df["di_plus"] - df["di_minus"]
    df["adx_strong"]     = (df["adx"] > 25).astype(int)

    # ─── Stochastic ─────────────────────────────────
    df["stoch_k"]        = _compute_stoch(df, 14, 3)
    df["stoch_d"]        = df["stoch_k"].rolling(3).mean()
    df["stoch_cross"]    = np.where(df["stoch_k"] > df["stoch_d"], 1, -1)
    df["stoch_ob"]       = (df["stoch_k"] > 80).astype(int)
    df["stoch_os"]       = (df["stoch_k"] < 20).astype(int)

    # ─── Momentum ───────────────────────────────────
    for p in [5, 10, 20]:
        df[f"mom_{p}"]   = df["close"].diff(p)
        df[f"roc_{p}"]   = df["close"].pct_change(p) * 100

    # ─── Volume features ────────────────────────────
    df["vol_sma_20"]     = df["volume"].rolling(20).mean()
    df["vol_ratio"]      = df["volume"] / df["vol_sma_20"].replace(0, np.nan)
    df["vol_spike"]      = (df["vol_ratio"] > 2.0).astype(int)
    df["vol_trend"]      = df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean()
    df["obv"]            = (df["volume"] * df["is_bullish"].replace(0, -1)).cumsum()
    df["obv_slope"]      = df["obv"].diff(5)

    # ─── Pivot Points ───────────────────────────────
    # Rolling daily pivot using last day's H/L/C
    df["pivot"]          = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    df["r1"]             = 2 * df["pivot"] - df["low"].shift(1)
    df["s1"]             = 2 * df["pivot"] - df["high"].shift(1)
    df["dist_pivot"]     = (df["close"] - df["pivot"]) / df["atr_14"]
    df["dist_r1"]        = (df["close"] - df["r1"]) / df["atr_14"]
    df["dist_s1"]        = (df["close"] - df["s1"]) / df["atr_14"]

    # ─── Session features ───────────────────────────
    if df.index.dtype == "datetime64[ns, UTC]" or hasattr(df.index, "hour"):
        df["hour"]           = df.index.hour
        df["in_london"]      = ((df["hour"] >= 7) & (df["hour"] < 16)).astype(int)
        df["in_ny"]          = ((df["hour"] >= 13) & (df["hour"] < 20)).astype(int)
        df["in_london_open"] = ((df["hour"] >= 7) & (df["hour"] < 10)).astype(int)
        df["in_ny_open"]     = ((df["hour"] >= 13) & (df["hour"] < 15)).astype(int)
        df["day_of_week"]    = df.index.dayofweek
        df["is_monday"]      = (df["day_of_week"] == 0).astype(int)
        df["is_friday"]      = (df["day_of_week"] == 4).astype(int)

    # ─── Higher timeframe context (H4) ──────────────
    if htf_df is not None:
        htf_df = htf_df.copy()
        htf_df.columns = [c.lower() for c in htf_df.columns]
        htf_df["ema_50"]  = htf_df["close"].ewm(span=50,  adjust=False).mean()
        htf_df["ema_200"] = htf_df["close"].ewm(span=200, adjust=False).mean()
        htf_df["rsi_14"]  = _compute_rsi(htf_df["close"], 14)
        htf_df["htf_bull"] = ((htf_df["close"] > htf_df["ema_200"]) &
                               (htf_df["ema_50"] > htf_df["ema_200"])).astype(int)
        htf_df["htf_bear"] = ((htf_df["close"] < htf_df["ema_200"]) &
                               (htf_df["ema_50"] < htf_df["ema_200"])).astype(int)
        htf_df["htf_rsi"]  = htf_df["rsi_14"]

        # Merge H4 features onto M15 via forward-fill
        htf_features = htf_df[["htf_bull", "htf_bear", "htf_rsi"]].copy()
        htf_features.index = pd.to_datetime(htf_features.index)
        df = df.join(htf_features.resample("15T").ffill(), how="left")
        df[["htf_bull", "htf_bear", "htf_rsi"]] = df[["htf_bull", "htf_bear", "htf_rsi"]].ffill()

    # ─── Composite signal score (rule-based) ────────
    df["bull_score"] = _compute_bull_score(df)
    df["bear_score"] = _compute_bear_score(df)

    # ─── Statistical features ───────────────────────
    df["returns_std_20"] = df["log_returns"].rolling(20).std()
    df["returns_mean_20"]= df["log_returns"].rolling(20).mean()
    df["skewness_20"]    = df["log_returns"].rolling(20).skew()
    df["high_low_std"]   = df["hl_range"].rolling(20).std()

    # Drop NaN rows created by indicators
    df.dropna(inplace=True)
    return df


def _compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high_low   = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close  = (df["low"]  - df["close"].shift(1)).abs()
    tr         = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta  = series.diff()
    gain   = delta.where(delta > 0, 0.0).ewm(span=period, adjust=False).mean()
    loss   = (-delta.where(delta < 0, 0.0)).ewm(span=period, adjust=False).mean()
    rs     = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_adx(df: pd.DataFrame, period: int) -> pd.DataFrame:
    high       = df["high"]
    low        = df["low"]
    close      = df["close"]

    up_move    = high.diff()
    down_move  = -low.diff()

    plus_dm    = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm   = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr        = _compute_atr(df, period)
    plus_dm_s  = pd.Series(plus_dm, index=df.index).ewm(span=period, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(span=period, adjust=False).mean()

    di_plus    = 100 * plus_dm_s  / atr.replace(0, np.nan)
    di_minus   = 100 * minus_dm_s / atr.replace(0, np.nan)
    dx         = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx        = dx.ewm(span=period, adjust=False).mean()

    return pd.DataFrame({"adx": adx, "di_plus": di_plus, "di_minus": di_minus}, index=df.index)


def _compute_stoch(df: pd.DataFrame, period: int, smooth: int) -> pd.Series:
    low_min  = df["low"].rolling(period).min()
    high_max = df["high"].rolling(period).max()
    k        = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    return k.rolling(smooth).mean()


def _compute_bull_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0, index=df.index)
    if "htf_bull" in df.columns: score += df["htf_bull"] * 15
    score += (df["micro_trend"] == 1).astype(int) * 10
    score += (df["ema_dist_200"] > 0).astype(int) * 5
    score += (df["mom_10"] > 0).astype(int) * 8
    score += (df["roc_5"]  > 0).astype(int) * 7
    score += ((df["rsi_14"] > 50) & (df["rsi_14"] < 70)).astype(int) * 10
    score += (df["vol_ratio"] > 1.3).astype(int) * 10
    score += (df["vol_ratio"] > 2.0).astype(int) * 5
    score += df["is_bullish"] * 8
    score += (df["adx"] > 20).astype(int) * 8
    score += (df["di_spread"] > 0).astype(int) * 7
    return score.clip(0, 100)


def _compute_bear_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0, index=df.index)
    if "htf_bear" in df.columns: score += df["htf_bear"] * 15
    score += (df["micro_trend"] == -1).astype(int) * 10
    score += (df["ema_dist_200"] < 0).astype(int) * 5
    score += (df["mom_10"] < 0).astype(int) * 8
    score += (df["roc_5"]  < 0).astype(int) * 7
    score += ((df["rsi_14"] < 50) & (df["rsi_14"] > 30)).astype(int) * 10
    score += (df["vol_ratio"] > 1.3).astype(int) * 10
    score += (df["vol_ratio"] > 2.0).astype(int) * 5
    score += (1 - df["is_bullish"]) * 8
    score += (df["adx"] > 20).astype(int) * 8
    score += (df["di_spread"] < 0).astype(int) * 7
    return score.clip(0, 100)


def create_labels(df: pd.DataFrame, forward_bars: int = 4,
                  profit_target_atr: float = 2.0,
                  stop_loss_atr: float = 1.5) -> pd.Series:
    """
    Generate ML labels: 1=BUY, -1=SELL, 0=NO TRADE
    Uses forward-looking price action with ATR-based targets.
    """
    labels = pd.Series(0, index=df.index)
    atr    = df["atr_14"]

    for i in range(len(df) - forward_bars):
        entry  = df["close"].iloc[i]
        future = df["close"].iloc[i+1 : i+forward_bars+1]
        future_high = df["high"].iloc[i+1 : i+forward_bars+1].max()
        future_low  = df["low"].iloc[i+1  : i+forward_bars+1].min()

        tp_buy  = entry + atr.iloc[i] * profit_target_atr
        sl_buy  = entry - atr.iloc[i] * stop_loss_atr
        tp_sell = entry - atr.iloc[i] * profit_target_atr
        sl_sell = entry + atr.iloc[i] * stop_loss_atr

        # Check which hits first
        if future_high >= tp_buy and future_low > sl_buy:
            labels.iloc[i] = 1    # BUY wins
        elif future_low <= tp_sell and future_high < sl_sell:
            labels.iloc[i] = -1   # SELL wins
        # else: 0 = no clear winner (skip)

    return labels


def get_feature_columns(df: pd.DataFrame) -> list:
    """Return list of feature columns (exclude price/label columns)."""
    exclude = {"open", "high", "low", "close", "volume", "label",
               "bb_upper", "bb_lower", "pivot", "r1", "s1",
               "ema_9", "ema_21", "ema_50", "ema_100", "ema_200",
               "obv"}
    return [c for c in df.columns if c not in exclude]
