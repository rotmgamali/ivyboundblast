import sys
sys.path.append("/Users/mac/Desktop/Ivybound")
from sheets_integration import GoogleSheetsClient

client = GoogleSheetsClient("Ivy Bound - Scraped Leads")
client.setup_sheets()
records = client.input_sheet.get_all_records()

print(f"Total Records: {len(records)}")
print("Last 10 Leads Appended:")
for r in records[-10:]:
    print(f"[{r.get('role', 'N/A')}] {r.get('first_name', '')} {r.get('last_name', '')} | {r.get('email', '')} | {r.get('business_name', '')}")
