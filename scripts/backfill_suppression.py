import os
import re
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.suppression_manager import SuppressionManager
from sheets_integration import GoogleSheetsClient
from mailreef_automation.automation_config import CAMPAIGN_PROFILES

def backfill():
    sm = SuppressionManager()
    all_sent_emails = set()
    
    # 1. Parse Logs
    log_dir = os.path.join(ROOT_DIR, "mailreef_automation", "logs")
    print(f"📂 Scanning logs in {log_dir}...")
    
    # Pattern to match both log formats
    # Format A: 2026-02-09 ... | SCHEDULER | INFO | ✅ [SEND SUCCESS] Email sent to email@domain.com ...
    # Format B: 2026-02-09 ...,... - SCHEDULER - INFO - ✅ [SEND SUCCESS] Email sent to email@domain.com ...
    send_pattern = re.compile(r"Email sent to ([\w\.-]+@[\w\.-]+\.\w+)", re.IGNORECASE)
    
    for log_file in Path(log_dir).glob("*.log"):
        # print(f"  - Reading {log_file.name}")
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "SEND SUCCESS" in line:
                        match = send_pattern.search(line)
                        if match:
                            all_sent_emails.add(match.group(1).lower().strip())
        except Exception as e:
            print(f"  ❌ Error reading {log_file.name}: {e}")
            
    print(f"✅ Found {len(all_sent_emails)} unique emails from logs.")
    
    # 2. Parse Sheets (Optional but thorough)
    print("\n📊 Scanning Google Sheets for historical sends...")
    profiles_to_scan = ["IVYBOUND", "WEB4GURU_ACCOUNTANTS", "STRATEGY_B"]
    
    for profile_name in profiles_to_scan:
        profile = CAMPAIGN_PROFILES.get(profile_name)
        if not profile: continue
        
        sheet_name = profile.get("input_sheet")
        print(f"  - Scanning sheet: {sheet_name}")
        try:
            sheets = GoogleSheetsClient(input_sheet_name=sheet_name)
            sheets.setup_sheets()
            records = sheets._fetch_all_records()
            
            for r in records:
                status = str(r.get('status', '')).lower()
                email = r.get('email')
                if ('sent' in status or 'replied' in status) and email:
                    all_sent_emails.add(email.lower().strip())
        except Exception as e:
            print(f"  ❌ Error reading sheet {sheet_name}: {e}")

    print(f"\n📈 Total unique sent emails identified: {len(all_sent_emails)}")
    
    # 3. Populate DB
    if all_sent_emails:
        print("💾 Populating suppression database...")
        sm.bulk_add(list(all_sent_emails), campaign="BACKFILL")
        print("✨ Backfill complete!")
    else:
        print("⚠️ No emails found to backfill.")

if __name__ == "__main__":
    backfill()
