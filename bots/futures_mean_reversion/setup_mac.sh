#!/usr/bin/env bash
# ─── TradeMastery Bot — One-command Mac setup ─────────────────────────────────
# Usage (run this from anywhere on your Mac):
#   bash <(curl -fsSL https://raw.githubusercontent.com/mastermindkev28-sys/TradeMasteryOS/claude/futures-mean-reversion-bot-6GK9s/bots/futures_mean_reversion/setup_mac.sh)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOT_DIR="$HOME/Desktop/Quant-PF-Signals-Bot"
BRANCH="claude/futures-mean-reversion-bot-6GK9s"
REPO="https://github.com/mastermindkev28-sys/TradeMasteryOS.git"
BOT_SUBDIR="bots/futures_mean_reversion"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   TradeMastery Signal Bot — Mac Setup    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Ensure bot dir exists ──────────────────────────────────────────────────
echo "📁  Target: $BOT_DIR"
mkdir -p "$BOT_DIR"

# ── 2. Pull latest bot files from TradeMasteryOS ──────────────────────────────
echo ""
echo "⬇️   Downloading bot files from GitHub..."

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

git clone --quiet --depth 1 --branch "$BRANCH" "$REPO" "$TMP_DIR/repo"

# Copy bot files (preserve existing .env if present)
if [[ -f "$BOT_DIR/.env" ]]; then
  echo "⚠️   Existing .env found — keeping it (not overwriting)"
  cp -r "$TMP_DIR/repo/$BOT_SUBDIR"/. "$BOT_DIR/" --backup=none 2>/dev/null || \
    rsync -a --exclude='.env' "$TMP_DIR/repo/$BOT_SUBDIR/" "$BOT_DIR/"
else
  cp -r "$TMP_DIR/repo/$BOT_SUBDIR"/. "$BOT_DIR/"
fi

echo "✅  Files copied."

# ── 3. Make launcher executable ───────────────────────────────────────────────
chmod +x "$BOT_DIR/run_scanner.sh"
echo "✅  run_scanner.sh is executable."

# ── 4. Create .env if missing ─────────────────────────────────────────────────
if [[ ! -f "$BOT_DIR/.env" ]]; then
  cat > "$BOT_DIR/.env" << 'EOF'
PROP_FIRM_PLAN=lucid_25k
TELEGRAM_BOT_TOKEN=8885775511:AAHIaBroM6Zv2mi4FIIiW95UYr4bR7WDmgk
TELEGRAM_CHAT_ID=8002213236
EOF
  echo "✅  .env created."
else
  echo "✅  .env already exists."
fi

# ── 5. Create logs dir ────────────────────────────────────────────────────────
mkdir -p "$BOT_DIR/logs"
echo "✅  logs/ directory ready."

# ── 6. Install Python dependencies ───────────────────────────────────────────
echo ""
echo "📦  Installing Python dependencies..."
pip3 install -q -r "$BOT_DIR/requirements.txt"
echo "✅  Dependencies installed."

# ── 7. Test dry run ───────────────────────────────────────────────────────────
echo ""
echo "🧪  Running dry test (no Telegram message sent)..."
echo "────────────────────────────────────────────────"
cd "$BOT_DIR"
set -a; source .env; set +a
python3 scanner.py --dry-run
echo "────────────────────────────────────────────────"

# ── 8. Install cron job ───────────────────────────────────────────────────────
echo ""
CRON_LINE="15 16 * * 1-5 $BOT_DIR/run_scanner.sh >> $BOT_DIR/logs/scanner.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "run_scanner.sh"; then
  echo "✅  Cron job already installed — skipping."
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  echo "✅  Cron job installed (runs Mon-Fri at 4:15pm ET)."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✅  Setup complete!                    ║"
echo "║                                          ║"
echo "║   Run manually anytime:                  ║"
echo "║   cd ~/Desktop/Quant-PF-Signals-Bot      ║"
echo "║   ./run_scanner.sh                       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
