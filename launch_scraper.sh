#!/bin/bash

# Configuration
PROJECT_DIR="/Users/mac/Ivybound"
PYTHON_BIN="python3"
SCRAPER_SCRIPT="Jobs/mass_harvest.py"
LOG_FILE="$PROJECT_DIR/scraper_service.log"
LOCK_FILE="/tmp/ivybound_scraper.lock"

# Navigate to project directory
cd "$PROJECT_DIR" || exit 1

# Check for existing lock
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "[$(date)] Scraper already running with PID $PID. Exiting."
        exit 1
    fi
fi

# Create lock
echo $$ > "$LOCK_FILE"

# Ensure log cleanup handler
trap "rm -f $LOCK_FILE; exit" INT TERM EXIT

# Ensure logs directory exists
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] --- Launching Ivybound LeadMachine Scraper Service ---" >> "$LOG_FILE"
echo "[$(date)] --- System Sleep Prevention (caffeinate) Active ---" >> "$LOG_FILE"

# Infinite loop to keep the scraper running
while true; do
    echo "[$(date)] Starting scraper process..." >> "$LOG_FILE"
    
    # Run the scraper with caffeinate to prevent sleep
    PYTHONPATH=. caffeinate -is "$PYTHON_BIN" -u "$SCRAPER_SCRIPT" >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    echo "[$(date)] Scraper exited with code $EXIT_CODE. Restarting in 60 seconds..." >> "$LOG_FILE"
    
    # Wait before restarting
    sleep 60
done
