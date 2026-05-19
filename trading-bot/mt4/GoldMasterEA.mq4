//+------------------------------------------------------------------+
//| GoldMaster Pro EA v3.0                                           |
//| XAUUSD Gold Trading Bot - Prop Firm Edition                      |
//| Target: $1000-$1500/week on $100K account                        |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property link      ""
#property version   "3.00"
#property strict

//--- Risk inputs
extern double RiskPct         = 0.75;   // Risk per trade (%)
extern double MaxDailyLossPct = 3.0;    // Max daily loss (%)
extern double MaxTotalDDPct   = 6.0;    // Max total drawdown (%)
extern int    MaxDailyTrades  = 3;      // Max trades per day
extern double MinRR           = 2.0;    // Min risk:reward ratio
extern bool   PropFirmMode    = true;   // Prop firm safety mode

//--- Indicator inputs
extern int    ATR_Period      = 14;
extern double SL_Mult         = 1.5;    // Stop = ATR * SL_Mult
extern double TP_Mult         = 3.0;    // TP   = ATR * SL_Mult * MinRR
extern int    EMA_Fast        = 9;
extern int    EMA_Mid         = 21;
extern int    EMA_Slow        = 50;
extern int    EMA_Trend       = 200;
extern int    RSI_Period      = 14;
extern int    ADX_Period      = 14;
extern int    ADX_Min         = 20;
extern double VolMult         = 1.3;    // Volume filter multiplier
extern int    MinScore        = 65;     // Min signal score (0-100)

//--- Strategy switches
extern bool   UseLondonBO     = true;   // London breakout strategy
extern bool   UseTrendPull    = true;   // Trend pullback strategy
extern bool   UseNYMomentum   = true;   // NY momentum strategy

//--- London breakout inputs
extern int    LB_StartHour    = 4;      // Range build start (UTC)
extern int    LB_EndHour      = 7;      // Range build end / London open (UTC)
extern double LB_TPMult       = 1.5;    // TP = range * LB_TPMult

//--- Session hours UTC
extern int    London_Open     = 7;
extern int    London_Close    = 16;
extern int    NY_Open         = 13;
extern int    NY_Close        = 20;

//--- Trade management
extern bool   UseTrail        = true;
extern double TrailStartR     = 1.0;    // Start trailing after 1R profit
extern double TrailATRMult    = 1.0;    // Trail distance = ATR * this
extern bool   UsePartial      = true;
extern double PartialR        = 1.5;    // Partial close at 1.5R
extern double PartialPct      = 50.0;   // Close 50% of position

//--- Display
extern bool   ShowInfo        = true;

//--- EA identifier
extern int    Magic           = 20250519;

//+------------------------------------------------------------------+
//| Global variables                                                  |
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
//| Expert initialization                                             |
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

   Print("GoldMaster Pro v3.0 started. Equity=$", DoubleToStr(AccountEquity(),2));
   Print("Risk=", RiskPct, "% PropFirm=", PropFirmMode);

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Comment("");
   Print("GoldMaster stopped. Code=", reason);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                              |
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
      Print("Daily reset. Equity=$", DoubleToStr(AccountEquity(),2));
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

   //--- Dead zone 20:00-02:00 UTC
   if(h >= 20 || h < 2) return(false);

   //--- London + NY sessions only
   bool inLondon = (h >= London_Open && h < London_Close);
   bool inNY     = (h >= NY_Open     && h < NY_Close);
   if(!inLondon && !inNY) return(false);

   if(!PropFirmMode) return(true);

   //--- Daily loss check
   double dailyPnL = AccountEquity() - g_TodayStartEquity;
   if(dailyPnL < -(g_TodayStartEquity * MaxDailyLossPct / 100.0))
     {
      g_Suspended     = true;
      g_SuspendReason = "Daily loss limit hit";
      Alert("GoldMaster: Daily loss limit reached. Trading suspended.");
      return(false);
     }

   //--- Total drawdown check
   if(g_StartEquity > 0)
     {
      double ddPct = (AccountEquity() - g_StartEquity) / g_StartEquity * 100.0;
      if(ddPct < -MaxTotalDDPct)
        {
         g_Suspended     = true;
         g_SuspendReason = "Max drawdown breached";
         Alert("GoldMaster: MAX DRAWDOWN BREACHED. Trading suspended.");
         return(false);
        }
     }

   //--- Daily trade limit
   if(g_TodayTrades >= MaxDailyTrades) return(false);

   return(true);
  }

//+------------------------------------------------------------------+
//| Signal engine - returns 1=BUY, -1=SELL, 0=none                  |
//+------------------------------------------------------------------+
int GetSignal()
  {
   if(Bars == g_LastSignalBars) return(0);

   double atr    = iATR(NULL, 0, ATR_Period, 1);
   double ema9   = iMA(NULL, 0, EMA_Fast,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema21  = iMA(NULL, 0, EMA_Mid,   0, MODE_EMA, PRICE_CLOSE, 1);
   double ema50  = iMA(NULL, 0, EMA_Slow,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema200 = iMA(NULL, 0, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE, 1);

   double rsi    = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
   double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
   double diP    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
   double diM    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

   //--- H4 macro trend
   double h4ema200 = iMA(NULL, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4ema50  = iMA(NULL, PERIOD_H4,  50, 0, MODE_EMA, PRICE_CLOSE, 1);

   double C1 = iClose(NULL, 0, 1);
   double O1 = iOpen(NULL,  0, 1);

   //--- Volume ratio
   double volSum = 0;
   int vi;
   for(vi = 1; vi <= 20; vi++) volSum += (double)iVolume(NULL, 0, vi);
   double volAvg   = volSum / 20.0;
   double vol1     = (double)iVolume(NULL, 0, 1);
   double volRatio = (volAvg > 0) ? vol1 / volAvg : 1.0;

   //--- Momentum
   double mom = C1 - iClose(NULL, 0, 13);
   double roc  = 0;
   double c6 = iClose(NULL, 0, 6);
   if(c6 > 0) roc = (C1 - c6) / c6 * 100.0;

   //--- Trend flags
   bool htfBull   = (C1 > h4ema200 && h4ema50 > h4ema200);
   bool htfBear   = (C1 < h4ema200 && h4ema50 < h4ema200);
   bool microBull = (ema9 > ema21 && ema21 > ema50);
   bool microBear = (ema9 < ema21 && ema21 < ema50);

   //--- Bull score
   int bs = 0;
   if(htfBull)                    bs += 15;
   if(microBull)                  bs += 10;
   if(C1 > ema200)                bs += 5;
   if(mom > 0)                    bs += 8;
   if(roc > 0)                    bs += 7;
   if(rsi > 50 && rsi < 70)      bs += 10;
   if(volRatio > VolMult)         bs += 10;
   if(volRatio > 2.0)             bs += 5;
   if(C1 > O1)                   bs += 8;
   if(adx > ADX_Min)             bs += 8;
   if(diP > diM)                  bs += 7;

   //--- Bear score
   int ss = 0;
   if(htfBear)                    ss += 15;
   if(microBear)                  ss += 10;
   if(C1 < ema200)                ss += 5;
   if(mom < 0)                    ss += 8;
   if(roc < 0)                    ss += 7;
   if(rsi < 50 && rsi > 30)      ss += 10;
   if(volRatio > VolMult)         ss += 10;
   if(volRatio > 2.0)             ss += 5;
   if(C1 < O1)                   ss += 8;
   if(adx > ADX_Min)             ss += 8;
   if(diM > diP)                  ss += 7;

   int h = TimeHour(TimeGMT());
   bool inLondonOpen = (h >= London_Open && h < London_Open + 3);
   bool inNYOpen     = (h >= NY_Open     && h < NY_Open + 2);

   //--- Strategy 1: London Breakout
   if(UseLondonBO && g_RangeSet && inLondonOpen)
     {
      if(C1 > g_RangeHigh && volRatio > VolMult && bs >= MinScore - 10)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      if(C1 < g_RangeLow && volRatio > VolMult && ss >= MinScore - 10)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   //--- Strategy 2: Trend Pullback
   if(UseTrendPull)
     {
      bool bullZone = (C1 >= ema21 * 0.9985 && C1 <= ema50 * 1.002);
      bool bearZone = (C1 <= ema21 * 1.0015 && C1 >= ema50 * 0.998);

      if(htfBull && microBull && bullZone && rsi > 30 && rsi < 70 && bs >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      if(htfBear && microBear && bearZone && rsi > 30 && rsi < 70 && ss >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(-1);
        }
     }

   //--- Strategy 3: NY Momentum
   if(UseNYMomentum && inNYOpen)
     {
      if(htfBull && C1 > ema50 && mom > 0 && roc > 0 &&
         volRatio > 1.5 && adx > ADX_Min && diP > diM && bs >= MinScore)
        {
         g_LastSignalBars = Bars;
         return(1);
        }
      if(htfBear && C1 < ema50 && mom < 0 && roc < 0 &&
         volRatio > 1.5 && adx > ADX_Min && diM > diP && ss >= MinScore)
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
      tp    = NormalizeDouble(entry + atr * SL_Mult * MinRR, digits);

      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double mid   = (g_RangeHigh + g_RangeLow) / 2.0;
         double rng   = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(mid - atr * 0.5, digits);
         tp = NormalizeDouble(g_RangeHigh + rng * LB_TPMult, digits);
        }
      otype = OP_BUY;
     }
   else
     {
      entry = bid;
      sl    = NormalizeDouble(entry + atr * SL_Mult, digits);
      tp    = NormalizeDouble(entry - atr * SL_Mult * MinRR, digits);

      if(g_RangeSet && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double mid   = (g_RangeHigh + g_RangeLow) / 2.0;
         double rng   = g_RangeHigh - g_RangeLow;
         sl = NormalizeDouble(mid + atr * 0.5, digits);
         tp = NormalizeDouble(g_RangeLow - rng * LB_TPMult, digits);
        }
      otype = OP_SELL;
     }

   //--- Validate R:R
   double riskPts   = MathAbs(entry - sl);
   double rewardPts = MathAbs(tp    - entry);
   if(riskPts <= 0 || (rewardPts / riskPts) < MinRR)
     {
      Print("GoldMaster: Skipped trade - R:R too low");
      return;
     }

   //--- Position size using tick value (works correctly for XAUUSD)
   double riskUSD   = AccountEquity() * RiskPct / 100.0;
   double tickSz    = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tickVal   = MarketInfo(Symbol(), MODE_TICKVALUE);

   if(tickSz <= 0 || tickVal <= 0)
     {
      Print("GoldMaster: Tick data error - cannot calculate lot size");
      return;
     }

   double slTicks = riskPts / tickSz;
   double lots    = riskUSD / (slTicks * tickVal);

   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   double lotMin  = MarketInfo(Symbol(), MODE_MINLOT);
   double lotMax  = MarketInfo(Symbol(), MODE_MAXLOT);
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(lotMin, MathMin(lotMax, lots));
   lots = NormalizeDouble(lots, 2);

   if(lots <= 0)
     {
      Print("GoldMaster: Lot size is 0 - skipping");
      return;
     }

   //--- Send order
   string cmt = (dir == 1) ? "GMP BUY" : "GMP SELL";
   color  clr = (dir == 1) ? clrLime   : clrRed;

   int ticket = OrderSend(Symbol(), otype, lots, entry, 3, sl, tp, cmt, Magic, 0, clr);

   if(ticket < 0)
     {
      int err = GetLastError();
      Print("GoldMaster: OrderSend failed. Error=", err);
      return;
     }

   g_TodayTrades++;
   Print("GoldMaster: Order placed. Ticket=", ticket,
         " Dir=", (dir==1?"BUY":"SELL"),
         " Entry=", DoubleToStr(entry, digits),
         " SL=", DoubleToStr(sl, digits),
         " TP=", DoubleToStr(tp, digits),
         " Lots=", DoubleToStr(lots, 2));
  }

//+------------------------------------------------------------------+
//| Manage open trades - trailing stop + partial close               |
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
      int    digits    = (int)MarketInfo(Symbol(), MODE_DIGITS);
      double bid       = MarketInfo(Symbol(), MODE_BID);
      double ask       = MarketInfo(Symbol(), MODE_ASK);
      double lotStep   = MarketInfo(Symbol(), MODE_LOTSTEP);
      double lotMin    = MarketInfo(Symbol(), MODE_MINLOT);

      if(OrderType() == OP_BUY)
        {
         double profR = (initRisk > 0) ? (bid - openPx) / initRisk : 0;

         //--- Breakeven at 1R
         if(profR >= 1.0 && curSL < openPx)
           {
            double be = NormalizeDouble(openPx + MarketInfo(Symbol(), MODE_POINT), digits);
            bool modOk = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!modOk) Print("GoldMaster: BE modify failed. Err=", GetLastError());
           }

         //--- Partial close at 1.5R
         if(UsePartial && profR >= PartialR && StringFind(OrderComment(), "PC") < 0)
           {
            double cv = NormalizeDouble(OrderLots() * PartialPct / 100.0, 2);
            cv = MathFloor(cv / lotStep) * lotStep;
            if(cv >= lotMin && OrderLots() > cv + lotMin)
              {
               if(OrderClose(OrderTicket(), cv, bid, 3, clrYellow))
                  Print("GoldMaster: Partial close done. Lots=", cv);
              }
           }

         //--- Trail
         if(UseTrail && profR >= TrailStartR)
           {
            double newSL = NormalizeDouble(bid - atr * TrailATRMult, digits);
            if(newSL > curSL && newSL > openPx)
              {
               bool modOk = OrderModify(OrderTicket(), openPx, newSL, curTP, 0, clrCyan);
               if(!modOk) Print("GoldMaster: Trail modify failed. Err=", GetLastError());
              }
           }
        }

      if(OrderType() == OP_SELL)
        {
         double profR = (initRisk > 0) ? (openPx - ask) / initRisk : 0;

         //--- Breakeven at 1R
         if(profR >= 1.0 && (curSL == 0 || curSL > openPx))
           {
            double be = NormalizeDouble(openPx - MarketInfo(Symbol(), MODE_POINT), digits);
            bool modOk = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!modOk) Print("GoldMaster: BE modify failed. Err=", GetLastError());
           }

         //--- Partial close at 1.5R
         if(UsePartial && profR >= PartialR && StringFind(OrderComment(), "PC") < 0)
           {
            double cv = NormalizeDouble(OrderLots() * PartialPct / 100.0, 2);
            cv = MathFloor(cv / lotStep) * lotStep;
            if(cv >= lotMin && OrderLots() > cv + lotMin)
              {
               if(OrderClose(OrderTicket(), cv, ask, 3, clrYellow))
                  Print("GoldMaster: Partial close done. Lots=", cv);
              }
           }

         //--- Trail
         if(UseTrail && profR >= TrailStartR)
           {
            double newSL = NormalizeDouble(ask + atr * TrailATRMult, digits);
            if(curSL == 0 || (newSL < curSL && newSL < openPx))
              {
               bool modOk = OrderModify(OrderTicket(), openPx, newSL, curTP, 0, clrCyan);
               if(!modOk) Print("GoldMaster: Trail modify failed. Err=", GetLastError());
              }
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Build London pre-market range                                     |
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
      datetime bt = iTime(NULL, 0, i);
      int bh = TimeHour(bt);
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
//| Count this EA's open orders                                       |
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
//| Dashboard comment on chart                                        |
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
                ? DoubleToStr(g_RangeLow,2) + " to " + DoubleToStr(g_RangeHigh,2)
                : "Building...";

   string txt = "GoldMaster Pro v3.0\n"
              + "Equity:  $" + DoubleToStr(eq, 2) + "\n"
              + "Day P&L: " + DoubleToStr(dailyDD, 2) + "%\n"
              + "Total DD: " + DoubleToStr(totalDD, 2) + "%\n"
              + "Trades: " + IntegerToString(g_TodayTrades) + "/" + IntegerToString(MaxDailyTrades) + "\n"
              + "Open: " + IntegerToString(OpenOrderCount()) + "\n"
              + "Range: " + rng + "\n"
              + "Status: " + st;

   Comment(txt);
  }
//+------------------------------------------------------------------+
