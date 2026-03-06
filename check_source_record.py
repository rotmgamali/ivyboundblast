from sheets_integration import GoogleSheetsClient

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"

def check_record():
    client = GoogleSheetsClient()
    sheet = client.client.open(SOURCE_SHEET_NAME).sheet1
    records = sheet.get_all_records()
    
    target_email = "jwindham@harvestacademy.net"
    
    found = False
    for r in records:
        if r.get('email') == target_email:
            print(f"FOUND RECORD for {target_email}:")
            print(f"  first_name: '{r.get('first_name')}'")
            print(f"  last_name:  '{r.get('last_name')}'")
            print(f"  name:       '{r.get('name')}'")
            found = True
            break
            
    if not found:
        print(f"Record for {target_email} NOT FOUND in source.")

if __name__ == "__main__":
    check_record()
