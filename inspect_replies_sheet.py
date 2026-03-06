
import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

client = GoogleSheetsClient()
client.setup_sheets()
worksheet = client.replies_sheet.sheet1
rows = worksheet.get_all_values()

print("\nHEADERS:")
print(rows[0] if rows else "EMPTY SHEET")

if len(rows) > 1:
    print("\nFIRST ROW DATA:")
    print(rows[1])
else:
    print("\nNO DATA ROWS")
