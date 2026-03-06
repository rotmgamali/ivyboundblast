
import sys
import os
import gspread
# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

SOURCE_SHEET_NAME = "Outscraper-20260204095850m31_high_school_%2B1"

def inspect_sheet():
    try:
        print(f"Connecting to sheet: {SOURCE_SHEET_NAME}...")
        client = GoogleSheetsClient()
        
        # Open by name
        spreadsheet = client.client.open(SOURCE_SHEET_NAME)
        worksheet = spreadsheet.sheet1
        
        # Get headers (first row)
        headers = worksheet.row_values(1)
        
        print(f"\n✅ Successfully accessed '{SOURCE_SHEET_NAME}'")
        print("-" * 50)
        print(f"Total Columns: {len(headers)}")
        print("Headers found:")
        for i, h in enumerate(headers):
            print(f"{i}: {h}")
        print("-" * 50)
        
        # Check specifically for "Email" keywords
        email_cols = [h for h in headers if "email" in h.lower()]
        if email_cols:
            print(f"Potential Email columns: {email_cols}")
        else:
            print("⚠️ No obvious 'Email' column found.")
            
    except gspread.SpreadsheetNotFound:
        print(f"❌ Error: Sheet '{SOURCE_SHEET_NAME}' not found. Please check the spelling exactly.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_sheet()
