from sheets_integration import GoogleSheetsClient
import json

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"

def deep_inspect():
    client = GoogleSheetsClient()
    sheet = client.client.open(SOURCE_SHEET_NAME).sheet1
    
    # 1. Inspect Headers by Index
    print("--- HEADERS (Index: Name) ---")
    headers = sheet.row_values(1)
    first_name_indices = []
    
    for i, h in enumerate(headers):
        print(f"{i}: {h}")
        if "first_name" in str(h).lower():
            first_name_indices.append(i)
            
    print(f"\nPotential 'First Name' Indices: {first_name_indices}")
    
    # 2. Find the Raw Row
    print("\n--- RAW ROW VALUES ---")
    target_email = "jwindham@harvestacademy.net"
    
    # We'll grab all values to find the row index manually to avoid get_all_records dict mapping
    all_values = sheet.get_all_values()
    
    found_row = None
    header_row = all_values[0]
    
    # Find email column index
    email_idx = -1
    for i, h in enumerate(header_row):
        if 'email' == h.lower().strip():
            email_idx = i
            break
            
    if email_idx == -1:
        print("Could not find 'email' column header!")
        return

    # Find row
    for row_idx, row in enumerate(all_values):
        if row_idx == 0: continue # Skip header
        
        # Safety check for short rows
        if len(row) > email_idx and row[email_idx] == target_email:
            found_row = row
            print(f"Found {target_email} at Row {row_idx + 1}")
            break
            
    if found_row:
        # Print value at every 'first_name' index
        for idx in first_name_indices:
            val = found_row[idx] if len(found_row) > idx else "<MISSING>"
            header_name = headers[idx]
            print(f"Column '{header_name}' (Index {idx}): '{val}'")
            
        print("\nFull Row Dump:")
        print(json.dumps(found_row, indent=2))
    else:
        print(f"Record {target_email} not found in raw values.")

if __name__ == "__main__":
    deep_inspect()
