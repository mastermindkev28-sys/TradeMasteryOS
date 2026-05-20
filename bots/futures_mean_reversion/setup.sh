#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  TradeMasteryOS — One-time setup for Lucid 25K bot
#  Run this once:  bash setup.sh
# ─────────────────────────────────────────────────────────────────
set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

echo ""
echo "=== TradeMastery Futures Bot Setup ==="
echo ""

# 1. Install Python deps
echo "[1/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet
echo "      Done."

# 2. Create .env from template if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "[2/4] Created .env — open it and fill in your Telegram credentials."
else
    echo "[2/4] .env already exists — skipping."
fi

# 3. Create outputs and logs dirs
mkdir -p outputs logs
echo "[3/4] Created outputs/ and logs/ directories."

# 4. Test the scanner in dry-run mode
echo "[4/4] Running scanner dry-run (no Telegram sent)..."
echo ""
python scanner.py --dry-run
echo ""

# 5. Show cron instructions
echo "─────────────────────────────────────────────────────────────"
echo " Setup complete. Next steps:"
echo ""
echo " 1. Open .env and paste in your Telegram token + chat ID"
echo "    (see TELEGRAM_SETUP.md for how to get these)"
echo ""
echo " 2. Test with real Telegram:"
echo "    source .env && python scanner.py"
echo ""
echo " 3. Schedule the scanner to run at 4:15pm ET, Mon-Fri:"
echo "    crontab -e"
echo "    Add this line:"
echo "    15 16 * * 1-5 cd $BOT_DIR && source .env && python scanner.py >> logs/scanner.log 2>&1"
echo ""
echo " 4. Run the full backtest:"
echo "    python main.py backtest --wf --mc"
echo "─────────────────────────────────────────────────────────────"
