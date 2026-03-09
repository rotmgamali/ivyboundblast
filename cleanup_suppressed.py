"""
Emergency cleanup: Mark all suppressed leads in the sheet as 'suppressed' 
so the scheduler stops re-scanning them every 5 seconds.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sheets_integration import GoogleSheetsClient
from mailreef_automation.suppression_manager import SuppressionManager

client = GoogleSheetsClient("Ivy Bound - Scraped Leads")
client.setup_sheets()
ws = client.input_sheet.sheet1

sm = SuppressionManager()

# Fetch all records
all_values = ws.get_all_values()
headers = [h.lower().strip() for h in all_values[0]]
email_col = headers.index("email") if "email" in headers else 0
status_col = headers.index("status") if "status" in headers else 10

print(f"Headers: {all_values[0]}")
print(f"Email col: {email_col}, Status col: {status_col}")
print(f"Total rows (excluding header): {len(all_values) - 1}")

# Find all rows where status is "pending" but email is suppressed
updates = []
for row_idx, row in enumerate(all_values[1:], start=2):  # 1-indexed, skip header
    if len(row) <= max(email_col, status_col):
        continue
    email = row[email_col].lower().strip()
    status = row[status_col].lower().strip()
    
    if status in ["pending", ""] and email and sm.is_suppressed(email):
        # Mark as "suppressed" so scheduler skips it
        cell = f"{chr(65 + status_col)}{row_idx}"
        updates.append({"range": cell, "values": [["suppressed"]]})

print(f"\nFound {len(updates)} suppressed leads stuck as 'pending'")

if updates:
    # Batch update in chunks of 50 to avoid API limits
    import time
    for i in range(0, len(updates), 50):
        chunk = updates[i:i+50]
        ws.batch_update(chunk, value_input_option="RAW")
        print(f"  Updated rows {i+1}-{min(i+50, len(updates))}")
        time.sleep(1)
    
    print(f"\n✅ Done! Marked {len(updates)} leads as 'suppressed'. Scheduler will now skip them.")
else:
    print("\nNo stuck leads found.")
