# Telegram Setup — 3 Minutes

## Step 1 — Create your bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name: e.g. `Lucid25K Signal Bot`
4. Choose a username: e.g. `lucid25k_signals_bot`
5. BotFather replies with your **bot token** — looks like:
   ```
   7123456789:AABBccDDeeFFggHHiiJJkkLLmmNNooP
   ```
   Copy it.

## Step 2 — Get your Chat ID

1. Search Telegram for **@userinfobot**
2. Send `/start`
3. It replies with your **Id** number — looks like:
   ```
   Id: 123456789
   ```
   Copy it.

## Step 3 — Add to .env

Open the `.env` file in the bot folder:

```
TELEGRAM_BOT_TOKEN=7123456789:AABBccDDeeFFggHHiiJJkkLLmmNNooP
TELEGRAM_CHAT_ID=123456789
```

## Step 4 — Test

```bash
source .env
python scanner.py
```

You should receive a message on Telegram within seconds.

---

## What messages you'll receive

**No signal day:**
```
📋 Daily Signal Scan — Mon Jan 06, 2025  4:15 PM ET

⚪ MNQ — No signal
  IBS: 0.512  |  Band: 21,340.00  |  Close: 21,580.25

⚪ MGC — No signal
  IBS: 0.448  |  Band: 2,618.40   |  Close: 2,664.30

No actionable signals today. Stay patient.
─────────────────────────────────────────
Account: Lucid 25K  |  Risk/trade: 0.5%
Daily loss limit: $500  |  Trailing DD limit: $1,000
```

**Signal day:**
```
📋 Daily Signal Scan — Tue Jan 07, 2025  4:15 PM ET

🟢 MNQ — LONG SIGNAL
  Entry:      near 21,200.00 at tomorrow's open
  Stop:       20,940.00  (1.5× ATR)
  Contracts:  1  (risk ≈ $104)
  IBS:        0.187  (threshold 0.30)
  Band:       21,340.00  |  SMA300: 20,110.50

⚪ MGC — No signal
  ...
```

**When you get a LONG signal:**
- Enter at market open next morning (or limit near prior close)
- Your stop is already calculated — place it immediately
- Exit when next signal shows FLAT (usually 1-5 days)
