
import sys
import os
from datetime import datetime
from collections import Counter

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

def check_status():
    print("Connecting to Google Sheets...")
    client = GoogleSheetsClient()
    client.setup_sheets() # Initialize connection
    
    # We need to fetch all records to count correctly
    # The client has a cached method, but we want fresh data
    # client._fetch_all_records() uses cache if recent.
    # We'll force fetch by clearing cache or just calling the worksheet directly if we want absolute fresh data.
    # But for stats, the cache (5 mins) is probably fine.
    
    records = client._fetch_all_records()
    print(f"Total Records: {len(records)}")
    
    status_counts = Counter()
    sent_today_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for r in records:
        status = r.get('status', 'unknown') or 'pending'
        status_counts[status] += 1
        
        # Check sent today (Email 1)
        e1_date = r.get('email_1_sent_at', '')
        if e1_date and today_str in e1_date:
            sent_today_count += 1
            
        # Check sent today (Email 2)
        e2_date = r.get('email_2_sent_at', '')
        if e2_date and today_str in e2_date:
            sent_today_count += 1
            
    print("\n--- Status Breakdown ---")
    for s, c in status_counts.items():
        print(f"{s}: {c}")
        
    print(f"\n✅ Total Emails Sent TODAY: {sent_today_count}")
    
    # Analyze 'email_1_sent' sources
    print("\n--- Contacted Source Analysis (email_1_sent) ---")
    source_counts = Counter()
    for r in records:
        if r.get('status') == 'email_1_sent':
            notes = str(r.get('notes', '')).lower()
            sType = str(r.get('school_type', '')).lower()
            
            if 'val status: receiving' in notes or 'val: receiving' in notes:
                label = "Verified Florida Leads (Original Batch)"
            elif 'outscraper' in notes:
                label = "New Public Leads (Unverified Batch)"
            else:
                label = "Other/Unknown Source"
                
            source_counts[label] += 1
            
    for label, count in source_counts.items():
        print(f"{label}: {count}")
    print("---------------------------------------------")

if __name__ == "__main__":
    check_status()
