
import sys
import os
# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

def inspect_sent_notes():
    print("Connecting...")
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    records = client._fetch_all_records()
    
    print("\n--- SENT LEADS SAMPLE (Notes) ---")
    count = 0
    for r in records:
        if r.get('status') == 'email_1_sent':
            print(f"[{count+1}] Notes: {r.get('notes')}")
            count += 1
            if count >= 10:
                break
                
if __name__ == "__main__":
    inspect_sent_notes()
