import os
import sys
from dotenv import load_dotenv

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from sheets_integration import GoogleSheetsClient

def find_domain(domain_fragment):
    load_dotenv()
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    print(f"📡 Searching for '{domain_fragment}' in all records...")
    records = sheets._fetch_all_records()
    
    matches = []
    for r in records:
        email = str(r.get('email', '')).lower()
        domain = str(r.get('domain', '')).lower()
        if domain_fragment in email or domain_fragment in domain:
            matches.append(r)
            
    print(f"✅ Found {len(matches)} matches:")
    for m in matches:
        print(f"  - Email: {m.get('email')} | Domain: {m.get('domain')} | Status: {m.get('status')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        find_domain(sys.argv[1])
    else:
        find_domain("covenantschool")
        find_domain("lifeprepchristianacademy")
        find_domain("alphaperformance")
