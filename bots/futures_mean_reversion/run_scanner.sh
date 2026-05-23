#!/usr/bin/env bash
# ─── TradeMastery Signal Scanner — cron-safe launcher ─────────────────────────
# Works in cron (no interactive shell needed). Loads .env, activates venv if
# present, runs scanner.py, and logs output with a timestamp.
#
# Crontab entry (4:15pm ET Mon-Fri):
#   15 16 * * 1-5 /Users/kev/Desktop/Quant-PF-Signals-Bot/run_scanner.sh >> /Users/kev/Desktop/Quant-PF-Signals-Bot/logs/scanner.log 2>&1
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Resolve the directory this script lives in (works even when called from cron)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "──────────────────────────────────────────"
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting scanner"

# Load .env (cron-safe: set -a exports every var automatically)
ENV_FILE="$SCRIPT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "Loaded .env from $ENV_FILE"
else
  echo "WARNING: .env not found at $ENV_FILE — using existing environment"
fi

# Activate virtualenv if one exists alongside this script
VENV="$SCRIPT_DIR/venv"
if [[ -d "$VENV" ]]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  echo "Activated venv at $VENV"
fi

# Make sure logs dir exists
mkdir -p "$SCRIPT_DIR/logs"

# Run the scanner
cd "$SCRIPT_DIR"
python3 scanner.py "$@"

echo "$(date '+%Y-%m-%d %H:%M:%S') — Done"
