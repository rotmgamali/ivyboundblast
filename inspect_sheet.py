from sheets_integration import GoogleSheetsClient
import json

SHEET_NAME = "Ivy Bound - High & Middle Schools (Validated)"

def inspect_headers():
    print(f"Opening '{SHEET_NAME}'...")
    client = GoogleSheetsClient().client
    sheet = client.open(SHEET_NAME).sheet1
    
    headers = sheet.row_values(1)
    print(f"Headers found ({len(headers)}):")
    print(headers)
    
    first_row = sheet.row_values(2)
    
    output = {
        "headers": headers,
        "first_row": first_row
    }
    
    with open("headers.json", "w") as f:
        json.dump(output, f, indent=2)
        
    print("Saved to headers.json")

if __name__ == "__main__":
    inspect_headers()
