import os
import sys
import json
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

def count_golden():
    client = GoogleSheetsClient()
    client.setup_sheets()
    sheet = client.replies_sheet.worksheet('Sheet 1')
    records = [r for r in sheet.get_all_records() if 'GOLDEN' in str(r.get('Sentiment', '')).upper()]
    # Print distinct emails
    emails = {r.get('From Email') for r in records}
    print(f"Total Rows: {len(records)}")
    print(f"Unique Emails: {len(emails)}")
    for email in emails:
        print(f" - {email}")

if __name__ == "__main__":
    count_golden()
