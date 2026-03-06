import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def check_timestamps():
    sheet_name = "Web4Guru Accountants - Campaign Leads"
    print(f"📊 Checking timestamps in {sheet_name}...")
    
    try:
        sheets = GoogleSheetsClient(input_sheet_name=sheet_name)
        sheets.setup_sheets()
        records = sheets._fetch_all_records()
        
        sent_leads = [r for r in records if r.get('email_1_sent_at')]
        print(f"Total sent: {len(sent_leads)}")
        
        if not sent_leads:
            print("No sent leads found.")
            return
            
        # Sort by timestamp
        sent_leads.sort(key=lambda x: str(x.get('email_1_sent_at')))
        
        print("\nRecent sent timestamps (Last 20):")
        for i, r in enumerate(sent_leads[-20:]):
            print(f"  {i+1}. {r.get('email')} at {r.get('email_1_sent_at')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_timestamps()
