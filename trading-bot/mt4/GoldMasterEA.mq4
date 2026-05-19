//+------------------------------------------------------------------+
//|  GoldMaster Pro EA — MT4 Expert Advisor                          |
//|  XAUUSD Gold Trading System | Prop Firm Edition                  |
//|  Target: $1,000-$1,500 net profit/week on $100K account          |
//|  Max Daily Loss: 3% | Max Drawdown: 6% | Min R:R 2:1             |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property version   "2.00"
#property strict

#include <stdlib.mqh>

// ─────────────────────────────────────────────
// INPUT PARAMETERS
// ─────────────────────────────────────────────

// Risk Management
extern double RiskPerTrade_Pct    = 0.75;   // Risk % per trade (0.75% on $100K = $750)
extern double MaxDailyLoss_Pct    = 3.0;    // Max daily drawdown %
extern double MaxTotalDD_Pct      = 6.0;    // Max total drawdown %
extern int    MaxTradesPerDay     = 3;      // Max trades per day
extern double MinRR               = 2.0;    // Minimum Risk:Reward ratio
extern bool   PropFirmMode        = true;   // Enable strict prop firm risk controls
extern bool   UseTrailingStop     = true;   // Enable trailing stops
extern double TrailActivate_R     = 1.0;    // Activate trail after X * R profit
extern double TrailStep_Pips      = 15;     // Trail step in pips

// ATR Settings
extern int    ATR_Period          = 14;     // ATR period
extern double SL_ATR_Mult         = 1.5;    // Stop loss = ATR * multiplier
extern double TP_ATR_Mult         = 3.5;    // Take profit = ATR * multiplier
extern double TP2_ATR_Mult        = 5.0;    // TP2 for partial close

// EMA Settings
extern int    EMA_Fast            = 9;
extern int    EMA_Mid             = 21;
extern int    EMA_Slow            = 50;
extern int    EMA_Trend           = 200;

// Strategy Selection
extern bool   UseStrategy_LondonBO    = true;  // London Session Breakout
extern bool   UseStrategy_TrendPull   = true;  // Trend + EMA Pullback
extern bool   UseStrategy_NYMomentum  = true;  // NY Session Momentum
extern bool   UseStrategy_VWAPRev     = false; // VWAP Mean Reversion

// Entry Filters
extern int    MinSignalScore      = 65;     // Minimum composite signal score
extern int    ADX_Period          = 14;
extern int    ADX_MinValue        = 20;
extern int    RSI_Period          = 14;
extern int    RSI_OB              = 70;
extern int    RSI_OS              = 30;
extern double VolFilter_Mult      = 1.3;    // Min volume vs 20-bar average

// London Breakout Settings
extern int    LB_RangeStartHour   = 4;     // UTC hour range starts (4 = 04:00 UTC)
extern int    LB_RangeEndHour     = 7;     // UTC hour range ends   (7 = London open)
extern double LB_TargetMult       = 1.5;   // Target = range * multiplier

// Session Hours (UTC)
extern int    London_Open_UTC     = 7;
extern int    London_Close_UTC    = 16;
extern int    NY_Open_UTC         = 13;
extern int    NY_Close_UTC        = 20;

// Partial Close
extern bool   UsePartialClose     = true;
extern double PartialClose_Pct    = 50.0;  // Close 50% at TP1
extern double PartialClose_R      = 1.5;   // Close partial at 1.5R profit

// Display
extern bool   ShowDashboard       = true;
extern bool   ShowSignalArrows    = true;
extern string EA_Comment          = "GoldMaster Pro";

// Magic Number
extern int    MagicNumber         = 20250519;

// ─────────────────────────────────────────────
// GLOBAL VARIABLES
// ─────────────────────────────────────────────
double AccountStartEquity;
double TodayStartEquity;
int    TodayTradeCount;
double TodayPnL;
datetime LastTradeTime;
datetime TodayDate;
bool   TradingSuspended;
string SuspendReason;

// London Range
double LondonRangeHigh;
double LondonRangeLow;
bool   LondonRangeSet;
datetime LondonRangeDate;

// Signal state
int    LastSignalBar;

// ─────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────
int OnInit()
{
    AccountStartEquity = AccountEquity();
    TodayStartEquity   = AccountEquity();
    TodayTradeCount    = 0;
    TodayPnL           = 0.0;
    LastTradeTime      = 0;
    TodayDate          = iTime(NULL, PERIOD_D1, 0);
    TradingSuspended   = false;
    SuspendReason      = "";
    LondonRangeHigh    = 0;
    LondonRangeLow     = 0;
    LondonRangeSet     = false;
    LastSignalBar      = -1;

    Print("GoldMaster Pro EA initialized. Account equity: $", AccountEquity());
    Print("Prop Firm Mode: ", PropFirmMode ? "ENABLED" : "DISABLED");
    Print("Risk per trade: ", RiskPerTrade_Pct, "% = $", AccountEquity() * RiskPerTrade_Pct / 100);

    return(INIT_SUCCEEDED);
}

// ─────────────────────────────────────────────
// DEINITIALIZATION
// ─────────────────────────────────────────────
void OnDeinit(const int reason)
{
    Comment("");
    Print("GoldMaster Pro EA stopped. Reason: ", reason);
}

// ─────────────────────────────────────────────
// MAIN TICK FUNCTION
// ─────────────────────────────────────────────
void OnTick()
{
    // Only run logic once per bar close (M15 or current chart TF)
    static datetime lastBarTime = 0;
    datetime currentBarTime = iTime(NULL, 0, 0);
    bool isNewBar = (currentBarTime != lastBarTime);

    // Always update trailing stops and partial close on every tick
    ManageOpenTrades();

    if (!isNewBar) {
        if (ShowDashboard) DrawDashboard();
        return;
    }
    lastBarTime = currentBarTime;

    // ── Daily reset ──────────────────────────────
    datetime newDay = iTime(NULL, PERIOD_D1, 0);
    if (newDay != TodayDate) {
        TodayDate        = newDay;
        TodayStartEquity = AccountEquity();
        TodayTradeCount  = 0;
        TodayPnL         = 0.0;
        TradingSuspended = false;
        SuspendReason    = "";
        LondonRangeHigh  = 0;
        LondonRangeLow   = 0;
        LondonRangeSet   = false;
        Print("New trading day. Equity reset: $", AccountEquity());
    }

    // ── Update London Range ──────────────────────
    UpdateLondonRange();

    // ── Risk checks ─────────────────────────────
    if (!CanTrade()) return;

    // ── Skip if already in trade ─────────────────
    if (CountOpenOrders() > 0) return;

    // ── Generate signals ─────────────────────────
    int signal = GetCompositeSignal();
    if (signal == 0) return;

    // ── Execute trade ────────────────────────────
    ExecuteTrade(signal);
}

// ─────────────────────────────────────────────
// CAN TRADE — ALL RISK GUARDS
// ─────────────────────────────────────────────
bool CanTrade()
{
    // Check suspension flag
    if (TradingSuspended) return false;

    // Weekend
    if (DayOfWeek() == 0 || DayOfWeek() == 6) return false;

    // Dead zone (UTC 20:00 - 02:00)
    int hourUTC = TimeHour(TimeGMT());
    if (hourUTC >= 20 || hourUTC < 2) return false;

    // Session check — only trade London + NY
    bool inLondon = (hourUTC >= London_Open_UTC && hourUTC < London_Close_UTC);
    bool inNY     = (hourUTC >= NY_Open_UTC     && hourUTC < NY_Close_UTC);
    if (!inLondon && !inNY) return false;

    if (!PropFirmMode) return true;

    // Prop firm: daily loss limit
    double dailyPnL = AccountEquity() - TodayStartEquity;
    if (dailyPnL < -(AccountEquity() * MaxDailyLoss_Pct / 100)) {
        TradingSuspended = true;
        SuspendReason    = "Daily loss limit hit";
        Alert("GoldMaster: Daily loss limit reached. Trading suspended.");
        return false;
    }

    // Prop firm: total drawdown
    double totalDD = (AccountEquity() - AccountStartEquity) / AccountStartEquity * 100;
    if (totalDD < -MaxTotalDD_Pct) {
        TradingSuspended = true;
        SuspendReason    = "Max drawdown breached";
        Alert("GoldMaster: MAX DRAWDOWN BREACHED. All trading suspended.");
        return false;
    }

    // Daily trade count
    if (TodayTradeCount >= MaxTradesPerDay) {
        return false;
    }

    return true;
}

// ─────────────────────────────────────────────
// SIGNAL SCORING (0-100) + COMPOSITE SIGNAL
// Returns: 1=BUY, -1=SELL, 0=NO SIGNAL
// ─────────────────────────────────────────────
int GetCompositeSignal()
{
    // Prevent multiple signals on same bar
    if (Bars == LastSignalBar) return 0;

    double atr    = iATR(NULL, 0, ATR_Period, 1);
    double ema9   = iMA(NULL, 0, EMA_Fast,  0, MODE_EMA, PRICE_CLOSE, 1);
    double ema21  = iMA(NULL, 0, EMA_Mid,   0, MODE_EMA, PRICE_CLOSE, 1);
    double ema50  = iMA(NULL, 0, EMA_Slow,  0, MODE_EMA, PRICE_CLOSE, 1);
    double ema200 = iMA(NULL, 0, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE, 1);
    double rsi    = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
    double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN,     1);
    double diPlus = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
    double diMinus= iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

    // H4 trend context
    double ema200_h4 = iMA(NULL, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
    double ema50_h4  = iMA(NULL, PERIOD_H4, 50,  0, MODE_EMA, PRICE_CLOSE, 1);

    double closeBar  = iClose(NULL, 0, 1);
    double openBar   = iOpen(NULL, 0, 1);

    // Volume
    double vol     = iVolume(NULL, 0, 1);
    double volSMA  = 0;
    for (int i = 1; i <= 20; i++) volSMA += iVolume(NULL, 0, i);
    volSMA /= 20.0;
    double volRatio = (volSMA > 0) ? vol / volSMA : 1.0;

    // Momentum
    double mom12  = closeBar - iClose(NULL, 0, 13);
    double roc5   = (iClose(NULL, 0, 6) > 0) ? (closeBar - iClose(NULL, 0, 6)) / iClose(NULL, 0, 6) * 100 : 0;

    // Trend flags
    bool htf_bull = (closeBar > ema200_h4 && ema50_h4 > ema200_h4);
    bool htf_bear = (closeBar < ema200_h4 && ema50_h4 < ema200_h4);
    bool micro_bull = (ema9 > ema21 && ema21 > ema50);
    bool micro_bear = (ema9 < ema21 && ema21 < ema50);

    // ── BULL SCORE ───────────────────────────────
    int bullScore = 0;
    if (htf_bull)  bullScore += 15;
    if (micro_bull) bullScore += 10;
    if (closeBar > ema200) bullScore += 5;
    if (mom12 > 0) bullScore += 8;
    if (roc5  > 0) bullScore += 7;
    if (rsi > 50 && rsi < 70) bullScore += 10;
    if (volRatio > VolFilter_Mult) bullScore += 10;
    if (volRatio > 2.0) bullScore += 5;
    if (closeBar > openBar) bullScore += 8;
    if (adx > ADX_MinValue) bullScore += 8;
    if (diPlus > diMinus)   bullScore += 7;

    // ── BEAR SCORE ───────────────────────────────
    int bearScore = 0;
    if (htf_bear)  bearScore += 15;
    if (micro_bear) bearScore += 10;
    if (closeBar < ema200) bearScore += 5;
    if (mom12 < 0) bearScore += 8;
    if (roc5  < 0) bearScore += 7;
    if (rsi < 50 && rsi > 30) bearScore += 10;
    if (volRatio > VolFilter_Mult) bearScore += 10;
    if (volRatio > 2.0) bearScore += 5;
    if (closeBar < openBar) bearScore += 8;
    if (adx > ADX_MinValue) bearScore += 8;
    if (diMinus > diPlus)   bearScore += 7;

    int hourUTC = TimeHour(TimeGMT());
    bool inLondonOpen = (hourUTC >= London_Open_UTC && hourUTC < (London_Open_UTC + 3));
    bool inNYOpen     = (hourUTC >= NY_Open_UTC     && hourUTC < (NY_Open_UTC + 2));

    // ── STRATEGY 1: LONDON BREAKOUT ──────────────
    if (UseStrategy_LondonBO && LondonRangeSet && inLondonOpen) {
        if (closeBar > LondonRangeHigh && volRatio > VolFilter_Mult) {
            if (bullScore >= MinSignalScore - 10) {
                LastSignalBar = Bars;
                return 1;
            }
        }
        if (closeBar < LondonRangeLow && volRatio > VolFilter_Mult) {
            if (bearScore >= MinSignalScore - 10) {
                LastSignalBar = Bars;
                return -1;
            }
        }
    }

    // ── STRATEGY 2: TREND PULLBACK ───────────────
    if (UseStrategy_TrendPull) {
        // Bull: H4 bullish, price pulling to EMA21/50 zone, RSI not OB
        bool bullPullZone = (closeBar >= ema21 * 0.9985 && closeBar <= ema50 * 1.002);
        bool bearPullZone = (closeBar <= ema21 * 1.0015 && closeBar >= ema50 * 0.998);

        if (htf_bull && micro_bull && bullPullZone && rsi > RSI_OS && rsi < RSI_OB && bullScore >= MinSignalScore) {
            LastSignalBar = Bars;
            return 1;
        }
        if (htf_bear && micro_bear && bearPullZone && rsi < RSI_OB && rsi > RSI_OS && bearScore >= MinSignalScore) {
            LastSignalBar = Bars;
            return -1;
        }
    }

    // ── STRATEGY 3: NY SESSION MOMENTUM ──────────
    if (UseStrategy_NYMomentum && inNYOpen) {
        double vwap = iCustom(NULL, 0, "VWAP", 0, 1);  // Requires VWAP indicator installed
        if (htf_bull && mom12 > 0 && volRatio > 1.5 && adx > ADX_MinValue && diPlus > diMinus && bullScore >= MinSignalScore) {
            LastSignalBar = Bars;
            return 1;
        }
        if (htf_bear && mom12 < 0 && volRatio > 1.5 && adx > ADX_MinValue && diMinus > diPlus && bearScore >= MinSignalScore) {
            LastSignalBar = Bars;
            return -1;
        }
    }

    return 0;
}

// ─────────────────────────────────────────────
// EXECUTE TRADE
// ─────────────────────────────────────────────
void ExecuteTrade(int direction)
{
    double atr    = iATR(NULL, 0, ATR_Period, 1);
    double ask    = MarketInfo(Symbol(), MODE_ASK);
    double bid    = MarketInfo(Symbol(), MODE_BID);
    double point  = MarketInfo(Symbol(), MODE_POINT);
    int    digits = (int)MarketInfo(Symbol(), MODE_DIGITS);

    double entryPrice, slPrice, tp1Price, tp2Price;
    int    orderType;
    string comment;

    if (direction == 1) {  // BUY
        entryPrice = ask;
        slPrice    = NormalizeDouble(entryPrice - atr * SL_ATR_Mult, digits);
        tp1Price   = NormalizeDouble(entryPrice + atr * SL_ATR_Mult * MinRR, digits);
        tp2Price   = NormalizeDouble(entryPrice + atr * TP2_ATR_Mult, digits);

        // London BO override
        if (LondonRangeSet && TimeHour(TimeGMT()) >= London_Open_UTC && TimeHour(TimeGMT()) < (London_Open_UTC + 3)) {
            double rangeMid = (LondonRangeHigh + LondonRangeLow) / 2.0;
            double rangeSize = LondonRangeHigh - LondonRangeLow;
            slPrice  = NormalizeDouble(rangeMid - atr * 0.5, digits);
            tp1Price = NormalizeDouble(LondonRangeHigh + rangeSize * LB_TargetMult, digits);
        }

        orderType = OP_BUY;
        comment   = "GMP BUY";
    } else {  // SELL
        entryPrice = bid;
        slPrice    = NormalizeDouble(entryPrice + atr * SL_ATR_Mult, digits);
        tp1Price   = NormalizeDouble(entryPrice - atr * SL_ATR_Mult * MinRR, digits);
        tp2Price   = NormalizeDouble(entryPrice - atr * TP2_ATR_Mult, digits);

        // London BO override
        if (LondonRangeSet && TimeHour(TimeGMT()) >= London_Open_UTC && TimeHour(TimeGMT()) < (London_Open_UTC + 3)) {
            double rangeMid = (LondonRangeHigh + LondonRangeLow) / 2.0;
            double rangeSize = LondonRangeHigh - LondonRangeLow;
            slPrice  = NormalizeDouble(rangeMid + atr * 0.5, digits);
            tp1Price = NormalizeDouble(LondonRangeLow - rangeSize * LB_TargetMult, digits);
        }

        orderType = OP_SELL;
        comment   = "GMP SELL";
    }

    // ── Calculate position size (risk-based) ─────
    double riskAmount = AccountEquity() * RiskPerTrade_Pct / 100.0;
    double slPips     = MathAbs(entryPrice - slPrice) / point / 10.0;  // XAUUSD: 1 pip = 0.1
    double lotSize    = CalculateLotSize(riskAmount, slPips);

    // Validate R:R
    double reward = MathAbs(tp1Price - entryPrice);
    double risk   = MathAbs(slPrice  - entryPrice);
    if (risk <= 0 || reward / risk < MinRR) {
        Print("GoldMaster: Trade skipped — R:R too low: ", reward/risk, " (min ", MinRR, ")");
        return;
    }

    // Send order
    int ticket = OrderSend(Symbol(), orderType, lotSize, entryPrice, 3, slPrice, tp1Price,
                           comment + " | Magic:" + IntegerToString(MagicNumber),
                           MagicNumber, 0, direction == 1 ? clrLime : clrRed);

    if (ticket < 0) {
        Print("GoldMaster: OrderSend failed. Error: ", GetLastError());
        return;
    }

    TodayTradeCount++;
    LastTradeTime = TimeCurrent();
    Print("GoldMaster: Trade opened. Ticket:", ticket, " Dir:", direction==1?"BUY":"SELL",
          " Entry:", entryPrice, " SL:", slPrice, " TP1:", tp1Price,
          " Lots:", lotSize, " Risk:$", riskAmount);
}

// ─────────────────────────────────────────────
// POSITION SIZE CALCULATOR
// ─────────────────────────────────────────────
double CalculateLotSize(double riskUSD, double slPips)
{
    if (slPips <= 0) return 0.01;

    // XAUUSD: 1 lot = 100 oz, pip value ≈ $1 per 0.01 lot per pip
    // More precisely: pip value = (lot_size * pip_size) / exchange_rate
    // For XAUUSD: 1 standard lot (100 oz) * $0.01 move = $1
    // So: pip_value_per_lot = 1.0 for XAUUSD (in USD account)
    double pipValuePerLot = MarketInfo(Symbol(), MODE_TICKVALUE);
    if (pipValuePerLot <= 0) pipValuePerLot = 1.0;

    double lots = riskUSD / (slPips * pipValuePerLot);

    // Normalize to broker's lot step
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    double lotMin  = MarketInfo(Symbol(), MODE_MINLOT);
    double lotMax  = MarketInfo(Symbol(), MODE_MAXLOT);

    lots = MathFloor(lots / lotStep) * lotStep;
    lots = MathMax(lotMin, MathMin(lotMax, lots));

    // Prop firm guard: never exceed 5% of account in one trade
    double maxLots = (AccountEquity() * 0.05) / (slPips * pipValuePerLot);
    lots = MathMin(lots, MathFloor(maxLots / lotStep) * lotStep);

    return NormalizeDouble(lots, 2);
}

// ─────────────────────────────────────────────
// MANAGE OPEN TRADES (trailing stop, partial close)
// ─────────────────────────────────────────────
void ManageOpenTrades()
{
    for (int i = OrdersTotal() - 1; i >= 0; i--) {
        if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
        if (OrderMagicNumber() != MagicNumber) continue;
        if (OrderSymbol() != Symbol()) continue;

        double atr         = iATR(NULL, 0, ATR_Period, 1);
        double entryPrice  = OrderOpenPrice();
        double currentSL   = OrderStopLoss();
        double currentTP   = OrderTakeProfit();
        double bid         = MarketInfo(Symbol(), MODE_BID);
        double ask         = MarketInfo(Symbol(), MODE_ASK);
        int    digits      = (int)MarketInfo(Symbol(), MODE_DIGITS);
        double point       = MarketInfo(Symbol(), MODE_POINT);
        double initialRisk = MathAbs(entryPrice - currentSL);

        if (OrderType() == OP_BUY) {
            double profit = bid - entryPrice;
            double profitR = (initialRisk > 0) ? profit / initialRisk : 0;

            // Partial close at 1.5R
            if (UsePartialClose && profitR >= PartialClose_R) {
                double closeVol = NormalizeDouble(OrderLots() * PartialClose_Pct / 100.0, 2);
                double lotStep  = MarketInfo(Symbol(), MODE_LOTSTEP);
                closeVol = MathFloor(closeVol / lotStep) * lotStep;
                if (closeVol >= MarketInfo(Symbol(), MODE_MINLOT) && OrderLots() > closeVol) {
                    // Mark that we've already partial closed by checking comment
                    if (StringFind(OrderComment(), "PC") == -1) {
                        if (OrderClose(OrderTicket(), closeVol, bid, 3, clrYellow)) {
                            Print("GoldMaster: Partial close ", closeVol, " lots at 1.5R");
                        }
                    }
                }
            }

            // Trailing stop — activate at TrailActivate_R
            if (UseTrailingStop && profitR >= TrailActivate_R) {
                double trailLevel = bid - atr * 1.0;
                trailLevel = NormalizeDouble(trailLevel, digits);
                if (trailLevel > currentSL + TrailStep_Pips * point * 10) {
                    // Move to breakeven first
                    double beLevel = NormalizeDouble(entryPrice + point * 5, digits);
                    double newSL   = MathMax(beLevel, trailLevel);
                    if (newSL > currentSL) {
                        OrderModify(OrderTicket(), entryPrice, newSL, currentTP, 0, clrCyan);
                    }
                }
            }

            // Move to breakeven at 1R
            if (profitR >= 1.0 && currentSL < entryPrice) {
                double beLevel = NormalizeDouble(entryPrice + point * 10, digits);
                OrderModify(OrderTicket(), entryPrice, beLevel, currentTP, 0, clrBlue);
            }
        }

        if (OrderType() == OP_SELL) {
            double profit  = entryPrice - ask;
            double profitR = (initialRisk > 0) ? profit / initialRisk : 0;

            // Partial close at 1.5R
            if (UsePartialClose && profitR >= PartialClose_R) {
                double closeVol = NormalizeDouble(OrderLots() * PartialClose_Pct / 100.0, 2);
                double lotStep  = MarketInfo(Symbol(), MODE_LOTSTEP);
                closeVol = MathFloor(closeVol / lotStep) * lotStep;
                if (closeVol >= MarketInfo(Symbol(), MODE_MINLOT) && OrderLots() > closeVol) {
                    if (StringFind(OrderComment(), "PC") == -1) {
                        if (OrderClose(OrderTicket(), closeVol, ask, 3, clrYellow)) {
                            Print("GoldMaster: Partial close ", closeVol, " lots at 1.5R");
                        }
                    }
                }
            }

            // Trailing stop
            if (UseTrailingStop && profitR >= TrailActivate_R) {
                double trailLevel = ask + atr * 1.0;
                trailLevel = NormalizeDouble(trailLevel, digits);
                if (currentSL == 0 || trailLevel < currentSL - TrailStep_Pips * point * 10) {
                    double beLevel = NormalizeDouble(entryPrice - point * 5, digits);
                    double newSL   = MathMin(beLevel, trailLevel);
                    if (currentSL == 0 || newSL < currentSL) {
                        OrderModify(OrderTicket(), entryPrice, newSL, currentTP, 0, clrCyan);
                    }
                }
            }

            // Move to breakeven at 1R
            if (profitR >= 1.0 && (currentSL == 0 || currentSL > entryPrice)) {
                double beLevel = NormalizeDouble(entryPrice - point * 10, digits);
                OrderModify(OrderTicket(), entryPrice, beLevel, currentTP, 0, clrBlue);
            }
        }
    }
}

// ─────────────────────────────────────────────
// LONDON RANGE BUILDER
// ─────────────────────────────────────────────
void UpdateLondonRange()
{
    int hourUTC = TimeHour(TimeGMT());
    datetime today = iTime(NULL, PERIOD_D1, 0);

    // Reset range on new day
    if (today != LondonRangeDate) {
        LondonRangeDate = today;
        LondonRangeHigh = 0;
        LondonRangeLow  = 0;
        LondonRangeSet  = false;
    }

    // Build range during pre-London window
    if (hourUTC >= LB_RangeStartHour && hourUTC < LB_RangeEndHour) {
        // Find highest high and lowest low in range window
        double rHigh = 0, rLow = 999999;
        for (int i = 0; i < 50; i++) {
            datetime barTime = iTime(NULL, 0, i);
            int barHour = TimeHour(barTime);
            if (barHour >= LB_RangeStartHour && barHour < LB_RangeEndHour) {
                double h = iHigh(NULL, 0, i);
                double l = iLow(NULL, 0, i);
                if (h > rHigh) rHigh = h;
                if (l < rLow)  rLow  = l;
            }
        }
        if (rHigh > 0 && rLow < 999999) {
            LondonRangeHigh = rHigh;
            LondonRangeLow  = rLow;
            LondonRangeSet  = true;
        }
    }
}

// ─────────────────────────────────────────────
// COUNT OPEN ORDERS (this EA only)
// ─────────────────────────────────────────────
int CountOpenOrders()
{
    int count = 0;
    for (int i = 0; i < OrdersTotal(); i++) {
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
            OrderMagicNumber() == MagicNumber &&
            OrderSymbol() == Symbol()) {
            count++;
        }
    }
    return count;
}

// ─────────────────────────────────────────────
// CALCULATE TODAY'S REALIZED PnL
// ─────────────────────────────────────────────
double GetTodayPnL()
{
    double pnl = 0;
    datetime dayStart = iTime(NULL, PERIOD_D1, 0);

    // Open trades floating PnL
    for (int i = 0; i < OrdersTotal(); i++) {
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
            OrderMagicNumber() == MagicNumber &&
            OrderSymbol() == Symbol()) {
            pnl += OrderProfit() + OrderSwap() + OrderCommission();
        }
    }

    // Closed trades today
    for (int i = OrdersHistoryTotal() - 1; i >= 0; i--) {
        if (OrderSelect(i, SELECT_BY_HISTORY, MODE_HISTORY)) {
            if (OrderMagicNumber() != MagicNumber) continue;
            if (OrderSymbol() != Symbol()) continue;
            if (OrderCloseTime() >= dayStart) {
                pnl += OrderProfit() + OrderSwap() + OrderCommission();
            }
        }
    }
    return pnl;
}

// ─────────────────────────────────────────────
// DASHBOARD — MT4 CHART OVERLAY
// ─────────────────────────────────────────────
void DrawDashboard()
{
    if (!ShowDashboard) return;

    double equity     = AccountEquity();
    double balance    = AccountBalance();
    double drawdown   = (AccountStartEquity > 0) ? (equity - AccountStartEquity) / AccountStartEquity * 100 : 0;
    double dailyDD    = (TodayStartEquity > 0) ? (equity - TodayStartEquity) / TodayStartEquity * 100 : 0;
    double todayPnL   = GetTodayPnL();
    int    openTrades = CountOpenOrders();

    string dash = "";
    dash += "═══ GoldMaster Pro v2.0 ═══\n";
    dash += "Symbol:      XAUUSD\n";
    dash += "Equity:      $" + DoubleToStr(equity, 2) + "\n";
    dash += "Today P&L:   $" + DoubleToStr(todayPnL, 2) + "  (" + DoubleToStr(dailyDD, 2) + "%)\n";
    dash += "Total DD:    " + DoubleToStr(drawdown, 2) + "%\n";
    dash += "Trades Today:" + IntegerToString(TodayTradeCount) + "/" + IntegerToString(MaxTradesPerDay) + "\n";
    dash += "Open Trades: " + IntegerToString(openTrades) + "\n";
    dash += "Prop Mode:   " + (PropFirmMode ? "ON ✓" : "OFF") + "\n";
    dash += "Status:      " + (TradingSuspended ? "SUSPENDED: " + SuspendReason : (CanTrade() ? "ACTIVE" : "WAITING")) + "\n";
    dash += "London Range:" + (LondonRangeSet ? DoubleToStr(LondonRangeLow,2) + " - " + DoubleToStr(LondonRangeHigh,2) : "Building...") + "\n";
    dash += "Daily Limit: $" + DoubleToStr(equity * MaxDailyLoss_Pct / 100, 2) + " (-" + DoubleToStr(MaxDailyLoss_Pct, 1) + "%)";

    Comment(dash);
}

// ─────────────────────────────────────────────
// TRADE EVENTS (for logging)
// ─────────────────────────────────────────────
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
    // MT4 does not have this event — handled via OnTick tracking
}
//+------------------------------------------------------------------+
