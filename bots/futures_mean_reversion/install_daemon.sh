#!/usr/bin/env bash
# ─── TradeMastery Bot Daemon Installer ────────────────────────────────────────
# Installs the 24/7 launchd service on Mac.
# Run once. After this the bot starts automatically on login and after crashes.
#
# Usage:
#   bash install_daemon.sh
#   bash install_daemon.sh --stop      # stop and uninstall
#   bash install_daemon.sh --restart   # restart the daemon
#   bash install_daemon.sh --status    # show status + last log lines
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
PLIST_NAME="com.trademastery.bot.plist"
PLIST_SRC="$BOT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_FILE="$BOT_DIR/logs/daemon.log"

# ── Handle flags ──────────────────────────────────────────────────────────────
case "${1:-}" in
  --stop)
    echo "🛑  Stopping TradeMastery daemon..."
    launchctl unload "$PLIST_DEST" 2>/dev/null && echo "✅  Stopped." || echo "⚠️   Not running."
    exit 0
    ;;
  --restart)
    echo "🔄  Restarting TradeMastery daemon..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 1
    launchctl load "$PLIST_DEST"
    echo "✅  Restarted."
    exit 0
    ;;
  --status)
    echo "📊  TradeMastery Bot Status"
    echo "───────────────────────────"
    launchctl list | grep trademastery || echo "  Not running (not loaded)"
    echo ""
    echo "Last 20 log lines:"
    tail -20 "$LOG_FILE" 2>/dev/null || echo "  No log yet."
    exit 0
    ;;
esac

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  TradeMastery Bot — Daemon Installer     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Install dependencies ───────────────────────────────────────────────────
echo "📦  Installing Python dependencies..."
pip3 install -q -r "$BOT_DIR/requirements.txt"
pip3 install -q schedule   # scheduler for the daemon
echo "✅  Dependencies ready."

# ── 2. Create logs dir ────────────────────────────────────────────────────────
mkdir -p "$BOT_DIR/logs"

# ── 3. Stop existing daemon if running ────────────────────────────────────────
if launchctl list | grep -q "com.trademastery.bot"; then
    echo "🔄  Stopping existing daemon..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 1
fi

# ── 4. Copy plist to LaunchAgents ─────────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DEST"
echo "✅  Plist installed → $PLIST_DEST"

# ── 5. Load (start) the daemon ────────────────────────────────────────────────
launchctl load "$PLIST_DEST"
echo "✅  Daemon loaded and running."

# ── 6. Wait a moment then send a test message ─────────────────────────────────
echo ""
echo "⏳  Waiting 3s for daemon to start..."
sleep 3

echo "📱  Sending test Telegram message..."
cd "$BOT_DIR"
set -a; source .env; set +a
python3 bot_daemon.py --test && echo "✅  Check Telegram!" || echo "⚠️   Test failed — check .env"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✅  Bot is live 24/7                   ║"
echo "║                                          ║"
echo "║   Scans: Mon–Fri at 6:00 AM PT           ║"
echo "║   Auto-restarts if Mac reboots           ║"
echo "║                                          ║"
echo "║   Commands:                              ║"
echo "║   bash install_daemon.sh --status        ║"
echo "║   bash install_daemon.sh --stop          ║"
echo "║   bash install_daemon.sh --restart       ║"
echo "║   tail -f logs/daemon.log                ║"
echo "╚══════════════════════════════════════════╝"
echo ""
