//+------------------------------------------------------------------+
//|  GoldMaster Pro EA — MT4 Expert Advisor v2.1 (Fixed)             |
//|  XAUUSD Gold Trading System | Prop Firm Edition                  |
//|  Fixes: removed MQL5 OnTradeTransaction, removed VWAP iCustom,  |
//|         corrected XAUUSD tick-based position sizing              |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property version   "2.10"
#property strict

// ─────────────────────────────────────────────
// INPUT PARAMETERS
// ─────────────────────────────────────────────

// Risk Management
extern double RiskPerTrade_Pct  = 0.75;  // Risk % per trade (0.75% on $100K = $750)
extern double MaxDailyLoss_Pct  = 3.0;   // Max daily drawdown %
extern double MaxTotalDD_Pct    = 6.0;   // Max total drawdown %
extern int    MaxTradesPerDay   = 3;     // Max trades per day
extern double MinRR             = 2.0;   // Minimum Risk:Reward ratio
extern bool   PropFirmMode      = true;  // Strict prop firm risk controls

// Stop / Target
extern int    ATR_Period        = 14;
extern double SL_ATR_Mult       = 1.5;   // Stop loss = ATR * this
extern double TP_ATR_Mult       = 3.0;   // Take profit = ATR * this

// EMA periods
extern int    EMA_Fast          = 9;
extern int    EMA_Mid           = 21;
extern int    EMA_Slow          = 50;
extern int    EMA_Trend         = 200;

// Strategy switches
extern bool   UseStrategy_LondonBO   = true;
extern bool   UseStrategy_TrendPull  = true;
extern bool   UseStrategy_NYMomentum = true;

// Filters
extern int    MinSignalScore    = 65;
extern int    ADX_Period        = 14;
extern int    ADX_MinValue      = 20;
extern int    RSI_Period        = 14;
extern int    RSI_OB            = 70;
extern int    RSI_OS            = 30;
extern double VolFilter_Mult    = 1.3;

// London Breakout
extern int    LB_RangeStartHour = 4;    // UTC — pre-London range start
extern int    LB_RangeEndHour   = 7;    // UTC — London open
extern double LB_TargetMult     = 1.5;  // TP = range * this beyond breakout

// Session hours (UTC)
extern int    London_Open_UTC   = 7;
extern int    London_Close_UTC  = 16;
extern int    NY_Open_UTC       = 13;
extern int    NY_Close_UTC      = 20;

// Trade management
extern bool   UseTrailingStop   = true;
extern double TrailActivate_R   = 1.0;  // Start trailing after X * R profit
extern double TrailATR_Mult     = 1.0;  // Trail distance = ATR * this
extern bool   UsePartialClose   = true;
extern double PartialClose_R    = 1.5;  // Close 50% at 1.5R profit
extern double PartialClose_Pct  = 50.0;

// Display
extern bool   ShowDashboard     = true;

// Magic number — identifies this EA's orders
extern int    MagicNumber       = 20250519;

// ─────────────────────────────────────────────
// GLOBAL STATE
// ─────────────────────────────────────────────
double   AccountStartEquity;
double   TodayStartEquity;
int      TodayTradeCount;
datetime TodayDate;
bool     TradingSuspended;
string   SuspendReason;

double   LondonRangeHigh;
double   LondonRangeLow;
bool     LondonRangeSet;
datetime LondonRangeDate;

int      LastSignalBar;

//+------------------------------------------------------------------+
//| INIT                                                              |
//+------------------------------------------------------------------+
int OnInit()
{
    AccountStartEquity = AccountEquity();
    TodayStartEquity   = AccountEquity();
    TodayTradeCount    = 0;
    TodayDate          = iTime(NULL, PERIOD_D1, 0);
    TradingSuspended   = false;
    SuspendReason      = "";
    LondonRangeHigh    = 0;
    LondonRangeLow     = 0;
    LondonRangeSet     = false;
    LondonRangeDate    = 0;
    LastSignalBar      = -1;

    // Verify we are on XAUUSD
    if (StringFind(Symbol(), "XAU") < 0 && StringFind(Symbol(), "GOLD") < 0)
        Print("WARNING: EA designed for XAUUSD. Current symbol: ", Symbol());

    Print("GoldMaster Pro v2.1 started | Equity: $", DoubleToStr(AccountEquity(), 2));
    Print("Risk per trade: ", RiskPerTrade_Pct, "% = $",
          DoubleToStr(AccountEquity() * RiskPerTrade_Pct / 100.0, 2));
    Print("Prop Firm Mode: ", PropFirmMode ? "ON" : "OFF");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| DEINIT                                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Comment("");
    Print("GoldMaster Pro stopped. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| MAIN TICK                                                         |
//+------------------------------------------------------------------+
void OnTick()
{
    // Manage open trades on every tick (trailing stop, partial close)
    ManageOpenTrades();

    // Only run signal logic on new bar
    static datetime lastBar = 0;
    datetime curBar = iTime(NULL, 0, 0);
    if (curBar == lastBar)
    {
        if (ShowDashboard) DrawDashboard();
        return;
    }
    lastBar = curBar;

    // ── Daily reset ──────────────────────────────────────────────
    datetime today = iTime(NULL, PERIOD_D1, 0);
    if (today != TodayDate)
    {
        TodayDate        = today;
        TodayStartEquity = AccountEquity();
        TodayTradeCount  = 0;
        TradingSuspended = false;
        SuspendReason    = "";
        LondonRangeHigh  = 0;
        LondonRangeLow   = 0;
        LondonRangeSet   = false;
        Print("New day reset | Start equity: $", DoubleToStr(AccountEquity(), 2));
    }

    // ── Update London pre-market range ───────────────────────────
    UpdateLondonRange();

    // ── Risk guard ───────────────────────────────────────────────
    if (!CanTrade()) return;

    // ── Only one trade open at a time ────────────────────────────
    if (CountOpenOrders() > 0) return;

    // ── Get signal ───────────────────────────────────────────────
    int sig = GetSignal();
    if (sig == 0) return;

    // ── Execute ──────────────────────────────────────────────────
    ExecuteTrade(sig);
}

//+------------------------------------------------------------------+
//| RISK GATE                                                         |
//+------------------------------------------------------------------+
bool CanTrade()
{
    if (TradingSuspended) return false;

    // No weekend trading
    int dow = DayOfWeek();
    if (dow == 0 || dow == 6) return false;

    // Session filter — London + NY only
    int h = TimeHour(TimeGMT());
    bool inLondon = (h >= London_Open_UTC  && h < London_Close_UTC);
    bool inNY     = (h >= NY_Open_UTC      && h < NY_Close_UTC);
    if (!inLondon && !inNY) return false;

    // Dead zone: 20:00 – 02:00 UTC
    if (h >= 20 || h < 2) return false;

    if (!PropFirmMode) return true;

    // Daily loss limit
    double dailyDD = AccountEquity() - TodayStartEquity;
    if (dailyDD < -(AccountEquity() * MaxDailyLoss_Pct / 100.0))
    {
        TradingSuspended = true;
        SuspendReason    = StringFormat("Daily loss %.1f%% hit", MaxDailyLoss_Pct);
        Alert("GoldMaster: Daily loss limit reached — trading suspended.");
        return false;
    }

    // Total drawdown
    double totalDD = (AccountStartEquity > 0)
                     ? (AccountEquity() - AccountStartEquity) / AccountStartEquity * 100.0
                     : 0;
    if (totalDD < -MaxTotalDD_Pct)
    {
        TradingSuspended = true;
        SuspendReason    = StringFormat("Total DD %.1f%% breached", MaxTotalDD_Pct);
        Alert("GoldMaster: MAX DRAWDOWN BREACHED — all trading suspended.");
        return false;
    }

    // Daily trade cap
    if (TodayTradeCount >= MaxTradesPerDay) return false;

    // Precautionary: pause at 80% of daily limit
    double dailyDDPct = (TodayStartEquity > 0)
                        ? (AccountEquity() - TodayStartEquity) / TodayStartEquity * 100.0
                        : 0;
    if (dailyDDPct < -(MaxDailyLoss_Pct * 0.8)) return false;

    return true;
}

//+------------------------------------------------------------------+
//| SIGNAL ENGINE  — returns 1=BUY, -1=SELL, 0=NONE                 |
//+------------------------------------------------------------------+
int GetSignal()
{
    // One signal per bar maximum
    if (Bars == LastSignalBar) return 0;

    // ── Read indicators (bar 1 = last closed bar) ────────────────
    double atr    = iATR(NULL, 0, ATR_Period, 1);
    double ema9   = iMA(NULL, 0, EMA_Fast,  0, MODE_EMA, PRICE_CLOSE, 1);
    double ema21  = iMA(NULL, 0, EMA_Mid,   0, MODE_EMA, PRICE_CLOSE, 1);
    double ema50  = iMA(NULL, 0, EMA_Slow,  0, MODE_EMA, PRICE_CLOSE, 1);
    double ema200 = iMA(NULL, 0, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE, 1);
    double rsi    = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
    double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
    double diPlus = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
    double diMinus= iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

    // H4 macro trend
    double ema200_h4 = iMA(NULL, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
    double ema50_h4  = iMA(NULL, PERIOD_H4, 50,  0, MODE_EMA, PRICE_CLOSE, 1);

    double C1 = iClose(NULL, 0, 1);  // last closed bar close
    double O1 = iOpen(NULL,  0, 1);

    // Volume ratio vs 20-bar average
    double volSum = 0;
    for (int k = 1; k <= 20; k++) volSum += (double)iVolume(NULL, 0, k);
    double volAvg   = volSum / 20.0;
    double vol1     = (double)iVolume(NULL, 0, 1);
    double volRatio = (volAvg > 0) ? vol1 / volAvg : 1.0;

    // Momentum
    double mom12 = C1 - iClose(NULL, 0, 13);
    double roc5  = (iClose(NULL, 0, 6) > 0)
                   ? (C1 - iClose(NULL, 0, 6)) / iClose(NULL, 0, 6) * 100.0
                   : 0;

    // Trend flags
    bool htf_bull   = (C1 > ema200_h4 && ema50_h4 > ema200_h4);
    bool htf_bear   = (C1 < ema200_h4 && ema50_h4 < ema200_h4);
    bool micro_bull = (ema9 > ema21 && ema21 > ema50);
    bool micro_bear = (ema9 < ema21 && ema21 < ema50);

    // ── Bull score (max 93) ──────────────────────────────────────
    int bs = 0;
    if (htf_bull)                         bs += 15;
    if (micro_bull)                       bs += 10;
    if (C1 > ema200)                      bs += 5;
    if (mom12 > 0)                        bs += 8;
    if (roc5  > 0)                        bs += 7;
    if (rsi > 50 && rsi < RSI_OB)        bs += 10;
    if (volRatio > VolFilter_Mult)        bs += 10;
    if (volRatio > 2.0)                   bs += 5;
    if (C1 > O1)                          bs += 8;
    if (adx > ADX_MinValue)              bs += 8;
    if (diPlus > diMinus)                bs += 7;

    // ── Bear score (max 93) ──────────────────────────────────────
    int ss = 0;
    if (htf_bear)                         ss += 15;
    if (micro_bear)                       ss += 10;
    if (C1 < ema200)                      ss += 5;
    if (mom12 < 0)                        ss += 8;
    if (roc5  < 0)                        ss += 7;
    if (rsi < 50 && rsi > RSI_OS)        ss += 10;
    if (volRatio > VolFilter_Mult)        ss += 10;
    if (volRatio > 2.0)                   ss += 5;
    if (C1 < O1)                          ss += 8;
    if (adx > ADX_MinValue)              ss += 8;
    if (diMinus > diPlus)                ss += 7;

    int h = TimeHour(TimeGMT());
    bool inLondonOpen = (h >= London_Open_UTC && h < London_Open_UTC + 3);
    bool inNYOpen     = (h >= NY_Open_UTC     && h < NY_Open_UTC + 2);

    // ── Strategy 1: London Session Breakout ──────────────────────
    if (UseStrategy_LondonBO && LondonRangeSet && inLondonOpen)
    {
        if (C1 > LondonRangeHigh && volRatio > VolFilter_Mult && bs >= MinSignalScore - 10)
        {
            LastSignalBar = Bars;
            return 1;
        }
        if (C1 < LondonRangeLow && volRatio > VolFilter_Mult && ss >= MinSignalScore - 10)
        {
            LastSignalBar = Bars;
            return -1;
        }
    }

    // ── Strategy 2: Trend Pullback (EMA bounce) ──────────────────
    if (UseStrategy_TrendPull)
    {
        bool bullZone = (C1 >= ema21 * 0.9985 && C1 <= ema50 * 1.0020);
        bool bearZone = (C1 <= ema21 * 1.0015 && C1 >= ema50 * 0.9980);

        if (htf_bull && micro_bull && bullZone &&
            rsi > RSI_OS && rsi < RSI_OB && bs >= MinSignalScore)
        {
            LastSignalBar = Bars;
            return 1;
        }
        if (htf_bear && micro_bear && bearZone &&
            rsi < RSI_OB && rsi > RSI_OS && ss >= MinSignalScore)
        {
            LastSignalBar = Bars;
            return -1;
        }
    }

    // ── Strategy 3: NY Session Momentum ──────────────────────────
    // VWAP removed — use EMA50 as intraday reference instead
    if (UseStrategy_NYMomentum && inNYOpen)
    {
        bool aboveEMA50 = (C1 > ema50);
        bool belowEMA50 = (C1 < ema50);

        if (htf_bull && aboveEMA50 && mom12 > 0 && roc5 > 0 &&
            volRatio > 1.5 && adx > ADX_MinValue &&
            diPlus > diMinus && bs >= MinSignalScore)
        {
            LastSignalBar = Bars;
            return 1;
        }
        if (htf_bear && belowEMA50 && mom12 < 0 && roc5 < 0 &&
            volRatio > 1.5 && adx > ADX_MinValue &&
            diMinus > diPlus && ss >= MinSignalScore)
        {
            LastSignalBar = Bars;
            return -1;
        }
    }

    return 0;
}

//+------------------------------------------------------------------+
//| EXECUTE TRADE                                                     |
//+------------------------------------------------------------------+
void ExecuteTrade(int dir)
{
    double atr    = iATR(NULL, 0, ATR_Period, 1);
    double ask    = MarketInfo(Symbol(), MODE_ASK);
    double bid    = MarketInfo(Symbol(), MODE_BID);
    int    digits = (int)MarketInfo(Symbol(), MODE_DIGITS);

    double entry, sl, tp;
    int    otype;

    if (dir == 1)   // BUY
    {
        entry = ask;
        sl    = NormalizeDouble(entry - atr * SL_ATR_Mult, digits);
        tp    = NormalizeDouble(entry + atr * SL_ATR_Mult * MinRR, digits);

        // London BO: use range-based levels
        if (LondonRangeSet && TimeHour(TimeGMT()) < London_Open_UTC + 3)
        {
            double mid   = (LondonRangeHigh + LondonRangeLow) / 2.0;
            double rSize = LondonRangeHigh - LondonRangeLow;
            sl = NormalizeDouble(mid - atr * 0.5, digits);
            tp = NormalizeDouble(LondonRangeHigh + rSize * LB_TargetMult, digits);
        }
        otype = OP_BUY;
    }
    else            // SELL
    {
        entry = bid;
        sl    = NormalizeDouble(entry + atr * SL_ATR_Mult, digits);
        tp    = NormalizeDouble(entry - atr * SL_ATR_Mult * MinRR, digits);

        if (LondonRangeSet && TimeHour(TimeGMT()) < London_Open_UTC + 3)
        {
            double mid   = (LondonRangeHigh + LondonRangeLow) / 2.0;
            double rSize = LondonRangeHigh - LondonRangeLow;
            sl = NormalizeDouble(mid + atr * 0.5, digits);
            tp = NormalizeDouble(LondonRangeLow - rSize * LB_TargetMult, digits);
        }
        otype = OP_SELL;
    }

    // Validate SL/TP distances
    double riskPts   = MathAbs(entry - sl);
    double rewardPts = MathAbs(tp - entry);
    if (riskPts <= 0 || rewardPts / riskPts < MinRR)
    {
        Print("GoldMaster: Skipped — R:R too low (",
              DoubleToStr(rewardPts / riskPts, 2), " < ", MinRR, ")");
        return;
    }

    // ── Position sizing (tick-based — broker-agnostic for XAUUSD) ─
    double riskUSD   = AccountEquity() * RiskPerTrade_Pct / 100.0;
    double tickSize  = MarketInfo(Symbol(), MODE_TICKSIZE);
    double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);

    if (tickSize <= 0 || tickValue <= 0)
    {
        Print("GoldMaster: Invalid tick data — cannot size position.");
        return;
    }

    double slTicks = riskPts / tickSize;
    double lots    = riskUSD / (slTicks * tickValue);

    // Normalise to broker step/min/max
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    double lotMin  = MarketInfo(Symbol(), MODE_MINLOT);
    double lotMax  = MarketInfo(Symbol(), MODE_MAXLOT);
    lots = MathFloor(lots / lotStep) * lotStep;
    lots = MathMax(lotMin, MathMin(lotMax, lots));
    lots = NormalizeDouble(lots, 2);

    if (lots <= 0)
    {
        Print("GoldMaster: Lot size calculated as 0 — skipping.");
        return;
    }

    // Send order
    string cmt = StringFormat("GMP %s | Score | Magic:%d",
                              dir == 1 ? "BUY" : "SELL", MagicNumber);
    int ticket = OrderSend(Symbol(), otype, lots, entry, 3,
                           sl, tp, cmt, MagicNumber, 0,
                           dir == 1 ? clrLime : clrRed);

    if (ticket < 0)
    {
        int err = GetLastError();
        Print("GoldMaster: OrderSend failed — error ", err,
              " (", ErrorDescription(err), ")");
        return;
    }

    TodayTradeCount++;
    Print("GoldMaster: Order opened | Ticket:", ticket,
          " | ", dir == 1 ? "BUY" : "SELL",
          " | Entry:", DoubleToStr(entry, digits),
          " | SL:", DoubleToStr(sl, digits),
          " | TP:", DoubleToStr(tp, digits),
          " | Lots:", DoubleToStr(lots, 2),
          " | Risk:$", DoubleToStr(riskUSD, 2));
}

//+------------------------------------------------------------------+
//| MANAGE OPEN TRADES — trailing stop + partial close               |
//+------------------------------------------------------------------+
void ManageOpenTrades()
{
    for (int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
        if (OrderMagicNumber() != MagicNumber)           continue;
        if (OrderSymbol()      != Symbol())              continue;

        double atr        = iATR(NULL, 0, ATR_Period, 1);
        double openPrice  = OrderOpenPrice();
        double curSL      = OrderStopLoss();
        double curTP      = OrderTakeProfit();
        double initRisk   = MathAbs(openPrice - curSL);
        int    digits     = (int)MarketInfo(Symbol(), MODE_DIGITS);
        double point      = MarketInfo(Symbol(), MODE_POINT);
        double bid        = MarketInfo(Symbol(), MODE_BID);
        double ask        = MarketInfo(Symbol(), MODE_ASK);

        // ── BUY trade ────────────────────────────────────────────
        if (OrderType() == OP_BUY)
        {
            double floatProfit = bid - openPrice;
            double profitR     = (initRisk > 0) ? floatProfit / initRisk : 0;

            // Move to breakeven at 1R
            if (profitR >= 1.0 && curSL < openPrice)
            {
                double be = NormalizeDouble(openPrice + point, digits);
                OrderModify(OrderTicket(), openPrice, be, curTP, 0, clrBlue);
            }

            // Partial close at 1.5R
            if (UsePartialClose && profitR >= PartialClose_R &&
                StringFind(OrderComment(), "PC") == -1)
            {
                double closeVol = NormalizeDouble(
                    OrderLots() * PartialClose_Pct / 100.0, 2);
                double step = MarketInfo(Symbol(), MODE_LOTSTEP);
                closeVol = MathFloor(closeVol / step) * step;
                if (closeVol >= MarketInfo(Symbol(), MODE_MINLOT) &&
                    OrderLots() > closeVol + MarketInfo(Symbol(), MODE_MINLOT))
                {
                    if (OrderClose(OrderTicket(), closeVol, bid, 3, clrYellow))
                        Print("GoldMaster: Partial close at 1.5R | lots: ", closeVol);
                }
            }

            // Trailing stop after TrailActivate_R
            if (UseTrailingStop && profitR >= TrailActivate_R)
            {
                double newSL = NormalizeDouble(bid - atr * TrailATR_Mult, digits);
                if (newSL > curSL && newSL > openPrice)
                    OrderModify(OrderTicket(), openPrice, newSL, curTP, 0, clrCyan);
            }
        }

        // ── SELL trade ───────────────────────────────────────────
        if (OrderType() == OP_SELL)
        {
            double floatProfit = openPrice - ask;
            double profitR     = (initRisk > 0) ? floatProfit / initRisk : 0;

            // Move to breakeven at 1R
            if (profitR >= 1.0 && (curSL == 0 || curSL > openPrice))
            {
                double be = NormalizeDouble(openPrice - point, digits);
                OrderModify(OrderTicket(), openPrice, be, curTP, 0, clrBlue);
            }

            // Partial close at 1.5R
            if (UsePartialClose && profitR >= PartialClose_R &&
                StringFind(OrderComment(), "PC") == -1)
            {
                double closeVol = NormalizeDouble(
                    OrderLots() * PartialClose_Pct / 100.0, 2);
                double step = MarketInfo(Symbol(), MODE_LOTSTEP);
                closeVol = MathFloor(closeVol / step) * step;
                if (closeVol >= MarketInfo(Symbol(), MODE_MINLOT) &&
                    OrderLots() > closeVol + MarketInfo(Symbol(), MODE_MINLOT))
                {
                    if (OrderClose(OrderTicket(), closeVol, ask, 3, clrYellow))
                        Print("GoldMaster: Partial close at 1.5R | lots: ", closeVol);
                }
            }

            // Trailing stop
            if (UseTrailingStop && profitR >= TrailActivate_R)
            {
                double newSL = NormalizeDouble(ask + atr * TrailATR_Mult, digits);
                if (curSL == 0 || newSL < curSL)
                    if (newSL < openPrice)
                        OrderModify(OrderTicket(), openPrice, newSL, curTP, 0, clrCyan);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| BUILD PRE-LONDON RANGE                                            |
//+------------------------------------------------------------------+
void UpdateLondonRange()
{
    datetime today = iTime(NULL, PERIOD_D1, 0);
    if (today != LondonRangeDate)
    {
        LondonRangeDate = today;
        LondonRangeHigh = 0;
        LondonRangeLow  = 999999;
        LondonRangeSet  = false;
    }

    int h = TimeHour(TimeGMT());
    if (h < LB_RangeStartHour || h >= LB_RangeEndHour) return;

    // Scan last 50 bars for those inside the range window
    double rHigh = 0, rLow = 999999;
    for (int i = 0; i < 50; i++)
    {
        datetime bt = iTime(NULL, 0, i);
        int bh = TimeHour(bt);
        if (bh < LB_RangeStartHour || bh >= LB_RangeEndHour) continue;
        double hi = iHigh(NULL, 0, i);
        double lo = iLow(NULL,  0, i);
        if (hi > rHigh) rHigh = hi;
        if (lo < rLow)  rLow  = lo;
    }

    if (rHigh > 0 && rLow < 999999)
    {
        LondonRangeHigh = rHigh;
        LondonRangeLow  = rLow;
        LondonRangeSet  = true;
    }
}

//+------------------------------------------------------------------+
//| COUNT EA's OPEN ORDERS                                            |
//+------------------------------------------------------------------+
int CountOpenOrders()
{
    int n = 0;
    for (int i = 0; i < OrdersTotal(); i++)
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
            OrderMagicNumber() == MagicNumber &&
            OrderSymbol() == Symbol()) n++;
    return n;
}

//+------------------------------------------------------------------+
//| TODAY'S P&L (open + closed)                                      |
//+------------------------------------------------------------------+
double GetTodayPnL()
{
    double pnl = 0;
    datetime dayStart = iTime(NULL, PERIOD_D1, 0);

    for (int i = 0; i < OrdersTotal(); i++)
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
            OrderMagicNumber() == MagicNumber &&
            OrderSymbol() == Symbol())
            pnl += OrderProfit() + OrderSwap() + OrderCommission();

    for (int i = OrdersHistoryTotal() - 1; i >= 0; i--)
        if (OrderSelect(i, SELECT_BY_HISTORY, MODE_HISTORY) &&
            OrderMagicNumber() == MagicNumber &&
            OrderSymbol() == Symbol() &&
            OrderCloseTime() >= dayStart)
            pnl += OrderProfit() + OrderSwap() + OrderCommission();

    return pnl;
}

//+------------------------------------------------------------------+
//| DASHBOARD COMMENT                                                 |
//+------------------------------------------------------------------+
void DrawDashboard()
{
    double eq       = AccountEquity();
    double todayPnL = GetTodayPnL();
    double dailyDD  = (TodayStartEquity > 0)
                      ? (eq - TodayStartEquity) / TodayStartEquity * 100.0 : 0;
    double totalDD  = (AccountStartEquity > 0)
                      ? (eq - AccountStartEquity) / AccountStartEquity * 100.0 : 0;

    string status;
    if (TradingSuspended)
        status = "SUSPENDED: " + SuspendReason;
    else if (!CanTrade())
        status = "WAITING (session/limit)";
    else
        status = "ACTIVE";

    string txt = "";
    txt += "══ GoldMaster Pro v2.1 ══\n";
    txt += "Symbol:       " + Symbol() + "\n";
    txt += "Equity:      $" + DoubleToStr(eq, 2) + "\n";
    txt += "Today P&L:   $" + DoubleToStr(todayPnL, 2)
         + " (" + DoubleToStr(dailyDD, 2) + "%)\n";
    txt += "Total DD:     " + DoubleToStr(totalDD, 2) + "%\n";
    txt += "Trades today: " + IntegerToString(TodayTradeCount)
         + " / " + IntegerToString(MaxTradesPerDay) + "\n";
    txt += "Open trades:  " + IntegerToString(CountOpenOrders()) + "\n";
    txt += "Prop mode:    " + (PropFirmMode ? "ON" : "OFF") + "\n";
    txt += "Status:       " + status + "\n";
    txt += "London range: "
         + (LondonRangeSet
            ? DoubleToStr(LondonRangeLow, 2) + " – " + DoubleToStr(LondonRangeHigh, 2)
            : "Building...") + "\n";
    txt += "Daily limit: -$"
         + DoubleToStr(TodayStartEquity * MaxDailyLoss_Pct / 100.0, 2);

    Comment(txt);
}
//+------------------------------------------------------------------+
