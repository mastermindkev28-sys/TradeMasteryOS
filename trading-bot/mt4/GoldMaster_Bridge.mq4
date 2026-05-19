//+------------------------------------------------------------------+
//|  GoldMaster Bridge — MT4 File Bridge                             |
//|  Reads order signals from Python webhook server via JSON file.   |
//|  Run alongside GoldMasterEA.mq4 OR as standalone auto-trader.   |
//+------------------------------------------------------------------+
#property copyright "GoldMaster Pro"
#property version   "1.00"
#property strict

extern string SignalsDir    = "C:\\GoldMaster\\signals\\";
extern string OrdersFile    = "orders.json";
extern string StatusFile    = "mt4_status.json";
extern int    CheckInterval = 5;        // Seconds between file checks
extern int    MagicNumber   = 20250519;
extern bool   AutoTrade     = true;     // Execute orders automatically
extern int    Slippage      = 3;
extern string WebhookURL    = "";       // Optional: POST status back to bridge

// State
datetime lastFileCheck = 0;
string   lastOrderId   = "";

int OnInit()
{
    EventSetTimer(CheckInterval);
    Print("GoldMaster Bridge started. Watching: ", SignalsDir + OrdersFile);
    WriteStatus();
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    EventKillTimer();
}

void OnTimer()
{
    WriteStatus();
    ReadAndExecuteOrder();
}

void OnTick()
{
    // Also check on tick in case timer is slow
    if (TimeCurrent() - lastFileCheck < CheckInterval) return;
    lastFileCheck = TimeCurrent();
    ReadAndExecuteOrder();
}

void ReadAndExecuteOrder()
{
    string filePath = SignalsDir + OrdersFile;

    int handle = FileOpen(filePath, FILE_READ | FILE_TXT | FILE_ANSI);
    if (handle == INVALID_HANDLE) return;

    string content = "";
    while (!FileIsEnding(handle)) {
        content += FileReadString(handle);
    }
    FileClose(handle);

    if (StringLen(content) < 10) return;

    // Simple JSON parsing (no lib needed for flat JSON)
    string orderId  = ExtractJsonString(content, "id");
    string action   = ExtractJsonString(content, "action");
    string symbol   = ExtractJsonString(content, "symbol");
    string status   = ExtractJsonString(content, "status");

    // Skip if already processed or not pending
    if (orderId == lastOrderId)  return;
    if (status  != "PENDING")    return;
    if (action  != "BUY" && action != "SELL") return;
    if (symbol  != Symbol()) return;

    double price    = StringToDouble(ExtractJsonString(content, "price"));
    double sl       = StringToDouble(ExtractJsonString(content, "sl"));
    double tp       = StringToDouble(ExtractJsonString(content, "tp1"));
    double lotSize  = StringToDouble(ExtractJsonString(content, "lot_size"));

    if (price <= 0 || sl <= 0 || tp <= 0 || lotSize <= 0) {
        Print("Bridge: Invalid order params");
        return;
    }

    lastOrderId = orderId;

    if (!AutoTrade) {
        Alert("GoldMaster Signal: ", action, " ", symbol, " @ ", price,
              " SL:", sl, " TP:", tp, " Lots:", lotSize);
        return;
    }

    // Execute
    int orderType = (action == "BUY") ? OP_BUY : OP_SELL;
    double execPrice = (action == "BUY") ? MarketInfo(symbol, MODE_ASK)
                                         : MarketInfo(symbol, MODE_BID);

    int ticket = OrderSend(symbol, orderType, lotSize, execPrice, Slippage,
                           sl, tp, "GoldMaster Bridge | ID:" + orderId,
                           MagicNumber, 0,
                           (action == "BUY") ? clrLime : clrRed);

    if (ticket > 0) {
        Print("Bridge: Order executed. Ticket:", ticket, " ", action, " ", lotSize, " lots");
        // Mark as executed by renaming file
        MarkOrderExecuted(filePath, ticket);
    } else {
        Print("Bridge: OrderSend failed. Error:", GetLastError());
    }
}

void MarkOrderExecuted(string filePath, int ticket)
{
    int handle = FileOpen(filePath, FILE_READ | FILE_TXT | FILE_ANSI);
    if (handle == INVALID_HANDLE) return;
    string content = "";
    while (!FileIsEnding(handle)) content += FileReadString(handle);
    FileClose(handle);

    // Replace PENDING with EXECUTED
    StringReplace(content, "\"status\":\"PENDING\"", "\"status\":\"EXECUTED\"");
    content += "\n// ticket:" + IntegerToString(ticket);

    handle = FileOpen(filePath, FILE_WRITE | FILE_TXT | FILE_ANSI);
    if (handle != INVALID_HANDLE) {
        FileWriteString(handle, content);
        FileClose(handle);
    }
}

void WriteStatus()
{
    string filePath = SignalsDir + StatusFile;
    int handle = FileOpen(filePath, FILE_WRITE | FILE_TXT | FILE_ANSI);
    if (handle == INVALID_HANDLE) return;

    double equity   = AccountEquity();
    double balance  = AccountBalance();
    double dd       = (balance > 0) ? (balance - equity) / balance * 100 : 0;
    int    openTrd  = 0;
    for (int i = 0; i < OrdersTotal(); i++) {
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
            OrderMagicNumber() == MagicNumber) openTrd++;
    }

    string json = StringFormat(
        "{\"equity\":%.2f,\"balance\":%.2f,\"drawdown_pct\":%.3f,"
        "\"open_trades\":%d,\"symbol\":\"%s\","
        "\"spread\":%.1f,\"auto_trade\":%s,"
        "\"status\":\"connected\",\"platform\":\"MT4\","
        "\"timestamp\":\"%s\"}",
        equity, balance, dd, openTrd, Symbol(),
        MarketInfo(Symbol(), MODE_SPREAD) * 0.1,
        AutoTrade ? "true" : "false",
        TimeToStr(TimeCurrent(), TIME_DATE | TIME_SECONDS)
    );

    FileWriteString(handle, json);
    FileClose(handle);
}

// ─────────────────────────────────────────────
// Simple JSON string extractor
// ─────────────────────────────────────────────
string ExtractJsonString(string json, string key)
{
    string searchKey = "\"" + key + "\"";
    int keyPos = StringFind(json, searchKey);
    if (keyPos < 0) return "";

    int colonPos = StringFind(json, ":", keyPos);
    if (colonPos < 0) return "";

    // Skip whitespace after colon
    int valStart = colonPos + 1;
    while (valStart < StringLen(json) &&
           (StringGetChar(json, valStart) == ' ' || StringGetChar(json, valStart) == '\t'))
        valStart++;

    if (valStart >= StringLen(json)) return "";

    // Check if quoted string
    if (StringGetChar(json, valStart) == '"') {
        int valEnd = StringFind(json, "\"", valStart + 1);
        if (valEnd < 0) return "";
        return StringSubstr(json, valStart + 1, valEnd - valStart - 1);
    }

    // Numeric value
    int valEnd = valStart;
    while (valEnd < StringLen(json)) {
        uchar c = StringGetChar(json, valEnd);
        if (c == ',' || c == '}' || c == '\n' || c == '\r') break;
        valEnd++;
    }
    return StringSubstr(json, valStart, valEnd - valStart);
}
//+------------------------------------------------------------------+
