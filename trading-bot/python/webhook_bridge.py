"""
GoldMaster Pro — Webhook Bridge Server
Receives TradingView alerts and forwards signals to MT4 via file bridge.
Also provides REST API for the Next.js dashboard.

Endpoints:
  POST /api/tradingview/webhook  — receive TV alerts
  POST /api/signal               — manual signal injection
  GET  /api/status               — bot + risk status
  GET  /api/trades               — recent trade history
  GET  /api/signal/latest        — latest generated signal
  POST /api/mt4/status           — MT4 EA heartbeat
"""
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, abort
from flask_cors import CORS

from config import (
    WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_SECRET,
    MT4_ORDERS_FILE, MT4_STATUS_FILE, WEBHOOK_SIGNAL_FILE,
    LOG_FILE, LOG_LEVEL
)
from risk_manager import RiskManager
from ml_signal_generator import GoldMLSignalGenerator

# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
Path("signals").mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("GoldMaster.Bridge")

app  = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://trademasteryos.com"])

risk = RiskManager()
ml   = GoldMLSignalGenerator()

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify TradingView/custom webhook HMAC-SHA256 signature."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def require_api_key(f):
    """Decorator: require X-API-Key header for admin endpoints."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if key != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# SIGNAL PROCESSING
# ─────────────────────────────────────────────
def process_signal(signal: dict) -> dict:
    """Validate, enrich, and route a trading signal."""
    log.info(f"Processing signal: {signal.get('action')} | Price: {signal.get('price')}")

    # Risk gate
    valid, reason = risk.validate_signal(signal)
    if not valid:
        log.warning(f"Signal rejected: {reason}")
        return {"status": "rejected", "reason": reason}

    # Write signal file for MT4 bridge
    order = {
        "id":         int(time.time()),
        "action":     signal["action"],
        "symbol":     signal.get("symbol", "XAUUSD"),
        "price":      signal.get("price", 0),
        "sl":         signal.get("sl", 0),
        "tp1":        signal.get("tp1", 0),
        "tp2":        signal.get("tp2", 0),
        "lot_size":   signal.get("lot_size", 0.01),
        "confidence": signal.get("confidence", 0),
        "score":      signal.get("score", 0),
        "atr":        signal.get("atr", 0),
        "source":     signal.get("source", "webhook"),
        "timestamp":  datetime.utcnow().isoformat(),
        "status":     "PENDING",
    }

    # Write for MT4 to consume
    with open(MT4_ORDERS_FILE, "w") as f:
        json.dump(order, f, indent=2)

    # Save as latest signal
    with open(WEBHOOK_SIGNAL_FILE, "w") as f:
        json.dump({**signal, **order}, f, indent=2)

    log.info(f"Signal queued for MT4: {order['action']} {order['symbol']} @ {order['price']}")
    return {"status": "queued", "order_id": order["id"], "signal": order}


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "GoldMaster Bridge", "time": datetime.utcnow().isoformat()})


@app.route("/api/tradingview/webhook", methods=["POST"])
def tradingview_webhook():
    """
    Receives TradingView alert webhooks.
    Configure TV alert webhook URL to: http://your-server:5000/api/tradingview/webhook
    Alert message format (JSON):
      {"action":"BUY","symbol":"XAUUSD","price":{{close}},"atr":{{atr14}},"score":65}
    """
    # Optional signature verification
    sig = request.headers.get("X-Signature", "")
    if sig and not verify_webhook_signature(request.data, sig):
        log.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "Empty payload"}), 400

        action = payload.get("action", "").upper()
        if action not in ("BUY", "SELL"):
            return jsonify({"error": f"Unknown action: {action}"}), 400

        # Enrich signal with risk levels if not provided
        price = float(payload.get("price", 0))
        atr   = float(payload.get("atr", 0))

        if price > 0 and atr > 0:
            from config import SL_ATR_MULT, TP_ATR_MULT, MIN_RR
            if action == "BUY":
                payload.setdefault("sl",  round(price - atr * SL_ATR_MULT, 2))
                payload.setdefault("tp1", round(price + atr * SL_ATR_MULT * MIN_RR, 2))
                payload.setdefault("tp2", round(price + atr * TP_ATR_MULT, 2))
            else:
                payload.setdefault("sl",  round(price + atr * SL_ATR_MULT, 2))
                payload.setdefault("tp1", round(price - atr * SL_ATR_MULT * MIN_RR, 2))
                payload.setdefault("tp2", round(price - atr * TP_ATR_MULT, 2))

            sl_pips = abs(price - payload["sl"]) / 0.01
            sizing  = risk.calculate_lot_size(sl_pips)
            payload.setdefault("lot_size", sizing["lot_size"])
            payload.setdefault("risk_usd", sizing["risk_usd"])
            payload.setdefault("rr_ratio", round(abs(payload["tp1"] - price) / abs(payload["sl"] - price), 2))

        payload["source"] = "tradingview"
        result = process_signal(payload)
        return jsonify(result), 200

    except Exception as e:
        log.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/signal", methods=["POST"])
@require_api_key
def manual_signal():
    """Manual signal injection (from ML engine or dashboard)."""
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "Empty payload"}), 400
    payload["source"] = payload.get("source", "manual")
    result = process_signal(payload)
    return jsonify(result)


@app.route("/api/signal/latest", methods=["GET"])
def latest_signal():
    """Return the latest signal."""
    if Path(WEBHOOK_SIGNAL_FILE).exists():
        with open(WEBHOOK_SIGNAL_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({"action": "HOLD", "message": "No signal yet"})


@app.route("/api/signal/ml", methods=["GET"])
def ml_signal():
    """Generate fresh ML signal on demand."""
    try:
        signal = ml.get_live_signal()
        if signal["action"] != "HOLD":
            signal["source"] = "ml"
            result = process_signal(signal)
            return jsonify({"signal": signal, "result": result})
        return jsonify({"signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def bot_status():
    """Return bot + risk manager status for dashboard."""
    status = risk.get_status()

    # Add MT4 status if available
    if Path(MT4_STATUS_FILE).exists():
        with open(MT4_STATUS_FILE) as f:
            try:
                status["mt4"] = json.load(f)
            except:
                status["mt4"] = {"status": "unknown"}
    else:
        status["mt4"] = {"status": "not connected"}

    # Add ML model status
    status["ml"] = {
        "trained":        ml.is_trained,
        "accuracy":       ml.performance.get("accuracy", 0),
        "needs_retrain":  ml.needs_retraining(),
    }

    return jsonify(status)


@app.route("/api/mt4/status", methods=["POST"])
def mt4_heartbeat():
    """Receive heartbeat + status from MT4 EA."""
    payload = request.get_json()
    if payload:
        payload["last_heartbeat"] = datetime.utcnow().isoformat()
        with open(MT4_STATUS_FILE, "w") as f:
            json.dump(payload, f, indent=2)

        # Update risk state with MT4 equity
        equity = payload.get("equity")
        if equity:
            risk.state._state["current_equity"] = float(equity)
            risk.state.save()

    return jsonify({"ok": True})


@app.route("/api/mt4/order/ack", methods=["POST"])
def mt4_order_ack():
    """MT4 EA acknowledges order execution."""
    payload = request.get_json()
    if payload:
        log.info(f"MT4 order ack: {payload}")
        # Mark order as acknowledged
        if Path(MT4_ORDERS_FILE).exists():
            with open(MT4_ORDERS_FILE) as f:
                order = json.load(f)
            order["status"] = payload.get("status", "EXECUTED")
            order["ticket"]  = payload.get("ticket")
            with open(MT4_ORDERS_FILE, "w") as f:
                json.dump(order, f, indent=2)
    return jsonify({"ok": True})


@app.route("/api/trades", methods=["GET"])
def trade_history():
    """Return recent trade history from CSV log."""
    import csv
    from config import TRADE_LOG_FILE
    trades = []
    if Path(TRADE_LOG_FILE).exists():
        with open(TRADE_LOG_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    # Return last 50 trades, newest first
    return jsonify({"trades": list(reversed(trades[-50:]))})


@app.route("/api/performance", methods=["GET"])
def performance():
    """Return performance summary for the dashboard."""
    status = risk.get_status()
    return jsonify({
        "equity":           status["equity"],
        "today_pnl":        status["today_pnl"],
        "week_pnl":         status["week_pnl"],
        "weekly_target":    [1000, 1500],
        "weekly_progress":  status["weekly_progress"],
        "win_rate":         status["win_rate"],
        "daily_dd_pct":     status["daily_dd_pct"],
        "total_dd_pct":     status["total_dd_pct"],
        "today_trades":     status["today_trades"],
        "total_trades":     status["total_trades"],
        "can_trade":        status["can_trade"],
    })


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"Starting GoldMaster Bridge on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    log.info(f"TradingView webhook URL: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/api/tradingview/webhook")

    # Pre-load ML model
    try:
        if ml.needs_retraining():
            log.info("Training ML model on startup...")
            ml.train(save=True)
        else:
            ml.load_model()
        log.info(f"ML model ready. Accuracy: {ml.performance.get('accuracy', 0):.1%}")
    except Exception as e:
        log.warning(f"ML model not loaded: {e}. Will use rule-based signals only.")

    app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, debug=False, threaded=True)
