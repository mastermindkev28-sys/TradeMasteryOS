//+------------------------------------------------------------------+
//| GoldMaster Pro EA v6.0 — Compounding Edition                     |
//| XAUUSD only | Auto-compounds with fixed % equity risk             |
//|                                                                   |
//| TRADE MANAGEMENT                                                  |
//|   50% close at 2R (lock profit) + trail runner to 5R+            |
//|   Breakeven at 1.2R (protect after partial hits)                 |
//|                                                                   |
//| STRATEGIES                                                        |
//|   1. Asian Session Breakout  (07:00-10:00 UTC)                   |
//|   2. H4 EMA Trend Pullback   (London + NY)                       |
//|   3. NY Momentum             (13:30-16:00 UTC)                   |
//|   4. H4 EMA50 Structure Bounce (London + NY)                     |
//|                                                                   |
//| REGIME FILTER                                                     |
//|   D1 + H4 trend must align | ADX > 22 | ATR in normal range      |
//|                                                                   |
//| COMPOUNDING MATH at 55% WR                                        |
//|   Avg win: 50%x2R + 50%x4R = 3R net per full trade               |
//|   EV: 0.55x3R - 0.45x1R = 1.2R per trade                        |
//|   $50K @ 1%: $600 EV per trade x 3/week = ~$1800/week            |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property link      ""
#property version   "6.00"
#property strict

//=== RISK & COMPOUNDING ============================================
extern double RiskPct         = 1.0;   // % of balance per trade (auto-compounds)
extern double MaxDailyLossPct = 3.0;   // Prop firm safe (FTMO: 5%)
extern double MaxTotalDDPct   = 6.0;   // Prop firm safe (FTMO: 10%)
extern int    MaxDailyTrades  = 3;     // Quality over quantity

//=== TRADE MANAGEMENT ==============================================
extern double SL_ATR          = 1.2;   // Stop loss = 1.2x ATR
extern double TP1_R           = 2.0;   // Partial close at 2R profit
extern double TP1_Pct         = 50.0;  // % of position to close at TP1
extern double TP2_ATR         = 5.0;   // Runner target = 5x ATR
extern double BE_R            = 1.2;   // Move SL to breakeven at 1.2R
extern double TrailR          = 1.5;   // Trail runner: keep 1.5R buffer below price
extern bool   UsePartialClose = true;
extern bool   UseTrailRunner  = true;
extern bool   UseBreakeven    = true;

//=== REGIME FILTERS ================================================
extern int    ATR_Period       = 14;
extern double MinATR           = 1.0;  // Skip dead sessions (< $1 volatility)
extern double MaxATR           = 10.0; // Skip news spikes (> $10 volatility)
extern int    ADX_Period       = 14;
extern int    ADX_Min          = 22;   // Require trending market
extern int    MinScore         = 70;   // Signal quality gate (0-100)

//=== EMA PERIODS ===================================================
extern int    EMA9             = 9;
extern int    EMA21            = 21;
extern int    EMA50            = 50;
extern int    EMA200           = 200;

//=== SESSION HOURS (UTC) ===========================================
extern int    London_Open      = 7;
extern int    London_Close     = 16;
extern int    NY_Open          = 13;
extern int    NY_Close         = 21;
extern int    Asian_Start      = 1;    // Range builds 01:00-07:00 UTC
extern int    Asian_End        = 7;

//=== STRATEGY SWITCHES =============================================
extern bool   UseAsianBO       = true;
extern bool   UseEMAPullback   = true;
extern bool   UseNYMomentum    = true;
extern bool   UseStructBounce  = true;

//=== DISPLAY & MAGIC ===============================================
extern bool   ShowDash         = true;
extern int    Magic            = 20250519;

//+------------------------------------------------------------------+
//| GLOBALS                                                           |
//+------------------------------------------------------------------+
double   g_StartBal;
double   g_DayStartBal;
int      g_DayTrades;
datetime g_DayStamp;
bool     g_Suspended;
string   g_SuspendMsg;

// Asian range
double   g_RangeHigh;
double   g_RangeLow;
bool     g_RangeReady;
datetime g_RangeStamp;

// Partial close tracking — store tickets of trades already partially closed
int      g_PartTix[200];
int      g_PartCount;

// Bar guard
int      g_LastSigBars;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_StartBal    = AccountBalance();
   g_DayStartBal = AccountBalance();
   g_DayTrades   = 0;
   g_DayStamp    = iTime(NULL, PERIOD_D1, 0);
   g_Suspended   = false;
   g_SuspendMsg  = "";
   g_RangeHigh   = 0;
   g_RangeLow    = 0;
   g_RangeReady  = false;
   g_RangeStamp  = 0;
   g_PartCount   = 0;
   g_LastSigBars = -1;

   double risk   = AccountBalance() * RiskPct / 100.0;
   double tp1win = risk * TP1_R * (TP1_Pct / 100.0);
   double runwin = risk * TP2_ATR / SL_ATR * (1.0 - TP1_Pct / 100.0);
   Print("GoldMaster v6.0 | Bal=$", DoubleToStr(AccountBalance(), 2),
         " | Risk=$", DoubleToStr(risk, 2),
         " | TP1 gain=$", DoubleToStr(tp1win, 2),
         " | Runner tgt=$", DoubleToStr(runwin, 2));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { Comment(""); }

//+------------------------------------------------------------------+
void OnTick()
  {
   //--- Trade management runs every tick for fast breakeven/trail
   ManageTrades();

   //--- Signal logic runs on new bar only
   static datetime lastBar = 0;
   datetime curBar = iTime(NULL, 0, 0);
   if(curBar == lastBar)
     {
      if(ShowDash) Dashboard();
      return;
     }
   lastBar = curBar;

   //--- Daily reset
   datetime today = iTime(NULL, PERIOD_D1, 0);
   if(today != g_DayStamp)
     {
      g_DayStamp    = today;
      g_DayStartBal = AccountBalance();
      g_DayTrades   = 0;
      g_Suspended   = false;
      g_SuspendMsg  = "";
      g_RangeHigh   = 0;
      g_RangeLow    = 0;
      g_RangeReady  = false;
      Print("GoldMaster: Day reset | Bal=$", DoubleToStr(AccountBalance(), 2));
     }

   BuildAsianRange();
   if(!CanTrade())     return;
   if(LiveOrderCount() > 0) return;  // One trade at a time

   int sig = GenerateSignal();
   if(sig != 0) ExecuteOrder(sig);
  }

//+------------------------------------------------------------------+
//| Risk Gate — prop firm hard stops                                  |
//+------------------------------------------------------------------+
bool CanTrade()
  {
   if(g_Suspended) return(false);

   int dow = DayOfWeek();
   if(dow == 0 || dow == 6) return(false);

   int h = TimeHour(TimeGMT());
   if(h >= 21 || h < Asian_Start) return(false);  // Dead zone

   if(g_DayTrades >= MaxDailyTrades) return(false);

   //--- Daily loss hard stop
   double dayLoss = AccountBalance() - g_DayStartBal;
   if(dayLoss < -(g_DayStartBal * MaxDailyLossPct / 100.0))
     {
      g_Suspended = true;
      g_SuspendMsg = "Daily loss limit hit";
      Alert("GoldMaster: Daily loss limit. Suspended for today.");
      return(false);
     }

   //--- Total drawdown hard stop
   double ddPct = (g_StartBal > 0) ? (AccountBalance() - g_StartBal) / g_StartBal * 100.0 : 0;
   if(ddPct < -MaxTotalDDPct)
     {
      g_Suspended = true;
      g_SuspendMsg = "Max drawdown breached";
      Alert("GoldMaster: MAX DRAWDOWN BREACHED. EA stopped.");
      return(false);
     }

   return(true);
  }

//+------------------------------------------------------------------+
//| SIGNAL ENGINE                                                     |
//| Returns +1 = BUY, -1 = SELL, 0 = no trade                       |
//+------------------------------------------------------------------+
int GenerateSignal()
  {
   if(Bars == g_LastSigBars) return(0);

   double atr = iATR(NULL, 0, ATR_Period, 1);
   if(atr < MinATR || atr > MaxATR) return(0);  // Regime: dead or too wild

   //--- Fetch indicators across all used timeframes
   double m15_c1  = iClose(NULL, 0, 1);
   double m15_c2  = iClose(NULL, 0, 2);
   double m15_o1  = iOpen(NULL,  0, 1);
   double m15_h1  = iHigh(NULL,  0, 1);
   double m15_l1  = iLow(NULL,   0, 1);

   double m15_e9   = iMA(NULL, 0, EMA9,   0, MODE_EMA, PRICE_CLOSE, 1);
   double m15_e21  = iMA(NULL, 0, EMA21,  0, MODE_EMA, PRICE_CLOSE, 1);
   double m15_e50  = iMA(NULL, 0, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double m15_e200 = iMA(NULL, 0, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double m15_rsi  = iRSI(NULL, 0, 14, PRICE_CLOSE, 1);

   double h1_e21  = iMA(NULL, PERIOD_H1, EMA21,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h1_e50  = iMA(NULL, PERIOD_H1, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h1_rsi  = iRSI(NULL, PERIOD_H1, 14, PRICE_CLOSE, 1);

   double h4_e21  = iMA(NULL, PERIOD_H4, EMA21,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h4_e50  = iMA(NULL, PERIOD_H4, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h4_e200 = iMA(NULL, PERIOD_H4, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4_adx  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
   double h4_diP  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
   double h4_diM  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);
   double h4_c1   = iClose(NULL, PERIOD_H4, 1);

   double d1_e50  = iMA(NULL, PERIOD_D1, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double d1_e200 = iMA(NULL, PERIOD_D1, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double d1_c1   = iClose(NULL, PERIOD_D1, 1);

   //--- Volume ratio (current vs 20-bar avg)
   double vsum = 0;
   int vi;
   for(vi = 1; vi <= 20; vi++) vsum += (double)iVolume(NULL, 0, vi);
   double vavg     = vsum / 20.0;
   double volRatio = (vavg > 0) ? (double)iVolume(NULL, 0, 1) / vavg : 1.0;

   //--- MACD on H1
   double h1_macd = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_MAIN,   1);
   double h1_sig  = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
   double h1_mac0 = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_MAIN,   2);

   //--- Candle quality
   double body  = MathAbs(m15_c1 - m15_o1);
   double rng   = m15_h1 - m15_l1;
   double bPct  = (rng > 0) ? body / rng : 0;
   double uwk   = m15_h1 - MathMax(m15_c1, m15_o1);  // upper wick
   double lwk   = MathMin(m15_c1, m15_o1) - m15_l1;  // lower wick
   bool bullBar = (m15_c1 > m15_o1 && bPct >= 0.45);
   bool bearBar = (m15_c1 < m15_o1 && bPct >= 0.45);
   bool pinUp   = (lwk >= body * 2.0 && uwk <= body * 0.5);  // hammer
   bool pinDown = (uwk >= body * 2.0 && lwk <= body * 0.5);  // shooting star

   //=================================================================
   //--- TREND FLAGS (3-timeframe alignment)
   //=================================================================
   bool d1Bull  = (d1_e50  > d1_e200  && d1_c1  > d1_e50);
   bool d1Bear  = (d1_e50  < d1_e200  && d1_c1  < d1_e50);

   bool h4Bull  = (h4_e21  > h4_e50   && h4_e50  > h4_e200);
   bool h4Bear  = (h4_e21  < h4_e50   && h4_e50  < h4_e200);
   bool h4DiOk  = (h4_adx  >= ADX_Min);

   bool h1Bull  = (h1_e21  > h1_e50);
   bool h1Bear  = (h1_e21  < h1_e50);

   bool microBull = (m15_e9 > m15_e21 && m15_e21 > m15_e50);
   bool microBear = (m15_e9 < m15_e21 && m15_e21 < m15_e50);

   //--- Full 3-TF alignment
   bool fullBull = (d1Bull && h4Bull && h1Bull);
   bool fullBear = (d1Bear && h4Bear && h1Bear);

   //--- Relaxed alignment (2-of-3 TF)
   int bullTF = (d1Bull?1:0) + (h4Bull?1:0) + (h1Bull?1:0);
   int bearTF = (d1Bear?1:0) + (h4Bear?1:0) + (h1Bear?1:0);

   int h = TimeHour(TimeGMT());
   bool inLondon    = (h >= London_Open  && h < London_Close);
   bool inNY        = (h >= NY_Open      && h < NY_Close);
   bool inLonOpen   = (h >= London_Open  && h < London_Open + 3);
   bool inNYOpen    = (h >= NY_Open      && h < NY_Open + 3);
   bool inOverlap   = (h >= NY_Open      && h < London_Close);  // Best quality

   //=================================================================
   //--- COMPOSITE SCORING (0-100)
   //=================================================================
   int bs = ScoreSetup(true,  bullTF, h4DiOk, h4_diP, h4_diM,
                        h1_macd, h1_sig, h1_mac0, h1_rsi,
                        m15_rsi, volRatio, bullBar, pinUp,
                        m15_c1, m15_e21, m15_e50, m15_e200, atr, inOverlap);

   int ss = ScoreSetup(false, bearTF, h4DiOk, h4_diM, h4_diP,
                        -h1_macd, -h1_sig, -h1_mac0,
                        100.0-h1_rsi, 100.0-m15_rsi, volRatio, bearBar, pinDown,
                        m15_c1, m15_e21, m15_e50, m15_e200, atr, inOverlap);

   //=================================================================
   //--- STRATEGY 1: ASIAN RANGE BREAKOUT
   //    Most reliable gold strategy: range compression -> explosive move
   //    Range 01:00-07:00 UTC, trade break at London open
   //=================================================================
   if(UseAsianBO && g_RangeReady && inLonOpen)
     {
      double rngSize = g_RangeHigh - g_RangeLow;
      bool validRange = (rngSize >= atr * 0.5 && rngSize <= atr * 4.0);

      if(validRange)
        {
         //--- Bullish breakout: close above range high, 2+ TF aligned
         if(m15_c1 > g_RangeHigh && !h4Bear && bullTF >= 2 &&
            volRatio >= 1.3 && bs >= MinScore - 10)
           {
            g_LastSigBars = Bars;
            return(1);
           }
         //--- Bearish breakout: close below range low, 2+ TF aligned
         if(m15_c1 < g_RangeLow && !h4Bull && bearTF >= 2 &&
            volRatio >= 1.3 && ss >= MinScore - 10)
           {
            g_LastSigBars = Bars;
            return(-1);
           }
        }
     }

   //=================================================================
   //--- STRATEGY 2: H4 EMA TREND PULLBACK (highest win rate)
   //    Wait for H4 trend -> pullback to EMA21-50 zone -> continuation
   //    This is the bread-and-butter institutional trade on gold
   //=================================================================
   if(UseEMAPullback && (inLondon || inNY) && h4DiOk)
     {
      //--- Bull: H4 uptrend, price pulled back to EMA21-50 zone
      double h4BullZoneTop = h4_e21 + atr * 0.4;
      double h4BullZoneBot = h4_e50 - atr * 0.2;

      if(h4Bull && d1Bull &&
         m15_c1 >= h4BullZoneBot && m15_c1 <= h4BullZoneTop &&
         m15_c1 > h4_e50 &&
         (bullBar || pinUp) && m15_rsi >= 42 && m15_rsi <= 62 &&
         h1_macd > h1_sig && bs >= MinScore)
        {
         g_LastSigBars = Bars;
         return(1);
        }

      //--- Bear: H4 downtrend, price pulled back to EMA21-50 zone
      double h4BearZoneBot = h4_e21 - atr * 0.4;
      double h4BearZoneTop = h4_e50 + atr * 0.2;

      if(h4Bear && d1Bear &&
         m15_c1 <= h4BearZoneTop && m15_c1 >= h4BearZoneBot &&
         m15_c1 < h4_e50 &&
         (bearBar || pinDown) && m15_rsi >= 38 && m15_rsi <= 58 &&
         h1_macd < h1_sig && ss >= MinScore)
        {
         g_LastSigBars = Bars;
         return(-1);
        }
     }

   //=================================================================
   //--- STRATEGY 3: NY MOMENTUM (high-velocity continuation)
   //    NY open often continues London trend with strong volume
   //    Only trade when London trend was clear (h4 + h1 aligned)
   //=================================================================
   if(UseNYMomentum && inNYOpen)
     {
      bool nyBull = (h4Bull && h1Bull && microBull &&
                     m15_c1 > m15_e21 &&
                     volRatio >= 1.5 && h4_diP > h4_diM &&
                     h1_macd > h1_sig && m15_rsi >= 50 && m15_rsi <= 72 &&
                     bs >= MinScore);

      bool nyBear = (h4Bear && h1Bear && microBear &&
                     m15_c1 < m15_e21 &&
                     volRatio >= 1.5 && h4_diM > h4_diP &&
                     h1_macd < h1_sig && m15_rsi >= 28 && m15_rsi <= 50 &&
                     ss >= MinScore);

      if(nyBull) { g_LastSigBars = Bars; return(1);  }
      if(nyBear) { g_LastSigBars = Bars; return(-1); }
     }

   //=================================================================
   //--- STRATEGY 4: H4 EMA50 STRUCTURE BOUNCE
   //    The H4 EMA50 is a major institutional level on gold.
   //    Price tests it -> rejection candle -> continuation of H4 trend
   //=================================================================
   if(UseStructBounce && (inLondon || inNY))
     {
      double distH4E50 = MathAbs(m15_c1 - h4_e50);
      bool nearH4E50 = (distH4E50 <= atr * 0.6);

      if(nearH4E50 && h4DiOk)
        {
         //--- Bounce long off H4 EMA50 in D1 uptrend
         if(d1Bull && h4Bull && m15_c1 > h4_e50 &&
            (pinUp || bullBar) && m15_rsi >= 35 && m15_rsi <= 52 &&
            volRatio >= 1.2 && bs >= MinScore)
           {
            g_LastSigBars = Bars;
            return(1);
           }

         //--- Bounce short off H4 EMA50 in D1 downtrend
         if(d1Bear && h4Bear && m15_c1 < h4_e50 &&
            (pinDown || bearBar) && m15_rsi >= 48 && m15_rsi <= 65 &&
            volRatio >= 1.2 && ss >= MinScore)
           {
            g_LastSigBars = Bars;
            return(-1);
           }
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
//| Composite score for one direction (0-100)                        |
//| Uses all available confluence factors                            |
//+------------------------------------------------------------------+
int ScoreSetup(bool isBull, int tfAlign, bool adxOk,
               double di1, double di2,
               double macdMain, double macdSig, double macdPrev,
               double h1rsi, double m15rsi,
               double volRat, bool hasBullBar, bool hasPin,
               double price, double e21, double e50, double e200,
               double atr, bool inOverlap)
  {
   int s = 0;

   // Timeframe alignment (30 pts)
   s += tfAlign * 10;

   // ADX confirms trend strength (15 pts)
   if(adxOk) s += 10;
   if(di1 > di2 + 5) s += 5;

   // MACD momentum (15 pts)
   if(macdMain > macdSig) s += 10;
   if(macdMain > macdSig && macdMain > macdPrev) s += 5;  // accelerating

   // RSI zone (15 pts)
   if(isBull)
     {
      if(h1rsi >= 45 && h1rsi <= 65) s += 8;
      if(m15rsi >= 42 && m15rsi <= 62) s += 7;
     }
   else
     {
      if(h1rsi >= 35 && h1rsi <= 55) s += 8;
      if(m15rsi >= 38 && m15rsi <= 58) s += 7;
     }

   // Price structure (15 pts)
   if(isBull)
     {
      if(price > e21) s += 5;
      if(price > e50) s += 5;
      if(price > e200) s += 5;
     }
   else
     {
      if(price < e21) s += 5;
      if(price < e50) s += 5;
      if(price < e200) s += 5;
     }

   // Volume (10 pts)
   if(volRat >= 1.5) s += 10;
   else if(volRat >= 1.2) s += 6;

   // Candle quality (10 pts)
   if(hasBullBar) s += 6;
   if(hasPin)     s += 10;  // Pin bar = highest quality rejection

   // Session bonus (5 pts)
   if(inOverlap) s += 5;

   return(MathMin(100, s));
  }

//+------------------------------------------------------------------+
//| EXECUTE ORDER                                                     |
//+------------------------------------------------------------------+
void ExecuteOrder(int dir)
  {
   double atr   = iATR(NULL, 0, ATR_Period, 1);
   double ask   = MarketInfo(Symbol(), MODE_ASK);
   double bid   = MarketInfo(Symbol(), MODE_BID);
   int    digs  = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double tSz   = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tVal  = MarketInfo(Symbol(), MODE_TICKVALUE);

   if(tSz <= 0 || tVal <= 0) { Print("GoldMaster: Tick data error."); return; }

   double entry, sl, tp2;
   int    otype;

   if(dir == 1)
     {
      entry = ask;
      sl    = NormalizeDouble(entry - atr * SL_ATR, digs);
      tp2   = NormalizeDouble(entry + atr * TP2_ATR, digs);
      otype = OP_BUY;

      //--- Asian BO: SL below range low (structural stop)
      if(g_RangeReady && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl  = NormalizeDouble(g_RangeLow - atr * 0.3, digs);
         tp2 = NormalizeDouble(g_RangeHigh + rng * (TP2_ATR / SL_ATR), digs);
        }
     }
   else
     {
      entry = bid;
      sl    = NormalizeDouble(entry + atr * SL_ATR, digs);
      tp2   = NormalizeDouble(entry - atr * TP2_ATR, digs);
      otype = OP_SELL;

      if(g_RangeReady && TimeHour(TimeGMT()) < London_Open + 3)
        {
         double rng = g_RangeHigh - g_RangeLow;
         sl  = NormalizeDouble(g_RangeHigh + atr * 0.3, digs);
         tp2 = NormalizeDouble(g_RangeLow  - rng * (TP2_ATR / SL_ATR), digs);
        }
     }

   //--- Minimum R:R check (must be at least 2:1)
   double riskPts = MathAbs(entry - sl);
   double rewPts  = MathAbs(tp2 - entry);
   if(riskPts <= 0 || rewPts / riskPts < 2.0)
     {
      Print("GoldMaster: R:R below 2.0. Skip.");
      return;
     }

   //--- Position sizing: risk fixed % of balance (auto-compounds)
   double riskUSD = AccountBalance() * RiskPct / 100.0;
   double lots    = riskUSD / ((riskPts / tSz) * tVal);
   double step    = MarketInfo(Symbol(), MODE_LOTSTEP);
   lots = MathFloor(lots / step) * step;
   lots = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                  MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lots));
   lots = NormalizeDouble(lots, 2);
   if(lots <= 0) { Print("GoldMaster: Lot calc=0."); return; }

   string cmt = (dir == 1) ? "GMP6 BUY" : "GMP6 SELL";
   int ticket  = OrderSend(Symbol(), otype, lots, entry, 3, sl, tp2, cmt, Magic, 0,
                           (dir == 1 ? clrLime : clrRed));
   if(ticket < 0)
     {
      Print("GoldMaster: OrderSend failed err=", GetLastError());
      return;
     }

   g_DayTrades++;
   double rr = rewPts / riskPts;
   Print("GoldMaster TRADE | ", (dir==1?"BUY":"SELL"),
         " Lots=",   DoubleToStr(lots, 2),
         " Entry=",  DoubleToStr(entry, digs),
         " SL=",     DoubleToStr(sl, digs),
         " TP=",     DoubleToStr(tp2, digs),
         " R:R=",    DoubleToStr(rr, 2),
         " Risk=$",  DoubleToStr(riskUSD, 2),
         " WinTgt=$",DoubleToStr(riskUSD * rr, 2));
  }

//+------------------------------------------------------------------+
//| TRADE MANAGEMENT                                                  |
//| 1. Breakeven at BE_R                                             |
//| 2. Partial close 50% at TP1 (2R)                                |
//| 3. Trail runner with 1.5R buffer                                 |
//+------------------------------------------------------------------+
void ManageTrades()
  {
   double atr   = iATR(NULL, 0, ATR_Period, 1);
   int    digs  = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double bid   = MarketInfo(Symbol(), MODE_BID);
   double ask   = MarketInfo(Symbol(), MODE_ASK);
   double pt    = MarketInfo(Symbol(), MODE_POINT);

   int i;
   for(i = OrdersTotal() - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != Magic)    continue;
      if(OrderSymbol()      != Symbol()) continue;

      int    tkt     = OrderTicket();
      double openPx  = OrderOpenPrice();
      double curSL   = OrderStopLoss();
      double curTP   = OrderTakeProfit();
      double initRsk = MathAbs(openPx - curSL);
      if(initRsk <= 0) continue;

      bool donePartial = IsPartialDone(tkt);

      if(OrderType() == OP_BUY)
        {
         double profR = (bid - openPx) / initRsk;

         //--- 1. Partial close at TP1 (2R)
         if(UsePartialClose && !donePartial && profR >= TP1_R)
           {
            double closeLots = NormalizeDouble(OrderLots() * TP1_Pct / 100.0, 2);
            double minLot    = MarketInfo(Symbol(), MODE_MINLOT);
            if(closeLots >= minLot)
              {
               bool ok = OrderClose(tkt, closeLots, bid, 3, clrYellow);
               if(ok)
                 {
                  MarkPartialDone(tkt);
                  Print("GoldMaster: Partial close at 2R | Lots=", DoubleToStr(closeLots, 2));
                  //--- Immediately move SL to entry + buffer (protect locked profit)
                  if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                    {
                     double be = NormalizeDouble(openPx + pt * 2, digs);
                     bool m = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
                     if(!m) Print("GoldMaster: BE after partial err=", GetLastError());
                    }
                  continue;
                 }
              }
           }

         //--- 2. Breakeven at BE_R (if partial not yet done)
         if(UseBreakeven && !donePartial && profR >= BE_R && curSL < openPx)
           {
            double be = NormalizeDouble(openPx + pt, digs);
            bool ok = OrderModify(tkt, openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE err=", GetLastError());
           }

         //--- 3. Trail runner (after partial close)
         if(UseTrailRunner && donePartial)
           {
            double trailBuffer = initRsk * TrailR;
            double newSL       = NormalizeDouble(bid - trailBuffer, digs);
            if(newSL > curSL && newSL < bid)
              {
               bool ok = OrderModify(tkt, openPx, newSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail err=", GetLastError());
              }
           }
        }

      if(OrderType() == OP_SELL)
        {
         double profR = (openPx - ask) / initRsk;

         //--- 1. Partial close at TP1 (2R)
         if(UsePartialClose && !donePartial && profR >= TP1_R)
           {
            double closeLots = NormalizeDouble(OrderLots() * TP1_Pct / 100.0, 2);
            double minLot    = MarketInfo(Symbol(), MODE_MINLOT);
            if(closeLots >= minLot)
              {
               bool ok = OrderClose(tkt, closeLots, ask, 3, clrYellow);
               if(ok)
                 {
                  MarkPartialDone(tkt);
                  Print("GoldMaster: Partial close at 2R | Lots=", DoubleToStr(closeLots, 2));
                  if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                    {
                     double be = NormalizeDouble(openPx - pt * 2, digs);
                     bool m = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
                     if(!m) Print("GoldMaster: BE after partial err=", GetLastError());
                    }
                  continue;
                 }
              }
           }

         //--- 2. Breakeven at BE_R
         if(UseBreakeven && !donePartial && profR >= BE_R && (curSL == 0 || curSL > openPx))
           {
            double be = NormalizeDouble(openPx - pt, digs);
            bool ok = OrderModify(tkt, openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE err=", GetLastError());
           }

         //--- 3. Trail runner (after partial close)
         if(UseTrailRunner && donePartial)
           {
            double trailBuffer = initRsk * TrailR;
            double newSL       = NormalizeDouble(ask + trailBuffer, digs);
            if((curSL == 0 || newSL < curSL) && newSL > ask)
              {
               bool ok = OrderModify(tkt, openPx, newSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail err=", GetLastError());
              }
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Build Asian consolidation range (01:00-07:00 UTC)                |
//+------------------------------------------------------------------+
void BuildAsianRange()
  {
   datetime today = iTime(NULL, PERIOD_D1, 0);
   if(today != g_RangeStamp)
     {
      g_RangeStamp = today;
      g_RangeHigh  = 0;
      g_RangeLow   = 999999;
      g_RangeReady = false;
     }

   int h = TimeHour(TimeGMT());
   if(h < Asian_Start || h >= Asian_End) return;

   double hi = 0, lo = 999999;
   int i;
   for(i = 0; i < 100; i++)
     {
      datetime bt = iTime(NULL, 0, i);
      int bh = TimeHour(bt);
      if(bh < Asian_Start || bh >= Asian_End) continue;
      if(iHigh(NULL, 0, i) > hi) hi = iHigh(NULL, 0, i);
      if(iLow(NULL,  0, i) < lo) lo = iLow(NULL,  0, i);
     }

   if(hi > 0 && lo < 999999)
     {
      g_RangeHigh  = hi;
      g_RangeLow   = lo;
      g_RangeReady = true;
     }
  }

//+------------------------------------------------------------------+
//| Partial close tracking                                            |
//+------------------------------------------------------------------+
bool IsPartialDone(int ticket)
  {
   int i;
   for(i = 0; i < g_PartCount; i++)
      if(g_PartTix[i] == ticket) return(true);
   return(false);
  }

void MarkPartialDone(int ticket)
  {
   if(g_PartCount < 200)
     {
      g_PartTix[g_PartCount] = ticket;
      g_PartCount++;
     }
  }

//+------------------------------------------------------------------+
int LiveOrderCount()
  {
   int n = 0, i;
   for(i = 0; i < OrdersTotal(); i++)
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
         OrderMagicNumber() == Magic &&
         OrderSymbol()      == Symbol()) n++;
   return(n);
  }

//+------------------------------------------------------------------+
//| Dashboard — shown on chart                                        |
//+------------------------------------------------------------------+
void Dashboard()
  {
   double bal     = AccountBalance();
   double eq      = AccountEquity();
   double risk    = bal * RiskPct / 100.0;
   double dayPL   = bal - g_DayStartBal;
   double totalPL = bal - g_StartBal;
   double ddPct   = (g_StartBal > 0) ? (bal - g_StartBal) / g_StartBal * 100.0 : 0;
   double atr     = iATR(NULL, 0, ATR_Period, 1);

   string rng = g_RangeReady
              ? DoubleToStr(g_RangeLow, 2) + " - " + DoubleToStr(g_RangeHigh, 2)
              : "Building...";
   string regime = (atr < MinATR) ? "LOW VOL" : (atr > MaxATR) ? "NEWS SPIKE" : "NORMAL";
   string status = g_Suspended  ? "SUSPENDED: " + g_SuspendMsg :
                   CanTrade()   ? "ACTIVE" : "WAITING";

   // Weekly projection
   double weeklyTarget = g_StartBal * 0.04;

   Comment("GoldMaster Pro v6.0 — Compounding Edition\n"
         + "Balance:   $" + DoubleToStr(bal, 2)
         + "  Equity: $" + DoubleToStr(eq, 2) + "\n"
         + "Risk/trade: $" + DoubleToStr(risk, 2)
         + "  (Win@2R: $" + DoubleToStr(risk*2.0*(TP1_Pct/100.0), 2)
         + " locked + runner)\n"
         + "Day P&L:   $" + DoubleToStr(dayPL, 2) + "\n"
         + "Total P&L: $" + DoubleToStr(totalPL, 2)
         + "  DD: " + DoubleToStr(ddPct, 2) + "%\n"
         + "Trades:    " + IntegerToString(g_DayTrades) + "/"
         + IntegerToString(MaxDailyTrades) + " today\n"
         + "Open:      " + IntegerToString(LiveOrderCount()) + "\n"
         + "ATR:       $" + DoubleToStr(atr, 2) + " [" + regime + "]\n"
         + "Range:     " + rng + "\n"
         + "Status:    " + status + "\n"
         + "SL=" + DoubleToStr(SL_ATR,1) + "xATR"
         + "  TP1=" + DoubleToStr(TP1_R,1) + "R(50%)"
         + "  Runner to " + DoubleToStr(TP2_ATR,1) + "xATR"
         + "  Score>=" + IntegerToString(MinScore));
  }
//+------------------------------------------------------------------+
