#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"
SCRAPER_SCRIPT="Jobs/mass_harvest.py"
LOG_FILE="$PROJECT_DIR/scraper_service.log"

# Navigate to project directory
cd "$PROJECT_DIR" || exit 1

# Ensure logs directory exists
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] --- Launching Ivybound LeadMachine Scraper Service ---" >> "$LOG_FILE"
echo "[$(date)] --- System Sleep Prevention (caffeinate) Active ---" >> "$LOG_FILE"

# Infinite loop to keep the scraper running
while true; do
    echo "[$(date)] Starting scraper process..." >> "$LOG_FILE"
    
    # Run the scraper with caffeinate to prevent sleep
    # -i: prevent system sleep
    # -s: prevent system sleep on AC power
    # -d: prevent display sleep (optional, but good for visibility)
    # PYTHONPATH=. to ensure imports work from root
    PYTHONPATH=. caffeinate -is "$PYTHON_BIN" -u "$SCRAPER_SCRIPT" >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    echo "[$(date)] Scraper exited with code $EXIT_CODE. Restarting in 60 seconds..." >> "$LOG_FILE"
    
    # Wait before restarting to avoid rapid-fire failure loops
    sleep 60
done
