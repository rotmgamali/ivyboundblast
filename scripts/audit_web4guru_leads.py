import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def audit_leads():
    sheet_name = "Web4Guru Accountants - Campaign Leads"
    print(f"📊 Auditing {sheet_name}...")
    
    try:
        sheets = GoogleSheetsClient(input_sheet_name=sheet_name)
        sheets.setup_sheets()
        records = sheets._fetch_all_records()
        
        status_counts = {}
        for r in records:
            status = str(r.get('status', '')).lower()
            status_counts[status] = status_counts.get(status, 0) + 1
            
        print("\n📈 Status Breakdown:")
        for status, count in status_counts.items():
            print(f"  - {status if status else '[empty]'}: {count}")
            
        # Sample some pending leads
        pending = [r for r in records if r.get('status', '').lower() in ['', 'pending']]
        print(f"\nFound {len(pending)} pending leads.")
        if pending:
            print(f"Sample pending lead: {pending[0].get('email')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    audit_leads()
