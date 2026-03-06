import sys
import os
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sheets_integration import GoogleSheetsClient
from mailreef_automation import automation_config

def main():
    profile = automation_config.CAMPAIGN_PROFILES["WEB4GURU_ACCOUNTANTS"]
    client = GoogleSheetsClient(input_sheet_name=profile["input_sheet"], replies_sheet_name=profile["replies_sheet"])
    client.setup_sheets()
    
    records = client._fetch_all_records()
    print(f"Total Records: {len(records)}")
    
    import json
    google_website_in_custom = 0
    total_custom_parsed = 0
    
    for r in records:
        custom = r.get('custom_data')
        if not custom: continue
        
        try:
            data = json.loads(custom)
            total_custom_parsed += 1
            algo_domain = str(r.get('domain', ''))
            
            # Check what's in 'website' vs 'domain' in source
            src_website = data.get('website', '')
            src_domain = data.get('domain', '')
            
            if "google.com" in src_website or "goo.gl" in src_website:
                google_website_in_custom += 1
                if total_custom_parsed <= 5:
                    print(f"⚠️ Row {r.get('_row')} has Google Link in 'website': {src_website}")
                    print(f"   But 'domain' col is: {algo_domain}")
                    print(f"   Source 'domain' key: {src_domain}")
        except:
            pass
            
    print(f"\nCustom Data Analysis:")
    print(f"Parsed: {total_custom_parsed}")
    print(f"Rows with Google Link in 'website' source: {google_website_in_custom}")

if __name__ == "__main__":
    main()
