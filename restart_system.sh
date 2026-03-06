#!/bin/bash
# Ivy Bound - Robust Restart Script

LOG_DIR="mailreef_automation/logs"
WATCHER_PID_FILE="$LOG_DIR/watcher_ivybound.pid"
SENDER_PID_FILE="$LOG_DIR/sender_ivybound.pid"

echo "🔄 Restarting Ivy Bound Email Automation..."

# Function to kill process by PID file
kill_pid_file() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null; then
            echo "🛑 Stopping process $pid..."
            kill $pid
            sleep 2
            if ps -p $pid > /dev/null; then
                kill -9 $pid
            fi
        fi
        rm -f "$pid_file"
    fi
}

kill_pid_file "$WATCHER_PID_FILE"
kill_pid_file "$SENDER_PID_FILE"

# Start the system
echo "🚀 Starting main.py --profile IVYBOUND..."
python3 mailreef_automation/main.py --profile IVYBOUND > "$LOG_DIR/automation.log" 2>&1 &

echo "✅ System started in background. Monitor via: tail -f $LOG_DIR/automation.log"
