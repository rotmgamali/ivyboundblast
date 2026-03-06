from sheets_integration import GoogleSheetsClient

def find_name_columns():
    client = GoogleSheetsClient()
    sheet_name = "Outscraper-20260201101100m30"
    
    print(f"Opening {sheet_name}...")
    try:
        sheet = client.client.open(sheet_name)
        headers = sheet.sheet1.row_values(1)
        
        print("\nPossible Name Columns:")
        for h in headers:
            if "name" in h.lower():
                print(f"- {h}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_name_columns()
