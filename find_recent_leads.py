
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

def find_recent_sends():
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    records = client._fetch_all_records()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    recent_sends = []
    for r in records:
        e1_date = r.get('email_1_sent_at', '')
        if e1_date and today_str in e1_date:
            recent_sends.append(r)
        
        if len(recent_sends) >= 5:
            break
            
    for i, r in enumerate(recent_sends):
        print(f"--- Lead {i+1} ---")
        print(f"Email: {r.get('email')}")
        print(f"Sent At: {r.get('email_1_sent_at')}")
        print(f"School: {r.get('school_name')}")
        print(f"Role: {r.get('role')}")
        print("-" * 20)

if __name__ == "__main__":
    find_recent_sends()
