from sheets_integration import GoogleSheetsClient
import json

def analyze_sheet():
    print("Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    
    sheet_name = "Outscraper-20260201101100m30"
    print(f"Attempting to open sheet: {sheet_name}")
    
    try:
        # Try to open the spreadsheet
        sheet = client.client.open(sheet_name)
        print(f"✓ Successfully opened spreadsheet: {sheet.title}")
        
        # Get the first worksheet
        worksheet = sheet.get_worksheet(0)
        print(f"Reading data from worksheet: {worksheet.title}")
        
        # Get headers
        headers = worksheet.row_values(1)
        print("\nHeaders found:")
        print(json.dumps(headers, indent=2))
        
        # Get all records to analyze validation
        print("\nReading all records...")
        records = worksheet.get_all_records()
        print(f"Total records found: {len(records)}")
        
        if not records:
            print("No data found in sheet.")
            return

        # Print first 2 records as sample
        print("\nSample Data (First 2 records):")
        print(json.dumps(records[:2], indent=2))
        
        # Analyze validation status
        # Look for columns related to validation
        validation_cols = [h for h in headers if 'status' in h.lower() or 'valid' in h.lower()]
        
        if validation_cols:
            print(f"\nAnalyzing validation columns: {validation_cols}")
            for col in validation_cols:
                counts = {}
                for record in records:
                    val = str(record.get(col, 'MISSING'))
                    counts[val] = counts.get(val, 0) + 1
                
                print(f"\nValue counts for '{col}':")
                for k, v in counts.items():
                    print(f"  {k}: {v}")
        else:
            print("\nWARNING: No obvious validation status columns found in headers.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        # List available sheets to help debug
        try:
            print("\nAvailable spreadsheets:")
            for s in client.client.list_spreadsheet_files():
                 print(f"- {s['name']}")
        except:
            pass

if __name__ == "__main__":
    analyze_sheet()
