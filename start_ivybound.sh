#!/bin/bash
echo "🗄️ Starting Ivybound Server Operations..."

# Start the continuous Lead Generator daemon in the background
# Wrapped in a permanent loop so if the OS OOM-kills the Chromium browser, it instantly restarts!
(
  while true; do
    echo "[!] Launching Pipeline Lead Generator Daemon..."
    python pipeline/lead_generator.py
    echo "[-] WARNING: Lead Generator crashed or was killed by OS. Restarting in 5 seconds..."
    sleep 5
  done
) &
echo "[+] Lead Generator initialized in background (Logging to main Railway console)"

# Start the core Mailreef Email Sender in the foreground
# This runs the standard pipeline against the WEB4GURU or IVYBOUND profiles
echo "[+] Starting Core Email Sender..."
python mailreef_automation/main.py --profile IVYBOUND
