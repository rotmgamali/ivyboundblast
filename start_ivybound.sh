#!/bin/bash
echo "🗄️ Starting Ivybound Server Operations..."

# Start the continuous Lead Generator daemon in the background
# It will run indefinitely and enforce its own 50,000 lead loop limits
nohup python pipeline/lead_generator.py > generator.log 2>&1 &
echo "[+] Lead Generator initialized in background (Logging to generator.log)"

# Start the core Mailreef Email Sender in the foreground
# This runs the standard pipeline against the WEB4GURU or IVYBOUND profiles
echo "[+] Starting Core Email Sender..."
python mailreef_automation/main.py --profile IVYBOUND
