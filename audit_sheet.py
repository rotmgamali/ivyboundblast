import sys
sys.path.append("/Users/mac/Desktop/Ivybound")
from sheets_integration import GoogleSheetsClient

client = GoogleSheetsClient("Ivy Bound - Scraped Leads")
client.setup_sheets()
records = client.input_sheet.sheet1.get_all_records()

invalid_leads = []
for r in records[-100:]:
    status = r.get('email_verified', '').lower()
    if status != 'verified' and status != 'unchecked' and status != 'passed':
        invalid_leads.append(f"{r.get('email')} | Status: {status}")

print(f"Total Records checked: {len(records[-100:])}")
print(f"Invalid leads in last 100: {len(invalid_leads)}")
for i in invalid_leads:
    print(i)
