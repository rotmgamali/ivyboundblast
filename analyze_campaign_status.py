
import sys
import os
from collections import Counter

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def analyze():
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    print("Fetching all records from Campaign Leads sheet...")
    records = client.input_sheet.sheet1.get_all_records()
    
    total_leads = len(records)
    status_counts = Counter()
    
    sent_count = 0
    followup_count = 0
    replied_count = 0
    
    for row in records:
        status = str(row.get('status', '')).lower().strip()
        status_counts[status] += 1
        
        if 'email_1_sent' in status or 'contacted' in status:
            sent_count += 1
        if 'email_2_sent' in status or 'followup' in status:  # Adjust based on likely status names
            followup_count += 1
        if 'replied' in status:
            replied_count += 1
            
    print("\n--- Campaign Analysis ---")
    print(f"Total Leads in Sheet: {total_leads}")
    print(f"Total Emails Sent (Status contains 'email_1_sent' or 'contacted'): {sent_count}")
    print(f"Total Follow-ups Sent (Status contains 'email_2_sent'): {followup_count}")
    print(f"Total Replied (Status contains 'replied'): {replied_count}")
    
    # Check for specific 'contacted_2' or similar if that's how we track round 2
    # Or maybe it's a separate column? Let's check keys.
    if records:
        print(f"\nSample Keys: {list(records[0].keys())}")
        
    print("\nStatus Breakdown:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    print("\nFirst 5 Records (Status Column):")
    for i, row in enumerate(records[:5]):
        print(f"Row {i+1}: {row.get('status', 'MISSING')}")

if __name__ == "__main__":
    analyze()
