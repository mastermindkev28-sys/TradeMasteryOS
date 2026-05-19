//+------------------------------------------------------------------+
//| GoldMaster Pro EA v6.2 — Unlimited Runner / Compounding         |
//| XAUUSD only                                                      |
//|                                                                   |
//| PHILOSOPHY: No fixed profit target. Trades close via trail only. |
//|   - Entry -> SL hit = full loss (controlled risk)                |
//|   - Entry -> 1R profit -> SL moves to breakeven (can't lose)     |
//|   - Entry -> 2R profit -> Chandelier trail activates             |
//|     Trail = price - 2.5xATR. Ratchets up as price runs.         |
//|     Trade closes ONLY when price reverses into the trail.        |
//|   - No hard TP. A $500 day can become $5,000 if gold trends.    |
//|                                                                   |
//| COMPOUNDING: uses AccountBalance() for sizing.                   |
//|   $50K -> $500/trade. $100K -> $1,000/trade. Scales itself.     |
//|                                                                   |
//| STRATEGIES                                                        |
//|   1. Asian Range Breakout  (07:00-10:00 UTC)                     |
//|   2. H4 EMA Trend Pullback (London + NY)                         |
//|   3. NY Momentum           (13:30-16:00 UTC)                     |
//|   4. H4 EMA50 Structure Bounce                                   |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property link      ""
#property version   "6.20"
#property strict

//=== RISK & COMPOUNDING ============================================
extern double RiskPct         = 1.0;   // % of balance per trade (auto-compounds)
extern double MaxDailyLossPct = 3.0;   // Prop firm safe (FTMO limit: 5%)
extern double MaxTotalDDPct   = 6.0;   // Prop firm safe (FTMO limit: 10%)
extern int    MaxDailyTrades  = 3;     // Max trades per day

//=== TRADE MANAGEMENT — LET WINNERS RUN ===========================
extern double SL_ATR          = 1.2;   // Initial stop = 1.2x ATR from entry
extern double BE_R            = 1.0;   // Move SL to breakeven at 1R (capital guard)
extern double TrailActivateR  = 2.0;   // Trail activates when 2R in profit
extern double TrailATR        = 2.5;   // Trail width = 2.5x ATR (wide, lets it run)
extern bool   UseBreakeven    = true;  // Move SL to entry at 1R (capital guard)
extern bool   UseTrail        = true;  // Trail-only exit — no fixed TP ceiling

//=== REGIME FILTERS ================================================
extern int    ATR_Period       = 14;
extern double MinATR           = 1.0;  // Skip dead sessions (< $1 ATR)
extern double MaxATR           = 10.0; // Skip news spikes (> $10 ATR)
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
extern int    Asian_Start      = 1;
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

double   g_RangeHigh;
double   g_RangeLow;
bool     g_RangeReady;
datetime g_RangeStamp;

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
   g_LastSigBars = -1;

   double risk = AccountBalance() * RiskPct / 100.0;
   Print("GoldMaster v6.1 | Bal=$", DoubleToStr(AccountBalance(), 2),
         " | Risk=$",       DoubleToStr(risk, 2),
         " | Trail @2R | Hard TP @8R=$", DoubleToStr(risk * 8.0, 2));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { Comment(""); }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManageTrades();  // Runs every tick: breakeven + trail updates

   static datetime lastBar = 0;
   datetime curBar = iTime(NULL, 0, 0);
   if(curBar == lastBar)
     {
      if(ShowDash) Dashboard();
      return;
     }
   lastBar = curBar;

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
   if(!CanTrade())       return;
   if(LiveOrderCount() > 0) return;

   int sig = GenerateSignal();
   if(sig != 0) ExecuteOrder(sig);
  }

//+------------------------------------------------------------------+
//| Risk Gate                                                         |
//+------------------------------------------------------------------+
bool CanTrade()
  {
   if(g_Suspended) return(false);
   int dow = DayOfWeek();
   if(dow == 0 || dow == 6) return(false);

   int h = TimeHour(TimeGMT());
   if(h >= 21 || h < Asian_Start) return(false);

   if(g_DayTrades >= MaxDailyTrades) return(false);

   double dayLoss = AccountBalance() - g_DayStartBal;
   if(dayLoss < -(g_DayStartBal * MaxDailyLossPct / 100.0))
     {
      g_Suspended = true; g_SuspendMsg = "Daily loss limit";
      Alert("GoldMaster: Daily loss limit hit. Suspended.");
      return(false);
     }

   double ddPct = (g_StartBal > 0) ? (AccountBalance() - g_StartBal) / g_StartBal * 100.0 : 0;
   if(ddPct < -MaxTotalDDPct)
     {
      g_Suspended = true; g_SuspendMsg = "Max drawdown hit";
      Alert("GoldMaster: MAX DRAWDOWN. EA stopped.");
      return(false);
     }

   return(true);
  }

//+------------------------------------------------------------------+
//| SIGNAL ENGINE — returns +1 BUY, -1 SELL, 0 none                 |
//+------------------------------------------------------------------+
int GenerateSignal()
  {
   if(Bars == g_LastSigBars) return(0);

   double atr = iATR(NULL, 0, ATR_Period, 1);
   if(atr < MinATR || atr > MaxATR) return(0);

   //--- Price action (M15)
   double c1  = iClose(NULL, 0, 1);
   double o1  = iOpen(NULL,  0, 1);
   double h1p = iHigh(NULL,  0, 1);
   double l1  = iLow(NULL,   0, 1);

   //--- M15 EMAs
   double e9   = iMA(NULL, 0, EMA9,   0, MODE_EMA, PRICE_CLOSE, 1);
   double e21  = iMA(NULL, 0, EMA21,  0, MODE_EMA, PRICE_CLOSE, 1);
   double e50  = iMA(NULL, 0, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double e200 = iMA(NULL, 0, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double rsi  = iRSI(NULL, 0, 14, PRICE_CLOSE, 1);

   //--- H1
   double h1e21  = iMA(NULL, PERIOD_H1, EMA21, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h1e50  = iMA(NULL, PERIOD_H1, EMA50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h1rsi  = iRSI(NULL, PERIOD_H1, 14, PRICE_CLOSE, 1);
   double h1mac  = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_MAIN,   1);
   double h1sig  = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
   double h1mac2 = iMACD(NULL, PERIOD_H1, 12, 26, 9, PRICE_CLOSE, MODE_MAIN,   2);

   //--- H4
   double h4e21  = iMA(NULL, PERIOD_H4, EMA21,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h4e50  = iMA(NULL, PERIOD_H4, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double h4e200 = iMA(NULL, PERIOD_H4, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4adx  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_MAIN,    1);
   double h4diP  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_PLUSDI,  1);
   double h4diM  = iADX(NULL, PERIOD_H4, ADX_Period, PRICE_CLOSE, MODE_MINUSDI, 1);

   //--- D1
   double d1e50  = iMA(NULL, PERIOD_D1, EMA50,  0, MODE_EMA, PRICE_CLOSE, 1);
   double d1e200 = iMA(NULL, PERIOD_D1, EMA200, 0, MODE_EMA, PRICE_CLOSE, 1);
   double d1c1   = iClose(NULL, PERIOD_D1, 1);

   //--- Volume
   double vsum = 0;
   int vi;
   for(vi = 1; vi <= 20; vi++) vsum += (double)iVolume(NULL, 0, vi);
   double vavg  = vsum / 20.0;
   double volR  = (vavg > 0) ? (double)iVolume(NULL, 0, 1) / vavg : 1.0;

   //--- Candle quality
   double body = MathAbs(c1 - o1);
   double rng  = h1p - l1;
   double bPct = (rng > 0) ? body / rng : 0;
   double uwk  = h1p - MathMax(c1, o1);
   double lwk  = MathMin(c1, o1) - l1;
   bool bullBar = (c1 > o1 && bPct >= 0.45);
   bool bearBar = (c1 < o1 && bPct >= 0.45);
   bool pinUp   = (lwk >= body * 2.0 && uwk <= body * 0.5);
   bool pinDown = (uwk >= body * 2.0 && lwk <= body * 0.5);

   //--- Trend alignment
   bool d1Bull = (d1e50 > d1e200 && d1c1 > d1e50);
   bool d1Bear = (d1e50 < d1e200 && d1c1 < d1e50);
   bool h4Bull = (h4e21 > h4e50  && h4e50 > h4e200);
   bool h4Bear = (h4e21 < h4e50  && h4e50 < h4e200);
   bool h1Bull = (h1e21 > h1e50);
   bool h1Bear = (h1e21 < h1e50);
   bool mBull  = (e9 > e21 && e21 > e50);
   bool mBear  = (e9 < e21 && e21 < e50);
   bool adxOk  = (h4adx >= ADX_Min);

   int bullTF = (d1Bull?1:0) + (h4Bull?1:0) + (h1Bull?1:0);
   int bearTF = (d1Bear?1:0) + (h4Bear?1:0) + (h1Bear?1:0);

   int h = TimeHour(TimeGMT());
   bool inLondon  = (h >= London_Open && h < London_Close);
   bool inNY      = (h >= NY_Open     && h < NY_Close);
   bool inLonOpen = (h >= London_Open && h < London_Open + 3);
   bool inNYOpen  = (h >= NY_Open     && h < NY_Open + 3);
   bool inOverlap = (h >= NY_Open     && h < London_Close);

   //--- Composite scores
   int bs = Score(true,  bullTF, adxOk, h4diP, h4diM, h1mac, h1sig, h1mac2,
                  h1rsi, rsi, volR, bullBar, pinUp,  c1, e21, e50, e200, inOverlap);
   int ss = Score(false, bearTF, adxOk, h4diM, h4diP, -h1mac, -h1sig, -h1mac2,
                  100.0-h1rsi, 100.0-rsi, volR, bearBar, pinDown, c1, e21, e50, e200, inOverlap);

   //=================================================================
   //--- STRATEGY 1: ASIAN RANGE BREAKOUT
   //    Gold compresses during Asia then explodes at London open.
   //    Structural SL below/above range = tight stop, explosive TP.
   //=================================================================
   if(UseAsianBO && g_RangeReady && inLonOpen)
     {
      double rngSz    = g_RangeHigh - g_RangeLow;
      bool validRange = (rngSz >= atr * 0.5 && rngSz <= atr * 4.0);

      if(validRange)
        {
         if(c1 > g_RangeHigh && !h4Bear && bullTF >= 2 && volR >= 1.3 && bs >= MinScore-10)
           { g_LastSigBars = Bars; return(1);  }
         if(c1 < g_RangeLow  && !h4Bull && bearTF >= 2 && volR >= 1.3 && ss >= MinScore-10)
           { g_LastSigBars = Bars; return(-1); }
        }
     }

   //=================================================================
   //--- STRATEGY 2: H4 EMA TREND PULLBACK
   //    Highest win rate: institutional trend -> pullback -> continuation.
   //    Price dips to EMA21-50 zone then shows reversal confirmation.
   //=================================================================
   if(UseEMAPullback && (inLondon || inNY) && adxOk)
     {
      double zoneTop = h4e21 + atr * 0.4;
      double zoneBot = h4e50 - atr * 0.2;

      if(h4Bull && d1Bull && c1 >= zoneBot && c1 <= zoneTop && c1 > h4e50 &&
         (bullBar || pinUp) && rsi >= 42 && rsi <= 62 && h1mac > h1sig && bs >= MinScore)
        { g_LastSigBars = Bars; return(1); }

      double zBot2 = h4e21 - atr * 0.4;
      double zTop2 = h4e50 + atr * 0.2;

      if(h4Bear && d1Bear && c1 <= zTop2 && c1 >= zBot2 && c1 < h4e50 &&
         (bearBar || pinDown) && rsi >= 38 && rsi <= 58 && h1mac < h1sig && ss >= MinScore)
        { g_LastSigBars = Bars; return(-1); }
     }

   //=================================================================
   //--- STRATEGY 3: NY MOMENTUM CONTINUATION
   //    NY open often extends London trend with heavy institutional flow.
   //    Requires strong trend alignment + volume confirmation.
   //=================================================================
   if(UseNYMomentum && inNYOpen)
     {
      if(h4Bull && h1Bull && mBull && c1 > e21 && volR >= 1.5 &&
         h4diP > h4diM && h1mac > h1sig && rsi >= 50 && rsi <= 72 && bs >= MinScore)
        { g_LastSigBars = Bars; return(1); }

      if(h4Bear && h1Bear && mBear && c1 < e21 && volR >= 1.5 &&
         h4diM > h4diP && h1mac < h1sig && rsi >= 28 && rsi <= 50 && ss >= MinScore)
        { g_LastSigBars = Bars; return(-1); }
     }

   //=================================================================
   //--- STRATEGY 4: H4 EMA50 STRUCTURE BOUNCE
   //    The H4 EMA50 is a major institutional reference on gold.
   //    Tests of it with rejection candles in trend = high probability.
   //=================================================================
   if(UseStructBounce && (inLondon || inNY) && adxOk)
     {
      double dist = MathAbs(c1 - h4e50);
      if(dist <= atr * 0.6)
        {
         if(d1Bull && h4Bull && c1 > h4e50 && (pinUp || bullBar) &&
            rsi >= 35 && rsi <= 52 && volR >= 1.2 && bs >= MinScore)
           { g_LastSigBars = Bars; return(1); }

         if(d1Bear && h4Bear && c1 < h4e50 && (pinDown || bearBar) &&
            rsi >= 48 && rsi <= 65 && volR >= 1.2 && ss >= MinScore)
           { g_LastSigBars = Bars; return(-1); }
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
//| Composite score 0-100                                            |
//+------------------------------------------------------------------+
int Score(bool isBull, int tfAlign, bool adxOk, double di1, double di2,
          double macd, double msig, double macd2,
          double h1rsi, double mrsi, double volR,
          bool hasBullBar, bool hasPin,
          double price, double e21, double e50, double e200, bool inOverlap)
  {
   int s = 0;
   s += tfAlign * 10;                         // 30 pts: TF alignment
   if(adxOk) s += 8;                          // 8 pts: trend strength
   if(di1 > di2 + 5) s += 7;                  // 7 pts: DI direction

   if(macd > msig) s += 8;                    // 8 pts: MACD aligned
   if(macd > msig && macd > macd2) s += 5;    // 5 pts: MACD accelerating

   if(isBull)
     {
      if(h1rsi >= 45 && h1rsi <= 65) s += 7;
      if(mrsi  >= 42 && mrsi  <= 62) s += 5;
      if(price > e21)  s += 4;
      if(price > e50)  s += 4;
      if(price > e200) s += 4;
     }
   else
     {
      if(h1rsi >= 35 && h1rsi <= 55) s += 7;
      if(mrsi  >= 38 && mrsi  <= 58) s += 5;
      if(price < e21)  s += 4;
      if(price < e50)  s += 4;
      if(price < e200) s += 4;
     }

   if(volR >= 1.5) s += 8;
   else if(volR >= 1.2) s += 4;

   if(hasPin)     s += 10;  // Pin bar: highest quality rejection signal
   if(hasBullBar) s += 6;

   if(inOverlap) s += 5;    // London/NY overlap: peak liquidity bonus

   return(MathMin(100, s));
  }

//+------------------------------------------------------------------+
//| EXECUTE ORDER                                                     |
//+------------------------------------------------------------------+
void ExecuteOrder(int dir)
  {
   double atr  = iATR(NULL, 0, ATR_Period, 1);
   double ask  = MarketInfo(Symbol(), MODE_ASK);
   double bid  = MarketInfo(Symbol(), MODE_BID);
   int    digs = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double tSz  = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tVal = MarketInfo(Symbol(), MODE_TICKVALUE);

   if(tSz <= 0 || tVal <= 0) { Print("GoldMaster: Tick data error."); return; }

   double entry, sl;
   int    otype;

   if(dir == 1)
     {
      entry = ask;
      sl    = NormalizeDouble(entry - atr * SL_ATR, digs);
      otype = OP_BUY;

      //--- Asian BO: structural SL below range low (tighter, higher R potential)
      if(g_RangeReady && TimeHour(TimeGMT()) < London_Open + 3)
         sl = NormalizeDouble(g_RangeLow - atr * 0.3, digs);
     }
   else
     {
      entry = bid;
      sl    = NormalizeDouble(entry + atr * SL_ATR, digs);
      otype = OP_SELL;

      if(g_RangeReady && TimeHour(TimeGMT()) < London_Open + 3)
         sl = NormalizeDouble(g_RangeHigh + atr * 0.3, digs);
     }

   double riskPts = MathAbs(entry - sl);
   if(riskPts <= 0)
     { Print("GoldMaster: SL calc error. Skip."); return; }

   //--- Position size: % of AccountBalance() auto-compounds
   double riskUSD = AccountBalance() * RiskPct / 100.0;
   double lots    = riskUSD / ((riskPts / tSz) * tVal);
   double step    = MarketInfo(Symbol(), MODE_LOTSTEP);
   lots = MathFloor(lots / step) * step;
   lots = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                  MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lots));
   lots = NormalizeDouble(lots, 2);
   if(lots <= 0) { Print("GoldMaster: Lot calc = 0."); return; }

   string cmt   = (dir == 1) ? "GMP61 BUY" : "GMP61 SELL";
   int    ticket = OrderSend(Symbol(), otype, lots, entry, 3, sl, tp, cmt, Magic, 0,
                             (dir == 1 ? clrLime : clrRed));
   if(ticket < 0)
     { Print("GoldMaster: OrderSend failed err=", GetLastError()); return; }

   g_DayTrades++;
   double rr = rewPts / riskPts;
   Print("GoldMaster TRADE | ", (dir==1?"BUY":"SELL"),
         " Lots=",    DoubleToStr(lots, 2),
         " Entry=",   DoubleToStr(entry, digs),
         " SL=",      DoubleToStr(sl,    digs),
         " HardTP=",  DoubleToStr(tp,    digs),
         " R:R=1:",   DoubleToStr(rr,    2),
         " Risk=$",   DoubleToStr(riskUSD, 2),
         " MaxWin=$", DoubleToStr(riskUSD * rr, 2));
  }

//+------------------------------------------------------------------+
//| TRADE MANAGEMENT — runs every tick                               |
//|                                                                   |
//| 1. Breakeven: SL moves to entry at BE_R (1R) — capital guard    |
//| 2. Chandelier trail: activates at TrailActivateR (2R)            |
//|    Trail = current price - (ATR * TrailATR)                      |
//|    Only moves in profitable direction, never backwards            |
//|    Width = 2.5xATR = gives gold room to breathe                  |
//+------------------------------------------------------------------+
void ManageTrades()
  {
   double atr  = iATR(NULL, 0, ATR_Period, 1);
   int    digs = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double bid  = MarketInfo(Symbol(), MODE_BID);
   double ask  = MarketInfo(Symbol(), MODE_ASK);
   double pt   = MarketInfo(Symbol(), MODE_POINT);

   int i;
   for(i = OrdersTotal() - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != Magic)    continue;
      if(OrderSymbol()      != Symbol()) continue;

      double openPx  = OrderOpenPrice();
      double curSL   = OrderStopLoss();
      double curTP   = OrderTakeProfit();
      double initRsk = MathAbs(openPx - curSL);
      if(initRsk <= 0) continue;

      //--------------------------------------------------------------
      if(OrderType() == OP_BUY)
        {
         double profR = (bid - openPx) / initRsk;

         //--- 1. Breakeven: protect capital, never lock in a full loss
         //       after we were 1R in profit
         if(UseBreakeven && profR >= BE_R && curSL < openPx)
           {
            double be = NormalizeDouble(openPx + pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE err=", GetLastError());
           }

         //--- 2. Chandelier trailing stop (activates at 2R, wide 2.5xATR)
         //       SL = current bid - 2.5 x ATR
         //       Never moves SL downward — only ratchets up
         if(UseTrail && profR >= TrailActivateR)
           {
            double trailSL = NormalizeDouble(bid - atr * TrailATR, digs);
            //--- Ensure trail SL is above initial SL (always protective)
            trailSL = MathMax(trailSL, NormalizeDouble(openPx + pt, digs));
            if(trailSL > curSL)
              {
               bool ok = OrderModify(OrderTicket(), openPx, trailSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail err=", GetLastError());
              }
           }
        }

      //--------------------------------------------------------------
      if(OrderType() == OP_SELL)
        {
         double profR = (openPx - ask) / initRsk;

         //--- 1. Breakeven
         if(UseBreakeven && profR >= BE_R && (curSL == 0 || curSL > openPx))
           {
            double be = NormalizeDouble(openPx - pt, digs);
            bool ok = OrderModify(OrderTicket(), openPx, be, curTP, 0, clrBlue);
            if(!ok) Print("GoldMaster: BE err=", GetLastError());
           }

         //--- 2. Chandelier trailing stop
         if(UseTrail && profR >= TrailActivateR)
           {
            double trailSL = NormalizeDouble(ask + atr * TrailATR, digs);
            trailSL = MathMin(trailSL, NormalizeDouble(openPx - pt, digs));
            if(curSL == 0 || trailSL < curSL)
              {
               bool ok = OrderModify(OrderTicket(), openPx, trailSL, curTP, 0, clrCyan);
               if(!ok) Print("GoldMaster: Trail err=", GetLastError());
              }
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Build Asian range (01:00-07:00 UTC)                              |
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
      int bh = TimeHour(iTime(NULL, 0, i));
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
void Dashboard()
  {
   double bal   = AccountBalance();
   double eq    = AccountEquity();
   double risk  = bal * RiskPct / 100.0;
   double dayPL = bal - g_DayStartBal;
   double totPL = bal - g_StartBal;
   double ddPct = (g_StartBal > 0) ? (bal - g_StartBal) / g_StartBal * 100.0 : 0;
   double atr   = iATR(NULL, 0, ATR_Period, 1);

   string rng    = g_RangeReady
                 ? DoubleToStr(g_RangeLow,2) + " - " + DoubleToStr(g_RangeHigh,2)
                 : "Building...";
   string regime = (atr < MinATR) ? "DEAD - NO TRADE" :
                   (atr > MaxATR) ? "NEWS SPIKE - NO TRADE" : "OK";
   string status = g_Suspended ? "SUSPENDED: " + g_SuspendMsg :
                   CanTrade()  ? "ACTIVE" : "WAITING";

   double weeklyEV = risk * 1.34 * MaxDailyTrades * 3;

   Comment("GoldMaster Pro v6.1 — Let Winners Run\n"
         + "Balance:  $" + DoubleToStr(bal, 2) + "  Equity: $" + DoubleToStr(eq, 2) + "\n"
         + "Risk/trade: $" + DoubleToStr(risk, 2) + "  Max win: $" + DoubleToStr(risk*HardTP_R,2) + "\n"
         + "Day P&L:  $" + DoubleToStr(dayPL, 2) + "\n"
         + "Total P&L: $" + DoubleToStr(totPL, 2) + "  DD: " + DoubleToStr(MathAbs(ddPct),2) + "%\n"
         + "Trades:   " + IntegerToString(g_DayTrades) + "/" + IntegerToString(MaxDailyTrades) + "\n"
         + "Open:     " + IntegerToString(LiveOrderCount()) + "\n"
         + "ATR:      $" + DoubleToStr(atr,2) + " [" + regime + "]\n"
         + "Range:    " + rng + "\n"
         + "Weekly EV: ~$" + DoubleToStr(weeklyEV, 0) + "\n"
         + "Status:   " + status + "\n"
         + "BE@1R | Trail@2R width=" + DoubleToStr(TrailATR,1) + "xATR | HardTP@8R");
  }
//+------------------------------------------------------------------+
