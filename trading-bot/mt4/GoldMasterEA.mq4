//+------------------------------------------------------------------+
//| GoldMaster Pro EA v4.0 - Optimized for Profitability             |
//| XAUUSD Gold Trading Bot - Prop Firm Edition                      |
//| Fixes: inverted R:R, longs vs trend, partial close cutting wins  |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property link      ""
#property version   "4.00"
#property strict

//--- Risk Management
extern double RiskPct          = 0.75;  // Risk per trade (%)
extern double MaxDailyLossPct  = 3.0;   // Max daily loss (%)
extern double MaxTotalDDPct    = 6.0;   // Max total drawdown (%)
extern int    MaxDailyTrades   = 3;     // Max trades per day
extern bool   PropFirmMode     = true;

//--- Stop / Target  (KEY FIX: wider TP, tighter SL = positive R:R)
extern double SL_Mult          = 1.0;   // Stop  = ATR * 1.0  (was 1.5 - too wide)
extern double TP_Mult          = 2.5;   // Target= ATR * 2.5  (was 3.0 but partial killed it)
extern double MinRR            = 2.0;   // Hard minimum R:R check
extern int    ATR_Period       = 14;

//--- Trend filters
extern int    EMA_Fast         = 9;
extern int    EMA_Mid          = 21;
extern int    EMA_Slow         = 50;
extern int    EMA_Trend        = 200;
extern int    ADX_Period       = 14;
extern int    ADX_Min          = 25;    // Was 20 - raised to require stronger trend
extern int    RSI_Period       = 14;

//--- Signal quality
extern int    MinScore         = 70;    // Was 65 - raised to reduce losing trades
extern double VolMult          = 1.5;   // Was 1.3 - raised volume requirement
extern double MinATR           = 1.0;   // Min ATR in points - avoid dead markets

//--- Strategy switches
extern bool   UseLondonBO      = true;
extern bool   UseTrendPull     = true;
extern bool   UseNYMomentum    = true;

//--- London breakout
extern int    LB_StartHour     = 4;     // UTC range start
extern int    LB_EndHour       = 7;     // UTC London open
extern double LB_TPMult        = 2.0;   // TP = range * this

//--- Session hours UTC
extern int    London_Open      = 7;
extern int    London_Close     = 16;
extern int    NY_Open          = 13;
extern int    NY_Close         = 20;

//--- Trade management (KEY FIX: no partial close - was killing R:R)
extern bool   UseTrail         = true;
extern double TrailStartR      = 1.5;   // Only trail after 1.5R (was 1.0)
extern double TrailATRMult     = 0.8;   // Trail = ATR * 0.8 (tight enough to protect)
extern bool   UsePartial       = false; // DISABLED - was cutting avg win to 0.6R

//--- Display
extern bool   ShowInfo         = true;
extern int    Magic            = 20250519;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
double   g_StartEquity;
double   g_TodayStartEquity;
int      g_TodayTrades;
datetime g_TodayDate;
bool     g_Suspended;
string   g_SuspendReason;
double   g_RangeHigh;
double   g_RangeLow;
bool     g_RangeSet;
datetime g_RangeDate;
int      g_LastSignalBars;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_StartEquity      = AccountEquity();
   g_TodayStartEquity = AccountEquity();
   g_TodayTrades      = 0;
   g_TodayDate        = iTime(NULL, PERIOD_D1, 0);
   g_Suspended        = false;
   g_SuspendReason    = "";
   g_RangeHigh        = 0;
   g_RangeLow         = 0;
   g_RangeSet         = false;
   g_RangeDate        = 0;
   g_LastSignalBars   = -1;

   Print("GoldMaster v4.0 started. Equity=$", DoubleToStr(AccountEquity(), 2));
   Print("SL=", SL_Mult, "xATR  TP=", TP_Mult, "xATR  MinRR=", MinRR);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManageTrades();

   static datetime lastBar = 0;
   datetime curBar = iTime(NULL, 0, 0);
   if(curBar == lastBar)
     {
      if(ShowInfo) ShowDashboard();
      return;
     }
   lastBar = curBar;

   //--- Daily reset
   datetime today = iTime(NULL, PERIOD_D1, 0);
   if(today != g_TodayDate)
     {
      g_TodayDate        = today;
      g_TodayStartEquity = AccountEquity();
      g_TodayTrades      = 0;
      g_Suspended        = false;
      g_SuspendReason    = "";
      g_RangeHigh        = 0;
      g_RangeLow         = 0;
      g_RangeSet         = false;
      Print("Daily reset. Equity=$", DoubleToStr(AccountEquity(), 2));
     }

   BuildLondonRange();
   if(!CanTrade()) return;
   if(OpenOrderCount() > 0) return;

   int sig = GetSignal();
   if(sig == 0) return;

   PlaceOrder(sig);
  }

//+------------------------------------------------------------------+
//| Risk gate                                                         |
//+------------------------------------------------------------------+
bool CanTrade()
  {
   if(g_Suspended) return(false);

   int dow = DayOfWeek();
   if(dow == 0 || dow == 6) return(false);

   int h = TimeHour(TimeGMT());
   if(h >= 20 || h < 2) return(false);

   bool inLondon = (h >= London_Open && h < London_Close);
   bool inNY     = (h >= NY_Open     && h < NY_Close);
   if(!inLondon && !inNY) return(false);

   if(!PropFirmMode) return(true);

   double dailyPnL = AccountEquity() - g_TodayStartEquity;
   if(dailyPnL < -(g_TodayStartEquity * MaxDailyLossPct / 100.0))
     {
      g_Suspended     = true;
      g_SuspendReason = "Daily loss limit";
      Alert("GoldMaster: Daily loss limit hit. Suspended.");
      return(false);
     }

   if(g_StartEquity > 0)
     {
      double ddPct = (AccountEquity() - g_StartEquity) / g_StartEquity * 100.0;
      if(ddPct < -MaxTotalDDPct)
        {
         g_Suspended     = true;
         g_SuspendReason = "Max DD breached";
         Alert("GoldMaster: MAX DRAWDOWN. Suspended.");
         return(false);
        }
     }

   if(g_TodayTrades >= MaxDailyTrades) return(false);

   return(true);
  }

//+------------------------------------------------------------------+
//| Signal engine                                                     |
//+------------------------------------------------------------------+
int GetSignal()
  {
   if(Bars == g_LastSignalBars) return(0);

   //--- Core indicators
   double atr    = iATR(NULL, 0, ATR_Period, 1);

   //--- KEY FIX: ATR filter - skip dead/choppy markets
   if(atr < MinATR) return(0);

   double ema9   = iMA(NULL, 0, EMA_Fast,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema21  = iMA(NULL, 0, EMA_Mid,   0, MODE_EMA, PRICE_CLOSE, 1);
   double ema50  = iMA(NULL, 0, EMA_Slow,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema200 = iMA(NULL, 0, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE, 1);
   double rsi    = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
   double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
   double diP    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
   double diM    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

   //--- KEY FIX: Use both H4 AND H1 for stronger trend confirmation
   double h4ema200 = iMA(NULL, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4ema50  = iMA(NULL, PERIOD_H4,  50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h1ema50  = iMA(NULL, PERIOD_H1,  50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h1ema200 = iMA(NULL, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE, 1);

   double C1 = iClose(NULL, 0, 1);
   double C2 = iClose(NULL, 0, 2);
   double O1 = iOpen(NULL,  0, 1);
   double H1 = iHigh(NULL,  0, 1);
   double L1 = iLow(NULL,   0, 1);

   //--- Volume
   double volSum = 0;
   int vi;
   for(vi = 1; vi <= 20; vi++) volSum += (double)iVolume(NULL, 0, vi);
   double volAvg   = volSum / 20.0;
   double volRatio = (volAvg > 0) ? (double)iVolume(NULL, 0, 1) / volAvg : 1.0;

   //--- Momentum
   double mom = C1 - iClose(NULL, 0, 13);
   double roc  = 0;
   if(iClose(NULL, 0, 6) > 0)
      roc = (C1 - iClose(NULL, 0, 6)) / iClose(NULL, 0, 6) * 100.0;

   //--- KEY FIX: Dual timeframe trend - BOTH H4 and H1 must agree
   bool h4Bull = (C1 > h4ema200 && h4ema50 > h4ema200);
   bool h4Bear = (C1 < h4ema200 && h4ema50 < h4ema200);
   bool h1Bull = (C1 > h1ema50  && h1ema50  > h1ema200);
   bool h1Bear = (C1 < h1ema50  && h1ema50  < h1ema200);

   //--- Full trend alignment (macro + intermediate must agree)
   bool trendBull = (h4Bull && h1Bull);
   bool trendBear = (h4Bear && h1Bear);

   //--- Candle quality
   double body    = MathAbs(C1 - O1);
   double candle  = H1 - L1;
   double bodyPct = (candle > 0) ? body / candle : 0;
   bool   bullBar = (C1 > O1 && bodyPct > 0.5);   // Strong bullish candle
   bool   bearBar = (C1 < O1 && bodyPct > 0.5);   // Strong bearish candle

   //--- Micro trend
   bool microBull = (ema9 > ema21 && ema21 > ema50);
   bool microBear = (ema9 < ema21 && ema21 < ema50);

   //--- Bull score (max 100)
   int bs = 0;
   if(trendBull)                  bs += 25;   // H4+H1 alignment = most weight
   else if(h4Bull)                bs += 10;   // H4 only = partial credit
   if(microBull)                  bs += 15;
   if(C1 > ema200)                bs += 5;
   if(mom > 0)                    bs += 8;
   if(roc > 0)                    bs += 7;
   if(rsi > 45 && rsi < 65)      bs += 15;   // Sweet spot RSI for entries
   if(volRatio > VolMult)         bs += 10;
   if(bullBar)                    bs += 10;
   if(adx > ADX_Min && diP > diM) bs += 5;

   //--- Bear score (max 100)
   int ss = 0;
   if(trendBear)                  ss += 25;
   else if(h4Bear)                ss += 10;
   if(microBear)                  ss += 15;
   if(C1 < ema200)                ss += 5;
   if(mom < 0)                    ss += 8;
   if(roc < 0)                    ss += 7;
   if(rsi > 35 && rsi < 55)      ss += 15;
   if(volRatio > VolMult)         ss += 10;
   if(bearBar)                    ss += 10;
   if(adx > ADX_Min && diM > diP) ss += 5;

   int h = TimeHour(TimeGMT());
   bool inLondonOpen = (h >= London_Open && h < London_Open + 3);
   bool inNYOpen     = (h >= NY_Open     && h < NY_Open + 2);

   //--- Strategy 1: London Breakout
   //    KEY FIX: also require trend alignment for breakout direction
   if(UseLondonBO && g_RangeSet && inLondonOpen)
     {
      double rngSize = g_RangeHigh - g_RangeLow;
      //--- Minimum range size: at least 0.5 ATR to avoid tiny ranges
      if(rngSize >= atr * 0.5)
        {
         if(C1 > g_RangeHigh && (h4Bull || trendBull) && volRatio > VolMult && bs >= MinScore - 5)
           {
            g_LastSignalBars = Bars;
            return(1);
           }
         if(C1 < g_RangeLow && (h4Bear || trendBear) && volRatio > VolMult && ss >= MinScore - 5)
           {
            g_LastSignalBars = Bars;
            return(-1);
           }
        }
     }

   //--- Strategy 2: Trend Pullback
   //    KEY FIX: require FULL dual-TF trend (not just H4)
   if(UseTrendPull)
     {
      bool bullZone = (C1 >= ema21 * 0.9990 && C1 <= ema50 * 1.0015);
      bool bearZone = (C1 <= ema21 * 1.0010 && C1 >= ema50 * 0.9985);

      //--- Bull: need full trend bull, price in pullback zone, RSI not OB
      if(trendBull && microBull && bullZone && rsi > 40 && rsi < 60 && bs >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      //--- Bear: need full trend bear, price in pullback zone, RSI not OS
      if(trendBear && microBear && bearZone && rsi > 40 && rsi < 60 && ss >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   //--- Strategy 3: NY Session Momentum
   //    Only fire when strong H4+H1 trend confirmed
   if(UseNYMomentum && inNYOpen)
     {
      if(trendBull && C1 > ema21 && mom > 0 && roc > 0 &&
         volRatio > 1.8 && adx > ADX_Min && diP > diM && bs >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      if(trendBear && C1 < ema21 && mom < 0 && roc < 0 &&
         volRatio > 1.8 && adx > ADX_Min && diM > diP && ss >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
//| Place order                                                       |
//+------------------------------------------------------------------+
void PlaceOrder(int dir)
  {
   double atr    = iATR(NULL, 0, ATR_Period, 1);
   double ask    = MarketInfo(Symbol(), MODE_ASK);
   double bid    = MarketInfo(Symbol(), MODE_BID);
   int    digits = (int)MarketInfo(Symbol(), MODE_DIGITS);

   double entry, sl, tp;
   int    otype;

   if(dir == 1)
     {
      entry = ask;
      sl    = NormalizeDouble(entry - atr * SL_Mult, digits);
      tp    = NormalizeDouble(entry + atr * TP_Mult, digits);

      //--- London BO: range-based levels
      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(g_RangeLow - atr * 0.3, digits);  // SL below range low
         tp = NormalizeDouble(g_RangeHigh + rng * LB_TPMult, digits);
        }
      otype = OP_BUY;
     }
   else
     {
      entry = bid;
      sl    = NormalizeDouble(entry + atr * SL_Mult, digits);
      tp    = NormalizeDouble(entry - atr * TP_Mult, digits);

      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(g_RangeHigh + atr * 0.3, digits);  // SL above range high
         tp = NormalizeDouble(g_RangeLow - rng * LB_TPMult, digits);
        }
      otype = OP_SELL;
     }

   //--- Validate R:R
   double riskPts   = MathAbs(entry - sl);
   double rewardPts = MathAbs(tp - entry);
   if(riskPts <= 0)
     {
      Print("GoldMaster: Invalid SL. Skipping.");
      return;
     }
   double actualRR = rewardPts / riskPts;
   if(actualRR < MinRR)
     {
      Print("GoldMaster: R:R too low: ", DoubleToStr(actualRR, 2), " < ", MinRR, ". Skipping.");
      return;
     }

   //--- Lot size (tick-based, broker-agnostic)
   double riskUSD  = AccountEquity() * RiskPct / 100.0;
   double tickSz   = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tickVal  = MarketInfo(Symbol(), MODE_TICKVALUE);
   if(tickSz <= 0 || tickVal <= 0)
     {
      Print("GoldMaster: Tick data unavailable.");
      return;
     }

   double lots = riskUSD / ((riskPts / tickSz) * tickVal);
   double step = MarketInfo(Symbol(), MODE_LOTSTEP);
   lots = MathFloor(lots / step) * step;
   lots = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                  MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lots));
   lots = NormalizeDouble(lots, 2);

   if(lots <= 0)
     {
      Print("GoldMaster: Lot=0. Skipping.");
      return;
     }

   string cmt  = (dir == 1) ? "GMP BUY v4" : "GMP SELL v4";
   color  clr  = (dir == 1) ? clrLime : clrRed;
   int ticket  = OrderSend(Symbol(), otype, lots, entry, 3, sl, tp, cmt, Magic, 0, clr);

   if(ticket < 0)
     {
      Print("GoldMaster: OrderSend failed. Err=", GetLastError());
      return;
     }

   g_TodayTrades++;
   Print("GoldMaster: ORDER OPEN | Ticket=", ticket,
         " | ", (dir==1?"BUY":"SELL"),
         " | Entry=", DoubleToStr(entry, digits),
         " | SL=",    DoubleToStr(sl, digits),
         " | TP=",    DoubleToStr(tp, digits),
         " | RR=",    DoubleToStr(actualRR, 2),
         " | Lots=",  DoubleToStr(lots, 2),
         " | Risk=$", DoubleToStr(riskUSD, 2));
  }

//+------------------------------------------------------------------+
//| Trade management - trailing stop only (partial close disabled)   |
//+------------------------------------------------------------------+
void ManageTrades()
  {
   int i;
   for(i = OrdersTotal() - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != Magic)    continue;
      if(OrderSymbol()      != Symbol()) continue;

      double atr       = iATR(NULL, 0, ATR_Period, 1);
      double openPx    = OrderOpenPrice();
      double curSL     = OrderStopLoss();
      double curTP     = OrderTakeProfit();
      double initRisk  = MathAbs(openPx - curSL);
      int    digs      = (int)MarketInfo(Symbol(), MODE_DIGITS);
      double bid       = MarketInfo(Symbol(), MODE_BID);
      double ask       = MarketInfo(Symbol(), MODE_ASK);
      double pt        = MarketInfo(Symbol(), MODE_POINT);

      if(OrderType() == OP_BUY)
        {
         double profR = (initRisk > 0) ? (bid - openPx) / initRisk : 0;

         //--- Move to breakeven at 1R
         if(profR >= 1.0 && curSL < openPx)
           {
            double be = NormalizeDouble(openPx + pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE modify error=", GetLastError());
           }

         //--- Trailing stop (starts at TrailStartR)
         if(UseTrail && profR >= TrailStartR)
           {
            double newSL = NormalizeDouble(bid - atr * TrailATRMult, digs);
            if(newSL > curSL && newSL > openPx)
              {
               bool ok = OrderModify(OrderTicket(), openPx, newSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail modify error=", GetLastError());
              }
           }
        }

      if(OrderType() == OP_SELL)
        {
         double profR = (initRisk > 0) ? (openPx - ask) / initRisk : 0;

         //--- Move to breakeven at 1R
         if(profR >= 1.0 && (curSL == 0 || curSL > openPx))
           {
            double be = NormalizeDouble(openPx - pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE modify error=", GetLastError());
           }

         //--- Trailing stop
         if(UseTrail && profR >= TrailStartR)
           {
            double newSL = NormalizeDouble(ask + atr * TrailATRMult, digs);
            if(curSL == 0 || (newSL < curSL && newSL < openPx))
              {
               bool ok = OrderModify(OrderTicket(), openPx, newSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail modify error=", GetLastError());
              }
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Build pre-London range                                            |
//+------------------------------------------------------------------+
void BuildLondonRange()
  {
   datetime today = iTime(NULL, PERIOD_D1, 0);
   if(today != g_RangeDate)
     {
      g_RangeDate = today;
      g_RangeHigh = 0;
      g_RangeLow  = 999999;
      g_RangeSet  = false;
     }

   int h = TimeHour(TimeGMT());
   if(h < LB_StartHour || h >= LB_EndHour) return;

   double rh = 0, rl = 999999;
   int i;
   for(i = 0; i < 60; i++)
     {
      int bh = TimeHour(iTime(NULL, 0, i));
      if(bh < LB_StartHour || bh >= LB_EndHour) continue;
      double hi = iHigh(NULL, 0, i);
      double lo = iLow(NULL,  0, i);
      if(hi > rh) rh = hi;
      if(lo < rl) rl = lo;
     }

   if(rh > 0 && rl < 999999)
     {
      g_RangeHigh = rh;
      g_RangeLow  = rl;
      g_RangeSet  = true;
     }
  }

//+------------------------------------------------------------------+
int OpenOrderCount()
  {
   int n = 0, i;
   for(i = 0; i < OrdersTotal(); i++)
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
         OrderMagicNumber() == Magic &&
         OrderSymbol()      == Symbol()) n++;
   return(n);
  }

//+------------------------------------------------------------------+
void ShowDashboard()
  {
   double eq      = AccountEquity();
   double dailyDD = (g_TodayStartEquity > 0)
                    ? (eq - g_TodayStartEquity) / g_TodayStartEquity * 100.0 : 0;
   double totalDD = (g_StartEquity > 0)
                    ? (eq - g_StartEquity) / g_StartEquity * 100.0 : 0;

   string st = g_Suspended ? "SUSPENDED: " + g_SuspendReason :
              (CanTrade() ? "ACTIVE" : "WAITING");

   string rng = g_RangeSet
                ? DoubleToStr(g_RangeLow, 2) + " to " + DoubleToStr(g_RangeHigh, 2)
                : "Building...";

   Comment("GoldMaster Pro v4.0\n"
         + "Equity:   $" + DoubleToStr(eq, 2) + "\n"
         + "Day DD:   " + DoubleToStr(dailyDD, 2) + "%\n"
         + "Total DD: " + DoubleToStr(totalDD, 2) + "%\n"
         + "Trades:   " + IntegerToString(g_TodayTrades) + "/" + IntegerToString(MaxDailyTrades) + "\n"
         + "Open:     " + IntegerToString(OpenOrderCount()) + "\n"
         + "Range:    " + rng + "\n"
         + "Status:   " + st + "\n"
         + "SL=" + DoubleToStr(SL_Mult,1) + "xATR  TP=" + DoubleToStr(TP_Mult,1) + "xATR");
  }
//+------------------------------------------------------------------+
