import os
import sys
import json
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

def get_golden():
    client = GoogleSheetsClient()
    client.setup_sheets()
    sheet = client.replies_sheet.worksheet('Sheet 1')
    records = [r for r in sheet.get_all_records() if 'GOLDEN' in str(r.get('Sentiment', '')).upper()]
    with open('/tmp/current_16_golden.json', 'w') as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} leads.")

if __name__ == "__main__":
    get_golden()
