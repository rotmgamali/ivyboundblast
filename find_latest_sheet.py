from sheets_integration import GoogleSheetsClient
from datetime import datetime

def find_newest_sheet():
    print("Authenticating...")
    gc = GoogleSheetsClient().client
    
    print("Listing spreadsheet files...")
    # list_spreadsheet_files returns a list of dicts with 'id', 'name', 'createdTime', 'modifiedTime'
    files = gc.list_spreadsheet_files()
    
    # Sort by createdTime descending
    # Time format usually: 2026-02-01T10:11:00.000Z
    files.sort(key=lambda x: x.get('createdTime', ''), reverse=True)
    
    print(f"\nFound {len(files)} spreadsheets. Showing top 10 newest:")
    print("-" * 60)
    print(f"{'CREATED':<25} | {'NAME'}")
    print("-" * 60)
    
    for f in files[:10]:
        print(f"{f.get('createdTime', 'N/A'):<25} | {f.get('name')}")

if __name__ == "__main__":
    find_newest_sheet()
