from sheets_integration import GoogleSheetsClient
import time

def cleanup_sheet(sheet_name):
    print(f"🧹 Cleaning up {sheet_name}...")
    client = GoogleSheetsClient(replies_sheet_name=sheet_name)
    client.setup_sheets()
    worksheet = client.replies_sheet.sheet1
    
    all_values = worksheet.get_all_values()
    if not all_values:
        print("Empty sheet, skipping.")
        return
        
    headers = all_values[0]
    data_rows = all_values[1:]
    
    # Filter for rows that have at least an email or a timestamp
    clean_data = [row for row in data_rows if any(cell.strip() for cell in row)]
    
    print(f"  - Original rows: {len(data_rows)}")
    print(f"  - Actual data rows: {len(clean_data)}")
    
    if len(data_rows) == len(clean_data):
        print("  - No empty rows found. Skipping clear/rewrite.")
        return

    # Clear everything
    worksheet.clear()
    
    # Rewrite
    worksheet.update('A1', [headers] + clean_data)
    
    # Re-apply formatting
    client.apply_formatting()
    print(f"✅ {sheet_name} cleaned and formatted.")

if __name__ == "__main__":
    cleanup_sheet("Ivy Bound - Reply Tracking")
    cleanup_sheet("Web4Guru - Reply Tracking")
