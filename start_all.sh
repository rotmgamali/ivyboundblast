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

# 1. Ivybound Summer email sender (truckice, 88 inboxes)
spawn_supervised "IVYBOUND_SUMMER" \
  "$PYTHON_BIN" mailreef_automation/main.py --profile IVYBOUND_SUMMER

# 2. Bahamas Retreat email sender — PAUSED.
#    The 84 competitionhand inboxes are on web4guru.online / agentsdirect.online /
#    airagents.online style domains. Sending a "SerenitySpaces Bahamas" pitch
#    from those domains is a brand/SPF mismatch that will torch deliverability.
#    Restart only after Bahamas-aligned domains are provisioned in Mailreef.
# spawn_supervised "BAHAMAS_RETREAT" \
#   "$PYTHON_BIN" mailreef_automation/main.py --profile BAHAMAS_RETREAT

# 3. Bahamas executive scraper daemon (24/7, auto-syncs verified leads to sheet).
#    Keep running so the lead pool builds while we sort out the sender domains.
spawn_supervised "BAHAMAS_SCRAPER" \
  "$PYTHON_BIN" bahamas_daemon.py \
    --auto-sync-sheets --max-per-city 25 --cities-per-cycle 3 --cycle-rest-min 90

log "Daemons spawned (BAHAMAS_RETREAT sender paused — domain mismatch). Waiting forever..."
wait
