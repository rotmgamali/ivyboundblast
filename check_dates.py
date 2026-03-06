
import sys
import os
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def check_earliest():
    client = GoogleSheetsClient()
    client.setup_sheets()
    records = client._fetch_all_records()
    
    dates = []
    for r in records:
        d = r.get('email_1_sent_at')
        if d:
            dates.append(d)
            
    if dates:
        dates.sort()
        print(f"Earliest email_1_sent: {dates[0]}")
        print(f"Latest email_1_sent: {dates[-1]}")
    else:
        print("No sent dates found.")

if __name__ == "__main__":
    check_earliest()
