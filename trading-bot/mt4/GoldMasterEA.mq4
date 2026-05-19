//+------------------------------------------------------------------+
//| GoldMaster Pro EA v5.0                                           |
//| XAUUSD | Target $1000-$2000/week on $50K account                 |
//| Key fix: no trailing stop, fixed 3R TP, breakeven at 1R          |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property link      ""
#property version   "5.00"
#property strict

//--- Risk (1% on $50K = $500/trade, TP 3R = $1500 win)
extern double RiskPct          = 1.0;   // $500 risk per trade on $50K
extern double MaxDailyLossPct  = 4.0;   // $2000 max daily loss on $50K
extern double MaxTotalDDPct    = 8.0;   // $4000 max total DD on $50K
extern int    MaxDailyTrades   = 5;     // More trades = more weekly profit
extern bool   PropFirmMode     = true;

//--- Stop and target
//    THE CORE FIX: no trailing stop, fixed 3R TP
//    Avg win must EXCEED avg loss for profitability
//    With SL=1.0 ATR and TP=3.0 ATR: even at 40% WR we profit
//    (0.40 x 3R) - (0.60 x 1R) = 1.2R - 0.6R = +0.6R per trade
extern double SL_Mult          = 1.0;   // Stop  = 1.0 x ATR
extern double TP_Mult          = 3.0;   // Target= 3.0 x ATR (FIXED, no trail)
extern int    ATR_Period        = 14;
extern bool   MoveToBreakeven  = true;  // Move SL to entry after 1R profit
extern bool   UseTrail         = false; // DISABLED - was cutting avg win to 0.76R

//--- Trend
extern int    EMA_Fast         = 9;
extern int    EMA_Mid          = 21;
extern int    EMA_Slow         = 50;
extern int    EMA_Trend        = 200;
extern int    ADX_Period       = 14;
extern int    ADX_Min          = 20;    // Back to 20 - 25 was too restrictive
extern int    RSI_Period       = 14;

//--- Signal quality
extern int    MinScore         = 65;    // Back to 65 - 70 was getting 0 longs
extern double VolMult          = 1.3;
extern double MinATR           = 0.5;   // Min ATR to trade (avoid dead sessions)

//--- Strategy switches
extern bool   UseLondonBO      = true;
extern bool   UseTrendPull     = true;
extern bool   UseNYMomentum    = true;
extern bool   UseAsianBO       = true;  // NEW: Asian session breakout

//--- London / Asian breakout settings
extern int    LB_StartHour     = 2;     // Asian range builds 02:00-07:00 UTC
extern int    LB_EndHour       = 7;
extern double LB_TPMult        = 2.0;

//--- Sessions (UTC)
extern int    London_Open      = 7;
extern int    London_Close     = 16;
extern int    NY_Open          = 13;
extern int    NY_Close         = 21;

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

   double weeklyTarget = AccountEquity() * 0.04;
   Print("GoldMaster v5.0 | Equity=$", DoubleToStr(AccountEquity(),2));
   Print("Risk=$", DoubleToStr(AccountEquity()*RiskPct/100,2),
         " | TP=3R=$", DoubleToStr(AccountEquity()*RiskPct/100*3,2),
         " | Weekly target=$", DoubleToStr(weeklyTarget,2));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { Comment(""); }

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
      Print("Daily reset | $", DoubleToStr(AccountEquity(),2));
     }

   BuildRange();
   if(!CanTrade()) return;
   if(OpenOrderCount() > 0) return;

   int sig = GetSignal();
   if(sig != 0) PlaceOrder(sig);
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
   if(h >= 21 || h < 2) return(false);   // No trading 21:00-02:00 UTC

   if(!PropFirmMode) return(true);

   //--- Daily loss check
   double loss = AccountEquity() - g_TodayStartEquity;
   if(loss < -(g_TodayStartEquity * MaxDailyLossPct / 100.0))
     {
      g_Suspended = true; g_SuspendReason = "Daily loss limit";
      Alert("GoldMaster: Daily loss limit hit.");
      return(false);
     }

   //--- Total DD check
   if(g_StartEquity > 0)
     {
      double dd = (AccountEquity() - g_StartEquity) / g_StartEquity * 100.0;
      if(dd < -MaxTotalDDPct)
        {
         g_Suspended = true; g_SuspendReason = "Max DD breached";
         Alert("GoldMaster: MAX DRAWDOWN. Suspended.");
         return(false);
        }
     }

   if(g_TodayTrades >= MaxDailyTrades) return(false);
   return(true);
  }

//+------------------------------------------------------------------+
//| Signal engine — 1=BUY, -1=SELL, 0=none                          |
//+------------------------------------------------------------------+
int GetSignal()
  {
   if(Bars == g_LastSignalBars) return(0);

   double atr = iATR(NULL, 0, ATR_Period, 1);
   if(atr < MinATR) return(0);   // Skip dead/illiquid sessions

   //--- M15 indicators
   double ema9   = iMA(NULL, 0, EMA_Fast,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema21  = iMA(NULL, 0, EMA_Mid,   0, MODE_EMA, PRICE_CLOSE, 1);
   double ema50  = iMA(NULL, 0, EMA_Slow,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema200 = iMA(NULL, 0, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE, 1);
   double rsi    = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
   double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
   double diP    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
   double diM    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

   //--- H4 macro trend only (H1 filter was blocking all longs)
   double h4e200 = iMA(NULL, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4e50  = iMA(NULL, PERIOD_H4,  50, 0, MODE_EMA, PRICE_CLOSE, 1);

   //--- D1 bias (highest timeframe direction)
   double d1e50  = iMA(NULL, PERIOD_D1,  50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double d1e200 = iMA(NULL, PERIOD_D1, 200, 0, MODE_EMA, PRICE_CLOSE, 1);

   double C1 = iClose(NULL, 0, 1);
   double O1 = iOpen(NULL,  0, 1);
   double H1 = iHigh(NULL,  0, 1);
   double L1 = iLow(NULL,   0, 1);
   double C2 = iClose(NULL, 0, 2);

   //--- Volume
   double vsum = 0;
   int vi;
   for(vi = 1; vi <= 20; vi++) vsum += (double)iVolume(NULL, 0, vi);
   double vavg     = vsum / 20.0;
   double volRatio = (vavg > 0) ? (double)iVolume(NULL, 0, 1) / vavg : 1.0;

   //--- Momentum
   double mom = C1 - iClose(NULL, 0, 13);
   double roc  = (iClose(NULL, 0, 6) > 0) ? (C1 - iClose(NULL, 0, 6)) / iClose(NULL, 0, 6) * 100.0 : 0;

   //--- Trend flags
   //    FIX: H4 alone is enough for direction (not H4+H1 which blocked longs)
   bool h4Bull = (h4e50 > h4e200);          // H4 uptrend
   bool h4Bear = (h4e50 < h4e200);          // H4 downtrend
   bool d1Bull = (d1e50 > d1e200);          // D1 uptrend (additional confirmation)
   bool d1Bear = (d1e50 < d1e200);          // D1 downtrend

   bool microBull = (ema9 > ema21 && ema21 > ema50);
   bool microBear = (ema9 < ema21 && ema21 < ema50);

   //--- Candle body quality
   double body   = MathAbs(C1 - O1);
   double range  = H1 - L1;
   double bPct   = (range > 0) ? body / range : 0;
   bool bullBar  = (C1 > O1 && bPct > 0.4);
   bool bearBar  = (C1 < O1 && bPct > 0.4);

   //--- RSI confirmation zones
   bool rsiLong  = (rsi > 45 && rsi < 70);
   bool rsiShort = (rsi > 30 && rsi < 55);

   //--- Bull score
   int bs = 0;
   if(h4Bull)                     bs += 20;   // H4 trend = highest weight
   if(d1Bull)                     bs += 10;   // D1 alignment bonus
   if(microBull)                  bs += 15;   // M15 trend aligned
   if(C1 > ema200)                bs += 5;
   if(mom > 0)                    bs += 8;
   if(roc > 0)                    bs += 7;
   if(rsiLong)                    bs += 15;
   if(volRatio > VolMult)         bs += 10;
   if(bullBar)                    bs += 10;

   //--- Bear score
   int ss = 0;
   if(h4Bear)                     ss += 20;
   if(d1Bear)                     ss += 10;
   if(microBear)                  ss += 15;
   if(C1 < ema200)                ss += 5;
   if(mom < 0)                    ss += 8;
   if(roc < 0)                    ss += 7;
   if(rsiShort)                   ss += 15;
   if(volRatio > VolMult)         ss += 10;
   if(bearBar)                    ss += 10;

   int h = TimeHour(TimeGMT());
   bool inLondonOpen  = (h >= London_Open && h < London_Open + 3);
   bool inNYOpen      = (h >= NY_Open     && h < NY_Open + 2);
   bool inLondon      = (h >= London_Open && h < London_Close);
   bool inNY          = (h >= NY_Open     && h < NY_Close);

   //=================================================================
   //--- Strategy 1: Asian/London Range Breakout
   //    Range built 02:00-07:00 UTC, trade the break at London open
   //=================================================================
   if(UseLondonBO && g_RangeSet && inLondonOpen)
     {
      double rngSize = g_RangeHigh - g_RangeLow;
      if(rngSize >= atr * 0.4)   // Valid range (not a spike)
        {
         //--- BUY: price breaks above range, H4 not strongly bearish
         if(C1 > g_RangeHigh && !h4Bear && volRatio > VolMult && bs >= MinScore - 10)
           {
            g_LastSignalBars = Bars;
            return(1);
           }
         //--- SELL: price breaks below range, H4 not strongly bullish
         if(C1 < g_RangeLow && !h4Bull && volRatio > VolMult && ss >= MinScore - 10)
           {
            g_LastSignalBars = Bars;
            return(-1);
           }
        }
     }

   //=================================================================
   //--- Strategy 2: Trend Pullback to EMA21
   //    H4 trend, M15 pulls to EMA21, bounces with RSI confirmation
   //=================================================================
   if(UseTrendPull && (inLondon || inNY))
     {
      //--- Price must be near EMA21 (within 0.3 ATR)
      double distToEma21 = MathAbs(C1 - ema21);
      bool nearEma21 = (distToEma21 <= atr * 0.3);

      if(h4Bull && microBull && nearEma21 && C1 > ema50 && rsiLong && bs >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      if(h4Bear && microBear && nearEma21 && C1 < ema50 && rsiShort && ss >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   //=================================================================
   //--- Strategy 3: NY Session Momentum Continuation
   //    NY opens and continues London direction
   //=================================================================
   if(UseNYMomentum && inNYOpen)
     {
      bool nyBull = (h4Bull && microBull && C1 > ema21 && mom > 0 &&
                     volRatio > 1.5 && adx > ADX_Min && diP > diM && bs >= MinScore);
      bool nyBear = (h4Bear && microBear && C1 < ema21 && mom < 0 &&
                     volRatio > 1.5 && adx > ADX_Min && diM > diP && ss >= MinScore);

      if(nyBull) { g_LastSignalBars = Bars; return(1);  }
      if(nyBear) { g_LastSignalBars = Bars; return(-1); }
     }

   //=================================================================
   //--- Strategy 4: EMA200 Bounce (high-probability confluent setups)
   //    Price tests EMA200 and bounces with volume + RSI confirmation
   //=================================================================
   if(inLondon || inNY)
     {
      double distToEma200 = MathAbs(C1 - ema200);
      bool nearEma200 = (distToEma200 <= atr * 0.5);

      //--- Bounce long off EMA200 in D1 uptrend
      if(d1Bull && nearEma200 && C1 > ema200 && bullBar &&
         rsi > 35 && rsi < 55 && volRatio > VolMult)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      //--- Bounce short off EMA200 in D1 downtrend
      if(d1Bear && nearEma200 && C1 < ema200 && bearBar &&
         rsi > 45 && rsi < 65 && volRatio > VolMult)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
//| Place order with fixed 3R target — NO trailing stop              |
//+------------------------------------------------------------------+
void PlaceOrder(int dir)
  {
   double atr    = iATR(NULL, 0, ATR_Period, 1);
   double ask    = MarketInfo(Symbol(), MODE_ASK);
   double bid    = MarketInfo(Symbol(), MODE_BID);
   int    digs   = (int)MarketInfo(Symbol(), MODE_DIGITS);

   double entry, sl, tp;
   int    otype;

   if(dir == 1)
     {
      entry = ask;
      sl    = NormalizeDouble(entry - atr * SL_Mult, digs);
      tp    = NormalizeDouble(entry + atr * TP_Mult, digs);

      //--- London BO: SL below range low, TP = range extension
      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(g_RangeLow - atr * 0.25, digs);
         tp = NormalizeDouble(g_RangeHigh + rng * LB_TPMult, digs);
        }
      otype = OP_BUY;
     }
   else
     {
      entry = bid;
      sl    = NormalizeDouble(entry + atr * SL_Mult, digs);
      tp    = NormalizeDouble(entry - atr * TP_Mult, digs);

      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(g_RangeHigh + atr * 0.25, digs);
         tp = NormalizeDouble(g_RangeLow  - rng * LB_TPMult, digs);
        }
      otype = OP_SELL;
     }

   //--- R:R check
   double riskPts = MathAbs(entry - sl);
   double rewPts  = MathAbs(tp - entry);
   if(riskPts <= 0 || rewPts / riskPts < 1.8)
     {
      Print("GoldMaster: R:R check failed. Skipping.");
      return;
     }

   //--- Lot sizing
   double riskUSD = AccountEquity() * RiskPct / 100.0;
   double tickSz  = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tickVal = MarketInfo(Symbol(), MODE_TICKVALUE);
   if(tickSz <= 0 || tickVal <= 0) { Print("GoldMaster: Tick error."); return; }

   double lots = riskUSD / ((riskPts / tickSz) * tickVal);
   double step = MarketInfo(Symbol(), MODE_LOTSTEP);
   lots = MathFloor(lots / step) * step;
   lots = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                  MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lots));
   lots = NormalizeDouble(lots, 2);
   if(lots <= 0) { Print("GoldMaster: Lot=0."); return; }

   string cmt = (dir == 1) ? "GMP BUY v5" : "GMP SELL v5";
   int ticket  = OrderSend(Symbol(), otype, lots, entry, 3, sl, tp, cmt, Magic, 0,
                           (dir==1 ? clrLime : clrRed));
   if(ticket < 0)
     {
      Print("GoldMaster: OrderSend failed. Err=", GetLastError());
      return;
     }

   g_TodayTrades++;
   double rr = rewPts / riskPts;
   Print("GoldMaster: TRADE OPEN | ", (dir==1?"BUY":"SELL"),
         " | Entry=",  DoubleToStr(entry, digs),
         " | SL=",     DoubleToStr(sl, digs),
         " | TP=",     DoubleToStr(tp, digs),
         " | R:R=",    DoubleToStr(rr, 2),
         " | Lots=",   DoubleToStr(lots, 2),
         " | Risk=$",  DoubleToStr(riskUSD, 2),
         " | WinTgt=$",DoubleToStr(riskUSD * rr, 2));
  }

//+------------------------------------------------------------------+
//| Manage trades — breakeven at 1R only, no trail                   |
//+------------------------------------------------------------------+
void ManageTrades()
  {
   int i;
   for(i = OrdersTotal() - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != Magic)    continue;
      if(OrderSymbol()      != Symbol()) continue;

      double openPx   = OrderOpenPrice();
      double curSL    = OrderStopLoss();
      double curTP    = OrderTakeProfit();
      double initRisk = MathAbs(openPx - curSL);
      int    digs     = (int)MarketInfo(Symbol(), MODE_DIGITS);
      double bid      = MarketInfo(Symbol(), MODE_BID);
      double ask      = MarketInfo(Symbol(), MODE_ASK);
      double pt       = MarketInfo(Symbol(), MODE_POINT);

      if(!MoveToBreakeven) continue;   // Skip if BE disabled

      if(OrderType() == OP_BUY)
        {
         double profR = (initRisk > 0) ? (bid - openPx) / initRisk : 0;
         //--- Move SL to entry + 1 point at 1R (protect from full loss)
         if(profR >= 1.0 && curSL < openPx)
           {
            double be = NormalizeDouble(openPx + pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE error=", GetLastError());
           }
        }

      if(OrderType() == OP_SELL)
        {
         double profR = (initRisk > 0) ? (openPx - ask) / initRisk : 0;
         //--- Move SL to entry - 1 point at 1R
         if(profR >= 1.0 && (curSL == 0 || curSL > openPx))
           {
            double be = NormalizeDouble(openPx - pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE error=", GetLastError());
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Build Asian/pre-London range (02:00-07:00 UTC)                   |
//+------------------------------------------------------------------+
void BuildRange()
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
   for(i = 0; i < 80; i++)
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
   double risk    = eq * RiskPct / 100.0;
   double dailyPL = eq - g_TodayStartEquity;
   double totalDD = (g_StartEquity > 0) ? (eq - g_StartEquity) / g_StartEquity * 100.0 : 0;

   string status = g_Suspended ? "SUSPENDED: " + g_SuspendReason :
                   (CanTrade() ? "ACTIVE" : "WAITING");

   string rng = g_RangeSet
                ? DoubleToStr(g_RangeLow,2) + " to " + DoubleToStr(g_RangeHigh,2)
                : "Building...";

   Comment("GoldMaster Pro v5.0\n"
         + "Equity:    $" + DoubleToStr(eq, 2) + "\n"
         + "Risk/trade:$" + DoubleToStr(risk, 2) + " | TP=$" + DoubleToStr(risk*3,2) + "\n"
         + "Day P&L:  $" + DoubleToStr(dailyPL, 2) + "\n"
         + "Total DD:  " + DoubleToStr(totalDD, 2) + "%\n"
         + "Trades:    " + IntegerToString(g_TodayTrades) + "/" + IntegerToString(MaxDailyTrades) + "\n"
         + "Open:      " + IntegerToString(OpenOrderCount()) + "\n"
         + "Range:     " + rng + "\n"
         + "Status:    " + status + "\n"
         + "SL=" + DoubleToStr(SL_Mult,1) + "xATR | TP=" + DoubleToStr(TP_Mult,1) + "xATR | Trail=OFF");
  }
//+------------------------------------------------------------------+
