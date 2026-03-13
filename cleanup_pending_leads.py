#!/usr/bin/env python3
"""
cleanup_pending_leads.py
------------------------
Scans all PENDING leads in the Google Sheet.
Groups them by school domain.
If a domain has more than 3 pending leads, marks the extras as 'duplicate'
so the scheduler skips them.

Only touches leads with status = '' or 'pending'. Already-sent leads are untouched.
"""

import sys
import os
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient
import mailreef_automation.automation_config as config

MAX_PER_SCHOOL = 3

def get_domain(email: str) -> str:
    """Extract domain from email address."""
    if email and "@" in email:
        return email.strip().lower().split("@")[-1]
    return ""

def main():
    print("🔌 Connecting to Google Sheets...")
    profile = config.CAMPAIGN_PROFILES["IVYBOUND"]
    sheets = GoogleSheetsClient(
        input_sheet_name=profile["input_sheet"],
        replies_sheet_name=profile["replies_sheet"],
        replies_sheet_id=profile.get("replies_sheet_id"),
        replies_worksheet_name=getattr(config, "ACTIVE_REPLIES_WORKSHEET", None)
    )
    sheets.setup_sheets()
    worksheet = sheets.input_sheet.sheet1

    print("📖 Reading all records...")
    records = worksheet.get_all_records()
    headers = worksheet.row_values(1)

    # Identify column indices (1-indexed for gspread)
    try:
        status_col = headers.index("status") + 1
        email_col  = headers.index("email") + 1
    except ValueError as e:
        print(f"❌ Missing expected column: {e}")
        sys.exit(1)

    # Group PENDING rows by school domain
    # domain -> list of (row_number, email, school_name)
    domain_rows = defaultdict(list)
    pending_statuses = {"", "pending"}

    for i, record in enumerate(records):
        row_num = i + 2  # +2 because enumerate is 0-indexed and row 1 is the header
        status = str(record.get("status", "")).strip().lower()
        if status not in pending_statuses:
            continue
        email = str(record.get("email", "")).strip().lower()
        if not email or "@" not in email:
            continue
        domain = get_domain(email)
        if not domain:
            continue
        school_name = record.get("school_name", record.get("company_name", domain))
        domain_rows[domain].append((row_num, email, school_name))

    print(f"\n📊 Found {sum(len(v) for v in domain_rows.values())} pending leads across {len(domain_rows)} unique school domains.\n")

    # Determine which rows need to be marked as duplicate
    rows_to_mark = []  # list of row numbers
    kept_total = 0
    duped_total = 0
    schools_affected = 0

    for domain, rows in domain_rows.items():
        if len(rows) <= MAX_PER_SCHOOL:
            kept_total += len(rows)
            continue
        # Keep first MAX_PER_SCHOOL, mark the rest
        keep = rows[:MAX_PER_SCHOOL]
        extras = rows[MAX_PER_SCHOOL:]
        kept_total += len(keep)
        duped_total += len(extras)
        schools_affected += 1
        school_name = rows[0][2]
        print(f"  🏫 {school_name} (@{domain}): keeping {len(keep)}, marking {len(extras)} as duplicate")
        for row_num, email, _ in extras:
            rows_to_mark.append((row_num, email))

    print(f"\n📝 Summary:")
    print(f"   ✅ Leads to KEEP:      {kept_total}")
    print(f"   🗑️  Leads to DUPLICATE: {duped_total} (across {schools_affected} schools)")

    if not rows_to_mark:
        print("\n🎉 Sheet is already clean! No changes needed.")
        return

    print(f"\n⚙️  Marking {len(rows_to_mark)} rows as 'duplicate' in batches...")

    # Batch update in groups of 30 to stay under Google Sheets 60-writes/min quota
    BATCH_SIZE = 30
    import gspread

    for batch_start in range(0, len(rows_to_mark), BATCH_SIZE):
        batch = rows_to_mark[batch_start:batch_start + BATCH_SIZE]
        cell_updates = []
        for row_num, email in batch:
            cell_updates.append(gspread.Cell(row_num, status_col, "duplicate"))
        try:
            worksheet.update_cells(cell_updates, value_input_option="RAW")
            print(f"   ✅ Updated rows {batch_start + 1}–{batch_start + len(batch)}")
        except Exception as e:
            print(f"   ⚠️  Quota hit, waiting 70s and retrying...")
            time.sleep(70)
            worksheet.update_cells(cell_updates, value_input_option="RAW")
            print(f"   ✅ Retried rows {batch_start + 1}–{batch_start + len(batch)}")
        time.sleep(2.5)  # Stay well under 60 writes/min

    print(f"\n🎉 Done! {duped_total} excess leads marked as 'duplicate'. They will be skipped by the scheduler.")

if __name__ == "__main__":
    main()
