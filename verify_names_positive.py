from sheets_integration import GoogleSheetsClient

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"
DEST_SHEET_NAME = "Ivy Bound - Campaign Leads"

def verify_positive_case():
    client = GoogleSheetsClient()
    gc = client.client
    
    print(f"Opening Source: {SOURCE_SHEET_NAME}...")
    source_records = gc.open(SOURCE_SHEET_NAME).sheet1.get_all_records()
    
    print(f"Opening Dest: {DEST_SHEET_NAME}...")
    dest_records = gc.open(DEST_SHEET_NAME).sheet1.get_all_records()
    
    # Build Dest Map
    dest_map = {str(r.get('email', '')).lower(): r for r in dest_records}
    
    print("\nSearching for a record with a valid First Name in Source...")
    count = 0
    for src in source_records:
        email = str(src.get('email', '')).lower()
        first = src.get('first_name', '').strip()
        
        if first and email in dest_map:
            dest_val = dest_map[email].get('first_name', '')
            print(f"Match Found: {email}")
            print(f"  Source First Name: '{first}'")
            print(f"  Dest   First Name: '{dest_val}'")
            
            if first == dest_val:
                print("  ✅ MATCH: Destination has the correct name.")
            else:
                print("  ❌ MISMATCH: Destination does not match source.")
                
            count += 1
            if count >= 3:
                break
                
    if count == 0:
        print("Could not find any overlapping records with a First Name in source.")

if __name__ == "__main__":
    verify_positive_case()
