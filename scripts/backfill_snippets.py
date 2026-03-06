import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import automation_config

def backfill_snippets():
    print("🚀 Starting Snippet Backfill...")
    
    # 1. Setup Mailreef
    mailreef = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    
    # 2. Setup Sheets
    sheet_name = "Ivy Bound - Reply Tracking"
    sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    # 3. Fetch Inbound Emails (Last 14 days)
    cutoff_ts = time.time() - (14 * 24 * 3600)
    print(f"📡 Fetching global inbound emails since {datetime.fromtimestamp(cutoff_ts).date()}...")
    
    inbound_emails = []
    page = 1
    while True:
        data = mailreef.get_global_inbound(page=page)
        batch = data.get("data", []) if isinstance(data, dict) else data
        
        if not batch:
            break
            
        added_count = 0
        for email_data in batch:
            ts = email_data.get("ts", 0)
            if ts < cutoff_ts:
                # If significantly older, stop matching
                if ts < cutoff_ts - 86400:
                    added_count = -1 # Signal to break outer loop
                    break
                continue
            
            inbound_emails.append(email_data)
            added_count += 1
            
        if added_count == -1:
            break
            
        if len(batch) < 100:
            break
        page += 1
        print(f"  - Page {page-1} processed ({len(inbound_emails)} total found)...")

    print(f"  ✅ Found {len(inbound_emails)} relevant emails.")

    # Map email -> snippet
    email_to_snippet = {}
    for email_data in inbound_emails:
        sender = email_data.get("from_email", "").lower().strip()
        snippet = email_data.get("snippet_preview", "")
        if sender and snippet:
            # Prefer longer snippets if duplicates exist?
            # Or just take the most recent (which comes first usually)
            if sender not in email_to_snippet:
                email_to_snippet[sender] = snippet
            
    # 4. Update Sheet
    rows = worksheet.get_all_records()
    print(f"  🔍 Processing {len(rows)} sheet rows...")
    
    updated_count = 0
    clean_rows = []
    headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
    
    for row in rows:
        email = str(row.get("From Email", "")).lower().strip()
        current_snippet = str(row.get("Snippet", ""))
        
        if not current_snippet and email in email_to_snippet:
            row['Snippet'] = email_to_snippet[email]
            updated_count += 1
            
        # Reconstruct list
        clean_rows.append([str(row.get(h, "")) for h in headers])
        
    if updated_count > 0:
        print(f"  📝 Updating {updated_count} snippets...")
        worksheet.clear()
        worksheet.update('A1', [headers] + clean_rows)
        print("  ✨ Backfill complete!")
    else:
        print("  ✅ No missing snippets found (or no matches).")

if __name__ == "__main__":
    backfill_snippets()
