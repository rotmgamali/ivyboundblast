
import sys
import os
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def check_replies():
    print("Connecting to Google Sheets...")
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    # Access the replies worksheet
    # Based on sheets_integration.py it should be client.replies_sheet
    worksheet = client.replies_sheet.sheet1
    records = worksheet.get_all_records()
    
    print(f"Total entries in Reply Tracking sheet: {len(records)}")
    
    if len(records) > 0:
        print("\n--- Recent Replies ---")
        for i, r in enumerate(records[-5:]): # Show last 5
            print(f"[{i+1}] From: {r.get('from_email', r.get('email'))}")
            print(f"    Subject: {r.get('subject')}")
            print(f"    Date: {r.get('date', r.get('timestamp'))}")
            print(f"    Snipped: {str(r.get('body', r.get('content')))[:100]}...")
            print("-" * 20)
    else:
        print("No replies found in the Google Sheet.")

if __name__ == "__main__":
    check_replies()
