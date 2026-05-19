"""
GoldMaster Pro — ML Signal Generator
XGBoost + Random Forest ensemble for gold trade signal classification.
Target: 60%+ win rate with strict risk filters.
"""
import os
import json
import pickle
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
warnings.filterwarnings("ignore")

from config import (
    ML_MODEL_PATH, ML_SCALER_PATH, ML_CONFIDENCE_MIN,
    FEATURE_WINDOW, TRAIN_SPLIT, YFINANCE_SYMBOL, MIN_SIGNAL_SCORE,
    LOG_FILE, LOG_LEVEL, ACCOUNT_SIZE, RISK_PER_TRADE_PCT,
    ATR_PERIOD, SL_ATR_MULT, TP_ATR_MULT, MIN_RR
)
from feature_engineering import compute_features, create_labels, get_feature_columns

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
Path("models").mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("GoldMaster.ML")

# ─────────────────────────────────────────────
# IMPORTS WITH FALLBACKS
# ─────────────────────────────────────────────
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    log.warning("XGBoost not available, falling back to Random Forest only")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
    from sklearn.preprocessing import RobustScaler
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.calibration import CalibratedClassifierCV
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("scikit-learn not available. Install: pip install scikit-learn")


class GoldMLSignalGenerator:
    """
    Ensemble ML model for XAUUSD signal generation.
    Combines XGBoost + Random Forest with confidence calibration.
    """

    def __init__(self):
        self.model  = None
        self.scaler = None
        self.features: list = []
        self.is_trained = False
        self.model_date = None
        self.performance = {}

        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn required. Run: pip install -r requirements.txt")

    # ─────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────
    def fetch_data(self, period: str = "2y", interval: str = "15m") -> pd.DataFrame:
        """Fetch XAUUSD data from Yahoo Finance."""
        log.info(f"Fetching {YFINANCE_SYMBOL} data: {period} / {interval}")
        try:
            ticker = yf.Ticker(YFINANCE_SYMBOL)
            df = ticker.history(period=period, interval=interval)
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            log.info(f"Fetched {len(df)} bars")
            return df
        except Exception as e:
            log.error(f"Data fetch error: {e}")
            raise

    def fetch_htf_data(self, period: str = "2y") -> pd.DataFrame:
        """Fetch H4 data for higher timeframe context."""
        try:
            ticker = yf.Ticker(YFINANCE_SYMBOL)
            df = ticker.history(period=period, interval="1h")
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            # Resample to H4
            df_h4 = df.resample("4H").agg({
                "open": "first", "high": "max",
                "low": "min",   "close": "last", "volume": "sum"
            }).dropna()
            log.info(f"Fetched H4 context: {len(df_h4)} bars")
            return df_h4
        except Exception as e:
            log.warning(f"H4 fetch failed: {e}. Proceeding without HTF context.")
            return None

    # ─────────────────────────────────────────────
    # TRAINING
    # ─────────────────────────────────────────────
    def train(self, save: bool = True) -> dict:
        """Full training pipeline: fetch → features → labels → train → evaluate."""
        log.info("=== Starting GoldMaster ML Training ===")

        # Fetch data
        df_m15 = self.fetch_data(period="2y", interval="15m")
        df_h4  = self.fetch_htf_data(period="2y")

        # Feature engineering
        log.info("Engineering features...")
        df_feat = compute_features(df_m15, df_h4)

        # Generate labels
        log.info("Creating labels...")
        df_feat["label"] = create_labels(df_feat, forward_bars=4,
                                          profit_target_atr=TP_ATR_MULT / 2,
                                          stop_loss_atr=SL_ATR_MULT)

        # Only keep tradeable signals (filter out 0-label noise)
        df_trade = df_feat[df_feat["label"] != 0].copy()
        log.info(f"Signal distribution:\n{df_trade['label'].value_counts()}")

        # Feature selection
        self.features = get_feature_columns(df_feat)
        self.features = [f for f in self.features if f in df_feat.columns]

        X = df_trade[self.features].values
        y = df_trade["label"].map({1: 1, -1: 0}).values  # 1=BUY, 0=SELL

        # Train/test split (time-series aware)
        split_idx = int(len(X) * TRAIN_SPLIT)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        log.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

        # Scale
        self.scaler = RobustScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s  = self.scaler.transform(X_test)

        # ── Build ensemble ────────────────────────────
        rf = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=20,
            max_features="sqrt",
            class_weight="balanced",
            n_jobs=-1,
            random_state=42
        )

        estimators = [("rf", rf)]

        if XGBOOST_AVAILABLE:
            xgb = XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=1,
                use_label_encoder=False,
                eval_metric="logloss",
                random_state=42,
                verbosity=0
            )
            estimators.append(("xgb", xgb))

        gb = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        estimators.append(("gb", gb))

        # Voting ensemble
        ensemble = VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)

        # Calibrate probabilities for reliable confidence scores
        self.model = CalibratedClassifierCV(ensemble, method="sigmoid", cv=3)
        self.model.fit(X_train_s, y_train)

        # ── Evaluate ──────────────────────────────────
        y_pred  = self.model.predict(X_test_s)
        y_proba = self.model.predict_proba(X_test_s)[:, 1]

        # Apply confidence threshold
        y_pred_filtered = np.where(
            np.maximum(y_proba, 1 - y_proba) >= ML_CONFIDENCE_MIN,
            y_pred, -1
        )
        mask = y_pred_filtered != -1

        accuracy = (y_pred[mask] == y_test[mask]).mean() if mask.sum() > 0 else 0
        coverage = mask.mean()

        self.performance = {
            "accuracy":     float(accuracy),
            "coverage":     float(coverage),
            "n_train":      int(len(X_train)),
            "n_test":       int(len(X_test)),
            "n_features":   len(self.features),
            "trained_at":   datetime.utcnow().isoformat(),
        }

        log.info(f"Model accuracy: {accuracy:.1%} (coverage: {coverage:.1%})")
        log.info(f"\n{classification_report(y_test[mask], y_pred[mask])}")

        self.is_trained = True
        self.model_date = datetime.utcnow()

        if save:
            self._save_model()

        return self.performance

    # ─────────────────────────────────────────────
    # PREDICTION
    # ─────────────────────────────────────────────
    def predict(self, df: pd.DataFrame, htf_df: pd.DataFrame = None) -> dict:
        """
        Generate signal for the latest bar.
        Returns dict with action, confidence, and metadata.
        """
        if not self.is_trained:
            self.load_model()

        # Feature engineering on latest data
        df_feat = compute_features(df.copy(), htf_df)

        if len(df_feat) == 0:
            return {"action": "HOLD", "confidence": 0.0, "reason": "No data"}

        # Get latest bar features
        latest = df_feat.iloc[-1]
        feature_vals = []
        for f in self.features:
            if f in df_feat.columns:
                feature_vals.append(latest[f])
            else:
                feature_vals.append(0.0)

        X = np.array(feature_vals).reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        proba = self.model.predict_proba(X_scaled)[0]
        pred  = self.model.predict(X_scaled)[0]

        # proba[1] = P(BUY), proba[0] = P(SELL)
        buy_conf  = float(proba[1])
        sell_conf = float(proba[0])
        confidence = max(buy_conf, sell_conf)

        # Rule-based score gate
        bull_score = float(latest.get("bull_score", 0))
        bear_score = float(latest.get("bear_score", 0))

        # Final decision: ML + rule-based consensus
        if confidence < ML_CONFIDENCE_MIN:
            return {
                "action":     "HOLD",
                "confidence": confidence,
                "reason":     f"ML confidence {confidence:.1%} below threshold {ML_CONFIDENCE_MIN:.1%}",
                "bull_score": bull_score,
                "bear_score": bear_score,
            }

        if pred == 1 and buy_conf >= ML_CONFIDENCE_MIN and bull_score >= MIN_SIGNAL_SCORE:
            action = "BUY"
            score  = bull_score
        elif pred == 0 and sell_conf >= ML_CONFIDENCE_MIN and bear_score >= MIN_SIGNAL_SCORE:
            action = "SELL"
            score  = bear_score
        else:
            return {
                "action":     "HOLD",
                "confidence": confidence,
                "reason":     "Rule score too low despite ML confidence",
                "bull_score": bull_score,
                "bear_score": bear_score,
            }

        # Calculate risk levels
        atr   = float(latest.get("atr_14", 0))
        price = float(df["close"].iloc[-1])
        if action == "BUY":
            sl    = round(price - atr * SL_ATR_MULT, 2)
            tp1   = round(price + atr * SL_ATR_MULT * MIN_RR, 2)
            tp2   = round(price + atr * TP_ATR_MULT, 2)
        else:
            sl    = round(price + atr * SL_ATR_MULT, 2)
            tp1   = round(price - atr * SL_ATR_MULT * MIN_RR, 2)
            tp2   = round(price - atr * TP_ATR_MULT, 2)

        # Lot size
        risk_usd = ACCOUNT_SIZE * RISK_PER_TRADE_PCT / 100
        sl_pips  = abs(price - sl) / 0.01
        lot_size = round(risk_usd / max(sl_pips, 1), 2)
        lot_size = min(lot_size, 5.0)  # Max 5 lots hard cap

        return {
            "action":      action,
            "confidence":  round(confidence, 4),
            "score":       round(score, 1),
            "price":       price,
            "sl":          sl,
            "tp1":         tp1,
            "tp2":         tp2,
            "atr":         round(atr, 2),
            "lot_size":    lot_size,
            "risk_usd":    round(risk_usd, 2),
            "rr_ratio":    round(abs(tp1 - price) / abs(price - sl), 2),
            "timestamp":   datetime.utcnow().isoformat(),
            "bull_score":  bull_score,
            "bear_score":  bear_score,
        }

    # ─────────────────────────────────────────────
    # LIVE SIGNAL LOOP
    # ─────────────────────────────────────────────
    def get_live_signal(self) -> dict:
        """Fetch latest data and generate live signal."""
        log.info("Fetching live data for signal generation...")
        try:
            df_m15 = self.fetch_data(period="60d", interval="15m")
            df_h4  = self.fetch_htf_data(period="60d")
            signal = self.predict(df_m15, df_h4)
            log.info(f"Signal: {signal['action']} | Conf: {signal.get('confidence', 0):.1%} | Score: {signal.get('score', 0)}")
            return signal
        except Exception as e:
            log.error(f"Live signal error: {e}")
            return {"action": "HOLD", "confidence": 0.0, "reason": str(e)}

    # ─────────────────────────────────────────────
    # SAVE / LOAD MODEL
    # ─────────────────────────────────────────────
    def _save_model(self):
        Path("models").mkdir(exist_ok=True)
        with open(ML_MODEL_PATH,  "wb") as f: pickle.dump(self.model,  f)
        with open(ML_SCALER_PATH, "wb") as f: pickle.dump(self.scaler, f)
        meta = {
            "features":    self.features,
            "performance": self.performance,
            "trained_at":  datetime.utcnow().isoformat(),
        }
        with open("models/meta.json", "w") as f: json.dump(meta, f, indent=2)
        log.info(f"Model saved to {ML_MODEL_PATH}")

    def load_model(self):
        if not Path(ML_MODEL_PATH).exists():
            log.info("No saved model found. Training now...")
            self.train()
            return
        with open(ML_MODEL_PATH,  "rb") as f: self.model  = pickle.load(f)
        with open(ML_SCALER_PATH, "rb") as f: self.scaler = pickle.load(f)
        with open("models/meta.json") as f:
            meta = json.load(f)
            self.features     = meta["features"]
            self.performance  = meta.get("performance", {})
        self.is_trained = True
        log.info(f"Model loaded. Accuracy: {self.performance.get('accuracy', 0):.1%}")

    def needs_retraining(self) -> bool:
        if not Path(ML_MODEL_PATH).exists(): return True
        mtime = datetime.fromtimestamp(Path(ML_MODEL_PATH).stat().st_mtime)
        return (datetime.utcnow() - mtime).days >= 7


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GoldMaster ML Signal Generator")
    parser.add_argument("--train",  action="store_true", help="Train/retrain the model")
    parser.add_argument("--signal", action="store_true", help="Generate live signal")
    parser.add_argument("--status", action="store_true", help="Show model status")
    args = parser.parse_args()

    bot = GoldMLSignalGenerator()

    if args.train:
        perf = bot.train(save=True)
        print(f"\n✓ Model trained. Accuracy: {perf['accuracy']:.1%} | Coverage: {perf['coverage']:.1%}")

    elif args.signal:
        if bot.needs_retraining():
            print("Model needs retraining. Running train first...")
            bot.train(save=True)
        signal = bot.get_live_signal()
        print(f"\n{'='*50}")
        print(f"SIGNAL: {signal['action']}")
        if signal['action'] != 'HOLD':
            print(f"Price:      {signal.get('price', 'N/A')}")
            print(f"SL:         {signal.get('sl', 'N/A')}")
            print(f"TP1:        {signal.get('tp1', 'N/A')}")
            print(f"TP2:        {signal.get('tp2', 'N/A')}")
            print(f"Lot Size:   {signal.get('lot_size', 'N/A')}")
            print(f"Risk:       ${signal.get('risk_usd', 'N/A')}")
            print(f"R:R:        {signal.get('rr_ratio', 'N/A')}")
            print(f"Confidence: {signal.get('confidence', 0):.1%}")
            print(f"Score:      {signal.get('score', 0)}/100")
        print('='*50)

    elif args.status:
        if Path(ML_MODEL_PATH).exists():
            bot.load_model()
            print(f"Model Status: LOADED")
            print(f"Accuracy:     {bot.performance.get('accuracy', 0):.1%}")
            print(f"Coverage:     {bot.performance.get('coverage', 0):.1%}")
            print(f"Features:     {len(bot.features)}")
            print(f"Needs retrain: {bot.needs_retraining()}")
        else:
            print("No model found. Run --train first.")

    else:
        parser.print_help()
