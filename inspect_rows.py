
import sys
import os
import gspread
import json
# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

SOURCE_SHEET_NAME = "Outscraper-20260204095850m31_high_school_%2B1"

def inspect_rows():
    try:
        print(f"Connecting to sheet: {SOURCE_SHEET_NAME}...")
        client = GoogleSheetsClient()
        
        spreadsheet = client.client.open(SOURCE_SHEET_NAME)
        worksheet = spreadsheet.sheet1
        
        # Get all records (headers + rows)
        # Using get_all_records which returns list of dicts
        records = worksheet.get_all_records()
        
        print(f"\n✅ Successfully fetched {len(records)} records")
        print("-" * 50)
        
        if not records:
            print("Sheet is empty.")
            return

        print("First 2 records sample:")
        for i, record in enumerate(records[:2]):
            print(f"\n--- Row {i+1} ---")
            # Print only keys with values to reduce noise
            clean_record = {k: v for k, v in record.items() if v}
            print(json.dumps(clean_record, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_rows()
