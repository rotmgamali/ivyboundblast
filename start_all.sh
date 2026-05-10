#!/bin/bash
# Production launcher for Railway / local 24/7 deployment.
# Starts all three daemons under a simple supervisor that restarts on crash.

set -u
cd "$(dirname "$0")"
mkdir -p logs

PYTHON_BIN="${PYTHON_BIN:-python3}"

# ANSI colours when running on a TTY.
if [ -t 1 ]; then
  GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
else
  GREEN=""; YELLOW=""; RED=""; RESET=""
fi

log() { echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] $*"; }

# Trap SIGTERM/SIGINT and propagate to children.
PIDS=()
shutdown() {
  log "${YELLOW}Shutdown signal received — stopping daemons${RESET}"
  for pid in "${PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  wait
  log "All daemons stopped"
  exit 0
}
trap shutdown SIGTERM SIGINT

# Spawn a single daemon with auto-restart on crash.
spawn_supervised() {
  local name="$1"; shift
  (
    while true; do
      log "${GREEN}[$name] starting${RESET}"
      "$@"
      ec=$?
      log "${RED}[$name] exited with code $ec — restarting in 30s${RESET}"
      sleep 30
    done
  ) &
  PIDS+=("$!")
}

log "${GREEN}========================================${RESET}"
log "${GREEN}  IVYBOUND + BAHAMAS PRODUCTION LAUNCH${RESET}"
log "${GREEN}========================================${RESET}"
log "Python:  $($PYTHON_BIN --version 2>&1)"
log "Workdir: $(pwd)"

# 1. Ivybound Summer email sender — PAUSED 2026-05-10.
#    User priority is Bahamas. All competitionhand inboxes redirected to BAH.
#    Truckice still idle (burned domain rep from March). IV restart only when
#    user explicitly says so.
# spawn_supervised "IVYBOUND_SUMMER" \
#   "$PYTHON_BIN" mailreef_automation/main.py --profile IVYBOUND_SUMMER

# 2. Bahamas Retreat email sender (competitionhand, 84 inboxes).
#    UN-PAUSED 2026-05-05 after live deliverability test: 3/3 test emails
#    landed in Gmail Inbox (vs 1/3 truckice/IV that even arrived, with
#    that one in Spam). Brand mismatch theory was wrong — competitionhand
#    is clean because it has no prior reputation history. truckice is
#    burned from the March IV campaign.
spawn_supervised "BAHAMAS_RETREAT" \
  "$PYTHON_BIN" mailreef_automation/main.py --profile BAHAMAS_RETREAT

# 3. Bahamas executive scraper daemon (24/7).
#    Sender is now active, so push the scraper harder so the pool stays ahead.
spawn_supervised "BAHAMAS_SCRAPER" \
  "$PYTHON_BIN" bahamas_daemon.py \
    --auto-sync-sheets --max-per-city 40 --cities-per-cycle 4 --cycle-rest-min 30 \
    --sheet-name "Bahamas Retreat - Leads"

log "All 3 daemons spawned. Waiting forever..."
wait
