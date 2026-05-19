# Futures Mean Reversion Bot — Implementation Guide
### From Evaluation to Funded: Step-by-Step

---

## Table of Contents
1. [Strategy Logic](#1-strategy-logic)
2. [Quick Start](#2-quick-start)
3. [Backtest Results Interpretation](#3-backtest-results-interpretation)
4. [Walk-Forward & Monte Carlo](#4-walk-forward--monte-carlo)
5. [Prop Firm Risk Settings](#5-prop-firm-risk-settings)
6. [Live Deployment on VPS](#6-live-deployment-on-vps)
7. [Broker Setup (Tradovate / TopstepX)](#7-broker-setup)
8. [Telegram Alerts Setup](#8-telegram-alerts-setup)
9. [Passing the Evaluation](#9-passing-the-evaluation-prop-firm-checklist)
10. [Overfitting Warnings](#10-overfitting--regime-change-warnings)
11. [Intraday vs Daily Variants](#11-intraday-vs-daily-variants)
12. [FAQ](#12-faq)

---

## 1. Strategy Logic

### IBS Mean Reversion (primary)

```
rolling_mean  = SMA(high − low, 25)           # avg bar range over 25 days
lower_band    = highest(high, 10) − 2.5 × rolling_mean
IBS           = (close − low) / (high − low)  # 0 = closed at low, 1 = at high
```

**Entry (Long Only):**
- `close < lower_band`   — price is stretched below recent range anchor
- `IBS < 0.30`           — bar closed near its low (bearish bar = oversold)
- `close > 300-bar SMA`  — long-term bullish regime filter

**Exit (any of):**
- `close > prev_bar.high`   — price recovered above yesterday's high
- `close < 300-bar SMA`     — trend reversal; abandon the trade
- `bars_held ≥ 20`          — hard time stop (prevents zombie positions)

**Why it works:** CME futures (especially /ES, /NQ) exhibit strong short-term mean reversion during bull-market regimes. When price gaps or sells hard intraday and closes near the low (low IBS), the market tends to recover within 1-5 sessions. The lower band ensures we only enter genuine dislocations, not normal selling.

### Dual Thrust (intraday alternative, `config.py → active_strategy = "dual_thrust"`)

```
Range = max(HH − LC,  HC − LL)   # prior N days
Upper = Open + K_long  × Range
Lower = Open − K_short × Range
```

Long when price breaks Upper; Short when it breaks Lower. Flatten at close.

---

## 2. Quick Start

### Install
```bash
cd bots/futures_mean_reversion
pip install -r requirements.txt
```

### Run a full backtest (MES, 2015–2024)
```bash
python main.py backtest --wf --mc
```

Outputs saved to `outputs/`:
- `backtest_results.png`  — equity curve, drawdown, trade markers, metrics table
- `walk_forward.png`      — IS vs OOS Sharpe by window
- `monte_carlo.png`       — equity path distribution, ruin probability
- `trade_log.csv`         — every trade with entry/exit/P&L
- `walk_forward.json`     — walk-forward summary data

### Check today's signal
```bash
python main.py signal
```

### Start paper trading
```bash
python main.py live    # paper_trade=True by default in config.py
```

---

## 3. Backtest Results Interpretation

| Metric | Minimum acceptable | Strong |
|--------|-------------------|--------|
| Sharpe Ratio | ≥ 0.8 | ≥ 1.5 |
| Profit Factor | ≥ 1.3 | ≥ 1.8 |
| Win Rate | ≥ 45% | ≥ 55% |
| Max Drawdown | ≤ 20% | ≤ 10% |
| CAGR | ≥ 10% | ≥ 25% |
| Calmar Ratio | ≥ 0.5 | ≥ 1.5 |

**Red flags in your backtest:**
- Win rate > 80%: likely curve-fit, check for look-ahead bias
- < 30 trades total: statistically meaningless, not enough data
- Max DD occurs in 2020 or 2022: expected — check recovery speed
- Sharpe > 3.0 on daily data: almost certainly overfit

---

## 4. Walk-Forward & Monte Carlo

### Walk-Forward Analysis
The optimizer searches `ibs_entry_threshold` and `band_multiplier` over 5 windows.
Each window optimises in-sample (IS) then validates out-of-sample (OOS).

**WF Efficiency = OOS Sharpe / IS Sharpe**
- ≥ 0.70 → Strategy is robust, parameters generalise
- 0.50–0.70 → Acceptable, monitor live carefully
- < 0.50 → Likely overfit — do NOT trade live

### Monte Carlo
5,000 bootstrapped trade sequences test whether results depend on lucky ordering.

**Probability of ruin (account down 10%):**
- < 5% → Safe to trade at configured size
- 5–15% → Reduce risk_pct_per_trade by 25%
- > 15% → Do not trade live

---

## 5. Prop Firm Risk Settings

### TopstepX 50K Evaluation
```python
# config.py settings
cfg.backtest.initial_capital = 50_000
cfg.risk.daily_loss_limit_pct = 0.02      # $1,000/day max loss
cfg.risk.trailing_drawdown_pct = 0.04     # $2,000 trailing DD limit
cfg.risk.risk_pct_per_trade = 0.005       # 0.5% per trade = ~$250
cfg.risk.max_contracts = 2                # conservative during eval
cfg.risk.max_profit_single_day_pct = 0.40 # consistency rule
```

**Profit target:** $3,000 (6% of 50K)
**Minimum trading days:** 10

### Apex 50K Evaluation
```python
cfg.risk.daily_loss_limit_pct = 0.02      # $1,000
cfg.risk.trailing_drawdown_pct = 0.026    # $1,300 (static, not trailing)
```

### Lucid 25K Evaluation
```python
cfg.backtest.initial_capital = 25_000
cfg.risk.daily_loss_limit_pct = 0.02      # $500
cfg.risk.trailing_drawdown_pct = 0.04     # $1,000
```

### General Prop Rules Implemented
1. **ATR stop:** Every trade has a hard stop at `1.5 × ATR` from entry
2. **Daily kill-switch:** Bot stops trading the moment daily loss limit is hit
3. **Trailing DD kill-switch:** Full shutdown if trailing DD breached
4. **Consistency:** Warning logged when daily P&L exceeds 40% of profit target
5. **No over-leverage:** Position sizing never exceeds 50% of buying power margin
6. **No HFT consistency violation:** All trades hold overnight (daily bars), so no sub-5-second holds

---

## 6. Live Deployment on VPS

### Recommended VPS Specs
- **Provider:** Vultr, DigitalOcean, or AWS EC2 (`t3.small` or `t3.medium`)
- **Location:** Chicago (CH3/CHI) for lowest CME latency
- **OS:** Ubuntu 22.04 LTS
- **RAM:** 2 GB minimum
- **Storage:** 20 GB SSD

### VPS Setup
```bash
# 1. SSH into your VPS
ssh root@YOUR_VPS_IP

# 2. Install Python
sudo apt update && sudo apt install -y python3.11 python3-pip git screen

# 3. Clone your repo
git clone https://github.com/YOUR_REPO/TradeMasteryOS.git
cd TradeMasteryOS/bots/futures_mean_reversion

# 4. Install dependencies
pip3 install -r requirements.txt

# 5. Set broker credentials (use environment variables, NOT in code)
export TRADOVATE_USER="your_username"
export TRADOVATE_PASS="your_password"
export TRADOVATE_APP_ID="your_app_id"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# 6. Run in a screen session (persists after SSH disconnect)
screen -S tradebot
python3 main.py live
# Ctrl+A, D to detach; "screen -r tradebot" to reattach

# 7. Optional: run as systemd service for auto-restart
# (see systemd template below)
```

### Systemd Service Template
```ini
# /etc/systemd/system/tradebot.service
[Unit]
Description=TradeMastery Futures Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/TradeMasteryOS/bots/futures_mean_reversion
ExecStart=/usr/bin/python3 main.py live
Restart=always
RestartSec=30
Environment="TRADOVATE_USER=YOUR_USER"
Environment="TRADOVATE_PASS=YOUR_PASS"
StandardOutput=append:/var/log/tradebot.log
StandardError=append:/var/log/tradebot.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tradebot
sudo systemctl start tradebot
sudo journalctl -u tradebot -f   # tail logs
```

---

## 7. Broker Setup

### Tradovate / TopstepX
1. Create a Tradovate demo account at `demo.tradovate.com`
2. Go to **Account → API Access** → create an app, get `App ID`
3. In `config.py`:
   ```python
   cfg.live.broker = "tradovate"
   cfg.live.paper_trade = True             # demo mode
   cfg.live.tradovate_base_url = "https://demo.tradovateapi.com/v1"
   cfg.live.tradovate_user = "YOUR_USER"
   cfg.live.tradovate_password = "YOUR_PASS"
   cfg.live.tradovate_app_id = "YOUR_APP_ID"
   ```
4. Switch to live: change base URL to `https://live.tradovateapi.com/v1` and `paper_trade = False`

### Contract Symbols (Tradovate format)
| Bot Symbol | Tradovate Symbol | Description |
|------------|-----------------|-------------|
| MES | MESH5 (current front month) | Micro E-mini S&P 500 |
| MNQ | MNQH5 | Micro E-mini Nasdaq |
| MCL | MCLH5 | Micro Crude Oil |

Update the symbol monthly when the contract rolls (3rd Friday of Mar/Jun/Sep/Dec).

### Rithmic
Set `cfg.live.broker = "rithmic"` — requires `rithmic-api` package and a dedicated gateway.
Contact your prop firm; TopstepX, Apex, and Earn2Trade all support Rithmic.

---

## 8. Telegram Alerts Setup

1. Message `@BotFather` on Telegram → `/newbot` → copy the **bot token**
2. Message `@userinfobot` → copy your **chat ID**
3. Update `config.py`:
   ```python
   cfg.telegram.enabled = True
   cfg.telegram.bot_token = "YOUR_TOKEN"
   cfg.telegram.chat_id = "YOUR_CHAT_ID"
   ```

You will receive alerts for:
- Every entry (symbol, direction, contracts, entry price, stop)
- Every exit (P&L per trade)
- Daily loss limit breached (with trading halt notice)
- Trailing drawdown breach (emergency shutdown)
- Bot errors and exceptions
- Daily status report (balance, DD, daily P&L)

---

## 9. Passing the Evaluation — Prop Firm Checklist

### Phase 1: Evaluation (e.g. TopstepX 50K)
- [ ] Paper trade the strategy for **4 weeks** minimum — confirm signals match your backtest
- [ ] Verify daily P&L never exceeds 40% of profit target (consistency rule)
- [ ] Hit profit target **over ≥10 trading days** (not 1-2 big days)
- [ ] Never breach daily loss limit — the bot enforces this, but verify manually
- [ ] Do not change strategy parameters mid-evaluation (counts as circumvention)
- [ ] Keep detailed trade notes — prop firms audit suspicious equity curves

### Phase 2: Funded Account
- [ ] Reduce `risk_pct_per_trade` from 0.5% to 0.25% initially
- [ ] Increase `max_contracts` gradually: start at 1, scale to 3-5 over 30 days
- [ ] Monitor WF efficiency monthly — if it drops below 0.4, pause and review
- [ ] Withdraw profits regularly (reduces trailing DD risk)
- [ ] Re-run walk-forward quarterly with new data

### Red Lines (automatic disqualification)
- Position held after market close (if `no_overnight_hold=True` required)
- Drawdown exceeding firm limit (bot enforces, but confirm manually)
- API key sharing or running multiple instances under same account

---

## 10. Overfitting & Regime Change Warnings

### Signs You Are Overfit
- Backtest win rate > 75% on daily bars (real win rate will be 50-60%)
- Walk-forward efficiency < 0.5
- Strategy only works on one specific symbol
- Parameters were optimised more than 3 times on the same dataset
- Monte Carlo P(ruin) > 15%

### Regime Changes to Watch
| Period | What Happened | Impact on IBS |
|--------|---------------|---------------|
| 2020 Mar | COVID crash | Stops hit; recovery rapid afterward |
| 2022 | Fed rate hike cycle | Trend strategy kills IBS longs |
| 2023-24 | AI bull run | IBS works well in trending-up-with-pullbacks |
| VIX > 30 | High volatility | Widen ATR stop multiplier to 2.0+ |

**Regime filter (not yet in code, add if WF degrades):**
```python
# Avoid trading when VIX > 30 (fear/uncertainty spikes)
# proxy: 20-day realised vol of /ES > 25%
if realised_vol_20d > 0.25:
    return Signal("flat", "High vol regime — skip")
```

### How to Avoid Overfitting
1. Only optimise **1-2 parameters** at a time
2. Keep out-of-sample data ≥ 30% of total
3. Use walk-forward with **≥ 5 windows**
4. Test on multiple symbols (/NQ, /CL, /GC) — a robust strategy should work on all
5. Run Monte Carlo — results should be stable across 5,000 paths

---

## 11. Intraday vs Daily Variants

### Daily Bars (default)
- Signal fires after the daily close
- Enter at next open (add `open` fill in backtest for realism)
- Best for funded accounts with no overnight hold restriction lifted
- Commissions negligible; overnight gap risk is the main cost

### Hourly Bars
```python
cfg.contract.data_timeframe = "1H"
cfg.ibs.trend_filter_sma = 200   # 200 hours ≈ 25 trading days
cfg.ibs.sma_period = 20          # shorter rolling mean
cfg.ibs.max_hold_bars = 8        # 8 hours max
```

### Dual Thrust Intraday (15-min)
```python
cfg.active_strategy = "dual_thrust"
cfg.contract.data_timeframe = "15Min"
cfg.risk.no_overnight_hold = True  # flatten before 4pm
```

---

## 12. FAQ

**Q: Why only long trades?**
IBS mean reversion is asymmetric — downside gaps recover faster than upside gaps fade in equity futures. Shorting with IBS has historically lower win rate and worse risk-adjusted returns on /ES.

**Q: Why 300-SMA and not 200-SMA?**
The 300-day SMA reduces false signals during bear markets. In 2022, the 200-SMA generated entries that continued to lose; the 300-SMA kept us out of most of 2022. Feel free to test both.

**Q: What if the prop firm requires min 5 trades/month?**
Lower `ibs_entry_threshold` to 0.35 and `band_multiplier` to 2.0. This generates more signals but slightly lower quality. Rerun WF to validate.

**Q: Can I run this on /NQ instead of /ES?**
Yes — change `cfg.contract.symbol = "MNQ"` and `cfg.contract.point_value = 2.0` (MNQ = $2/point). NQ is more volatile so consider raising `atr_stop_multiplier` to 1.75.

**Q: The strategy has no trades for months. Is that normal?**
Yes. IBS mean reversion is low-frequency (typically 2-5 trades/month on daily bars). This is a feature — each trade is high-conviction. Resist the urge to force more signals.

**Q: What data is required for the backtest?**
Yahoo Finance (`yfinance`) provides free daily OHLCV for `ES=F` going back to ~2000. For tick or minute data, use Databento (~$50/month), Rithmic Historical, or NinjaTrader's free backadjusted data.
