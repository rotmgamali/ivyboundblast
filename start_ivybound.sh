#!/bin/bash
echo "🗄️ Starting Ivybound Server Operations..."

# Start the continuous Lead Generator daemon in the background
# It will run indefinitely and enforce its own 50,000 lead loop limits
# We remove the > generator.log redirect so that Railway can capture these logs in the main console!
python pipeline/lead_generator.py &
echo "[+] Lead Generator initialized in background (Logging to main Railway console)"

# Start the core Mailreef Email Sender in the foreground
# This runs the standard pipeline against the WEB4GURU or IVYBOUND profiles
echo "[+] Starting Core Email Sender..."
python mailreef_automation/main.py --profile IVYBOUND
