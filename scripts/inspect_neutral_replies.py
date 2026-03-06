import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient

def inspect_neutral():
    print("🚀 Inspecting Neutral Replies...")
    
    sheet_name = "Ivy Bound - Reply Tracking"
    sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    rows = worksheet.get_all_records()
    
    neutrals = [r for r in rows if r.get("Sentiment") == "NEUTRAL"]
    print(f"  Found {len(neutrals)} Neutral replies.")
    
    print("\n--- SAMPLE SNIPPETS ---")
    for i, row in enumerate(neutrals[:15]):
        print(f"{i+1}. Subject: {row.get('Subject')}")
        print(f"   Snippet: {row.get('Snippet')}")
        print("-" * 40)

if __name__ == "__main__":
    inspect_neutral()
