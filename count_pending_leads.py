import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from sheets_integration import GoogleSheetsClient

def count_leads():
    print("Connecting to Google Sheets...")
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    print("Fetching all records to count pending leads...")
    all_records = client._fetch_all_records()
    
    from collections import Counter
    status_counts = Counter()
    
    for row in all_records:
        status = row.get('status', '').strip().lower()
        if not status:
            status = 'pending (empty)'
        status_counts[status] += 1
        
    print(f"\\n--- EXACT STATUS BREAKDOWN ---")
    print(f"Total Leads in Sheet: {len(all_records)}")
    for status, count in status_counts.most_common():
        print(f"'{status}': {count}")

if __name__ == "__main__":
    count_leads()
