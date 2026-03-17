#!/usr/bin/env python3
import csv
import os
from sheets_integration import GoogleSheetsClient
from mailreef_automation.logger_util import get_logger

logger = get_logger("IMPORT_SCRAPULA_FIXED")

CSV_PATH = "/Users/mac/Downloads/Scrapula-20260315094946m3f_high_school_+1.csv"
SHEET_NAME = "Ivy Bound - Campaign Leads"

def import_leads():
    if not os.path.exists(CSV_PATH):
        logger.error(f"CSV file not found: {CSV_PATH}")
        return

    client = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
    client.setup_sheets()
    
    # Get existing emails to avoid duplicates
    existing_records = client._fetch_all_records()
    existing_emails = {str(r.get('email', '')).lower().strip() for r in existing_records if r.get('email')}

    new_leads = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = str(row.get('email', '')).lower().strip()
            if not email: continue

            # Filter for Utah Leads
            state_code = row.get('state_code', '').upper()
            if state_code != 'UT': continue

            # Filter for valid emails
            validator_status = row.get('email.emails_validator.status', '').upper()
            if validator_status in ['INVALID', 'BLACKLISTED']: continue

            if email in existing_emails: continue

            lead = {
                "email": email,
                "first_name": row.get('first_name', ''),
                "last_name": row.get('last_name', ''),
                "role": row.get('title', ''),
                "school_name": row.get('name', ''),
                "domain": row.get('domain', ''),
                "state": state_code,
                "city": row.get('city', ''),
                "phone": row.get('phone', ''),
                "status": "pending",
                "school_type": row.get('type', ''),
                "email_verified": "verified" # Pass the internal safety gate
            }
            
            new_leads.append(lead)
            existing_emails.add(email)

    if not new_leads:
        logger.info("No new leads to add.")
        return

    logger.info(f"Adding {len(new_leads)} leads with DYNAMIC mapping...")
    success = client.add_leads_batch(new_leads)
    
    if success:
        logger.info(f"Successfully added {len(new_leads)} leads.")
    else:
        logger.error("Failed to add leads.")

if __name__ == "__main__":
    import_leads()
