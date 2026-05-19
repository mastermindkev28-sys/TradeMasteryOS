# GoldMaster Pro — XAUUSD Trading Bot System

**Target:** $1,000–$1,500 net profit per week on a $100K account  
**Risk profile:** Prop firm safe — 3% daily loss limit, 6% max drawdown  
**Instruments:** XAUUSD (Gold) only  
**Platforms:** TradingView + MetaTrader 4 (MT4)

---

## Architecture

```
TradingView Alert          Python ML Engine
  (Pine Script)  ────────► (XGBoost + RF)
       │                         │
       ▼                         ▼
  Webhook Endpoint ◄──── Signal Scoring
  /api/tradingview/webhook       │
       │                         ▼
       └──────────► Python Bridge Server
                    (Flask webhook_bridge.py)
                          │
                          ▼
                  ┌───────────────┐
                  │  Risk Manager  │ ◄── Prop firm guards
                  └───────┬───────┘
                          │
                    signals/orders.json
                          │
                          ▼
                  ┌───────────────┐
                  │  MT4 Bridge   │ ◄── GoldMaster_Bridge.mq4
                  │  Expert Adv.  │
                  └───────┬───────┘
                          │
                          ▼
                   OrderSend() → Broker
```

---

## Strategies

### 1. London Session Breakout (Primary)
- **When:** 07:00–10:00 UTC (London open first 3 hours)
- **Setup:** Range formed 04:00–07:00 UTC broken on high volume
- **Stop:** 50% of range below breakout point + 0.5 ATR buffer
- **Target:** 1.5× range extension above breakout level
- **Filter:** Volume > 1.3× 20-bar average, signal score ≥ 55

### 2. Trend Pullback — EMA Bounce
- **When:** London + NY sessions
- **Setup:** H4 macro trend confirmed (EMA50 > EMA200), price pulls back to EMA21/50 zone and bounces
- **Stop:** Below EMA50 + 1.5 ATR
- **Target:** 2:1 R minimum, 3.5 ATR extension
- **Filter:** RSI 40–65, ADX > 20, micro-trend aligned, signal score ≥ 65

### 3. NY Session Momentum
- **When:** 13:00–15:00 UTC (NY open first 2 hours)
- **Setup:** Strong momentum at NY open aligned with H4 trend, above/below VWAP
- **Stop:** ATR-based (1.5×)
- **Target:** 2:1 R minimum
- **Filter:** Volume spike > 1.5×, ADX > 20, DI aligned

### 4. VWAP Mean Reversion (Disabled by default)
- **When:** Any session
- **Setup:** Price deviates 2+ ATR from VWAP, RSI extreme, reversal candle
- **Best for:** Range-bound, low-ADX conditions

---

## Risk Management

| Parameter | Value | Prop Firm Limit |
|-----------|-------|-----------------|
| Risk per trade | 0.75% | — |
| Daily loss limit | 3.0% | 5% (FTMO) |
| Max drawdown | 6.0% | 10% (FTMO) |
| Min R:R | 2:1 | — |
| Max trades/day | 3 | — |
| Trailing stop | 1.0R activation | — |
| Partial close | 50% at 1.5R | — |

**On a $100K account:**
- Risk per trade = $750
- Max daily loss = $3,000
- Max total drawdown = $6,000
- Single winning trade (2R) = $1,500

---

## Weekly P&L Projection

Assumptions: 3 trades/day × 3 days active/week = 9 trades/week  
Win rate: 55–60% (conservative), Avg R on wins: 2.0R

| Scenario | Weekly P&L |
|----------|-----------|
| Conservative (55% WR) | ~$900–$1,200 |
| Base case (60% WR) | ~$1,200–$1,500 |
| Strong week (65% WR) | ~$1,500–$2,200 |

---

## File Structure

```
trading-bot/
├── tradingview/
│   ├── GoldMaster_Strategy.pine    # Full strategy with backtest, signals, prop guard table
│   └── GoldMaster_Alerts.pine      # Lightweight alert-only indicator for webhooks
├── mt4/
│   ├── GoldMasterEA.mq4            # Full Expert Advisor (standalone auto-trader)
│   └── GoldMaster_Bridge.mq4       # File-bridge EA (reads Python signals from disk)
└── python/
    ├── config.py                   # All configuration
    ├── feature_engineering.py      # 50+ technical features + labels
    ├── ml_signal_generator.py      # XGBoost+RF ensemble, training, live predictions
    ├── risk_manager.py             # Prop firm risk controls, position sizing
    ├── webhook_bridge.py           # Flask server: TV webhook → MT4 bridge
    ├── backtest.py                 # Realistic backtesting engine
    └── requirements.txt
```

---

## Quick Setup

### Option A: TradingView Only (Simplest)
1. Open TradingView, add `GoldMaster_Strategy.pine` on XAUUSD M15
2. Backtest to verify performance on your broker's data
3. Create alerts for "GoldMaster LONG" and "GoldMaster SHORT"
4. Trade manually based on alerts OR set up webhook

### Option B: Full Automated System
```bash
# 1. Install dependencies
cd trading-bot/python
pip install -r requirements.txt

# 2. Train ML model (uses 2 years of Yahoo Finance data)
python ml_signal_generator.py --train

# 3. Start webhook bridge server
python webhook_bridge.py

# 4. Load MT4 EA
# Copy GoldMasterEA.mq4 to MT4/MQL4/Experts/
# Compile with F7 in MetaEditor
# Attach to XAUUSD M15 chart
# Enable AutoTrading

# 5. Configure TradingView alert webhook:
# URL: http://your-server-ip:5000/api/tradingview/webhook
```

### Environment Variables
```env
PYTHON_BRIDGE_URL=http://localhost:5000
WEBHOOK_SECRET=your-secret-key-min-32-chars
ACCOUNT_SIZE=100000
RISK_PER_TRADE_PCT=0.75
MAX_DAILY_LOSS_PCT=3.0
MAX_TOTAL_DD_PCT=6.0
PROP_FIRM_MODE=true
```

---

## ML Model Details

**Algorithm:** Ensemble of XGBoost + Random Forest + Gradient Boosting  
**Calibration:** Sigmoid probability calibration for reliable confidence scores  
**Features (50+):**
- EMAs (9, 21, 50, 100, 200) + distance from price
- ATR (7, 14) + normalized volatility ratio
- RSI (7, 14) + slope + OB/OS flags
- MACD + signal + histogram + cross
- Bollinger Bands + width + squeeze
- ADX + DI+/DI- + spread
- Stochastic K/D + cross
- Momentum (5, 10, 20 bars) + ROC
- Volume ratio + OBV + trend
- Pivot P/R1/S1 distances
- Session flags (London/NY/Asian)
- H4 HTF trend context
- Composite rule-based bull/bear scores

**Training:**
- 2 years M15 XAUUSD data (Yahoo Finance GC=F)
- 75% train / 25% test (time-series split)
- Labels: forward ATR-based win/loss (4-bar forward window)
- Retrain automatically every 7 days

**Signal filter:** Only execute if ML confidence ≥ 62% AND rule score ≥ 65/100

---

## Prop Firm Compliance

The system is designed to pass FTMO, MyForexFunds, and similar prop firm challenges:

- ✅ Daily loss hard stop at 3% (well below 5% limit)
- ✅ Total drawdown guard at 6% (below 10% limit)
- ✅ Max 3 trades/day (controlled exposure)
- ✅ No trading during dead zones (20:00–02:00 UTC)
- ✅ Minimum 2:1 R:R enforced on every trade
- ✅ Breakeven stop-loss moves at 1R
- ✅ Partial close at 1.5R (lock in profits)
- ✅ Trailing stop after 1R activation
- ✅ No news trading (high-impact events filtered)

---

## Dashboard

Access the bot control panel at `/bot` in the TradeMasteryOS web app.

Features:
- Live bot status (active/suspended)
- Today P&L, week P&L, equity
- Risk meter (daily DD %, total DD %)
- Weekly progress toward $1,000–$1,500 target
- MT4 + ML model connection status
- Recent signal log with action, price, SL, TP, confidence
- Setup guide
