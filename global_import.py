
import sys
import os
import gspread
import logging
from datetime import datetime
from collections import Counter

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

# Configuration
SOURCE_SHEETS = [
    "Outscraper-20260203225955m87_high_school_%2B1",
    "Outscraper-20260204095850m31_high_school_%2B1"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GLOBAL_IMPORTER")

def run_global_import():
    client = GoogleSheetsClient()
    client.setup_sheets()
    target_ws = client.input_sheet.sheet1
    
    # 1. Fetch ALL existing emails for final deduplication
    logger.info("📡 Fetching existing emails from target sheet...")
    target_emails = set(e.strip().lower() for e in target_ws.col_values(1) if '@' in str(e))
    logger.info(f"Target sheet already contains {len(target_emails)} unique emails.")
    
    target_headers = target_ws.row_values(1)
    header_map = {h.lower().strip().replace(' ', '_'): i for i, h in enumerate(target_headers)}
    
    new_rows = []
    global_emails_found = set()
    
    # 2. Process each source sheet
    for sheet_name in SOURCE_SHEETS:
        logger.info(f"📖 Processing Source: {sheet_name}...")
        try:
            source_ss = client.client.open(sheet_name)
            source_records = source_ss.sheet1.get_all_records()
            logger.info(f"Found {len(source_records)} records in {sheet_name}.")
            
            sheet_new_count = 0
            for row in source_records:
                # Try multiple possible email keys
                email = row.get('email', row.get('email_1', ''))
                if not email or '@' not in str(email):
                    continue
                
                email = str(email).strip().lower()
                
                # Deduplicate against:
                # 1. Target sheet
                # 2. Other leads in this run (global_emails_found)
                if email in target_emails or email in global_emails_found:
                    continue
                
                # --- Mapping ---
                subtypes = str(row.get('subtypes', '')).lower()
                if any(x in subtypes for x in ['private', 'catholic', 'christian']):
                    school_type = 'Private'
                else:
                    school_type = 'Public'
                
                new_row = [''] * len(target_headers)
                
                def set_val(col_name, val):
                    if col_name in header_map:
                        new_row[header_map[col_name]] = str(val)
                
                set_val('email', email)
                set_val('first_name', "Administrator")
                set_val('last_name', "")
                set_val('role', "Administrator")
                set_val('school_name', row.get('name', ''))
                set_val('school_type', school_type)
                set_val('domain', row.get('site', row.get('website', '')))
                set_val('state', row.get('state', ''))
                set_val('city', row.get('city', ''))
                set_val('phone', row.get('phone', ''))
                set_val('status', 'pending')
                set_val('notes', f"Global Import from {sheet_name}")
                
                new_rows.append(new_row)
                global_emails_found.add(email)
                sheet_new_count += 1
            
            logger.info(f"Added {sheet_new_count} unique leads from this sheet.")
            
        except Exception as e:
            logger.error(f"Failed to process {sheet_name}: {e}")

    # 3. Batch Append
    if new_rows:
        logger.info(f"🚀 Appending TOTAL {len(new_rows)} new unique leads to Sheets...")
        # Break into chunks to avoid timeout
        chunk_size = 500
        for i in range(0, len(new_rows), chunk_size):
            chunk = new_rows[i:i + chunk_size]
            logger.info(f"Uploading batch {i//chunk_size + 1}...")
            target_ws.append_rows(chunk)
        logger.info("✅ Global Import complete!")
    else:
        logger.info("No new unique leads found across both spreadsheets.")

if __name__ == "__main__":
    run_global_import()
