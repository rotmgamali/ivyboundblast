#!/bin/bash
echo "🗄️ Starting Ivybound Server Operations..."

# DIAGNOSTIC: Show current directory structure to confirm path sanity
echo "[DIAGNOSTIC] Directory Structure:"
ls -F

# Start the core Mailreef Email Sender in the foreground
echo "[+] Starting Core Email Sender..."
python3 mailreef_automation/main.py --profile IVYBOUND
