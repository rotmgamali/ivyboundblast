
import sys
import os
import gspread
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

# Configuration
SOURCE_SHEET_NAME = "Outscraper-20260204095850m31_high_school_%2B1"
TARGET_SHEET_INDEX = 0 # First sheet of the Main Spreadsheet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IMPORTER")

def import_source_to_leads():
    client = GoogleSheetsClient()
    client.setup_sheets() # Critical: Initialize sheets connection
    
    # 1. Connect to Source
    logger.info(f"Reading from source: {SOURCE_SHEET_NAME}")
    try:
        source_ss = client.client.open(SOURCE_SHEET_NAME)
        source_records = source_ss.sheet1.get_all_records()
        logger.info(f"Found {len(source_records)} records in source.")
    except Exception as e:
        logger.error(f"Failed to open source sheet: {e}")
        return

    # 2. Get Existing Leads (to prevent duplicates)
    existing_emails = set()
    try:
        current_leads = client.get_pending_leads(limit=10000) # Get as many as possible
        # Also need to check processed leads? 
        # Better: Fetch ALL emails from the sheet column to be 100% sure
        worksheet = client.input_sheet.sheet1
        all_emails = worksheet.col_values(1) # Assuming Email is Column A (1 sets 'email' key)
        # Actually col_values(1) might return 'email' header too
        existing_emails = set(e.strip().lower() for e in all_emails if '@' in str(e))
        logger.info(f"Found {len(existing_emails)} existing emails in target.")
    except Exception as e:
        logger.warning(f"Could not fetch existing emails (Duplicate check might fail): {e}")

    # 3. Map & Prepare Rows
    target_headers = worksheet.row_values(1)
    
    # Auto-Migrate: Add 'school_type' if missing
    if 'school_type' not in [h.lower() for h in target_headers]:
        logger.info("⚠️ 'school_type' column missing. Adding it now...")
        new_col_index = len(target_headers) + 1
        worksheet.update_cell(1, new_col_index, "school_type")
        worksheet.format(f"{chr(64+new_col_index)}1", {'textFormat': {'bold': True}}) # Basic char map (A=65) failure for >26 cols but safe here
        target_headers = worksheet.row_values(1) # Refresh
        logger.info("✓ Added 'school_type' header.")

    # Re-build map
    header_map = {h.lower().strip().replace(' ', '_'): i for i, h in enumerate(target_headers)}
    
    new_rows = []
    skipped_count = 0
    
    for i, row in enumerate(source_records):
        email = row.get('email', '') # CORRECT KEY
        
        # Debug first few rows
        if i < 5:
            logger.info(f"Row {i} email raw: '{email}'")
            
        if not email or '@' not in str(email):
            continue
            
        email = email.strip().lower()
        # DE-DUPLICATION DISABLED BY USER REQUEST
        # if email in existing_emails:
        #     if skipped_count < 5:
        #        logger.info(f"Skipping duplicate: {email}")
        #     skipped_count += 1
        #     continue
            
        # Mapping Logic
        # Parse 'subtypes' for school_type
        subtypes = str(row.get('subtypes', '')).lower()
        if 'private' in subtypes or 'catholic' in subtypes or 'christian' in subtypes:
            school_type = 'Private'
        elif 'public' in subtypes or 'district' in subtypes:
            school_type = 'Public'
        else:
            # User said "these are public schools" -> Default
            school_type = 'Public' 
            
        # Parse Name
        school_name = row.get('name', '')
        
        # Generic First Name
        first_name = "Administrator" # Safe default for generic email
        last_name = ""
        role = "Administrator"
        
        # Prepare a sparse row (list of empty strings)
        new_row_data = [''] * len(target_headers)
        
        def set_val(col_name, val):
            if col_name in header_map:
                new_row_data[header_map[col_name]] = str(val)
        
        set_val('email', email)
        set_val('first_name', first_name)
        set_val('last_name', last_name)
        set_val('role', role)
        set_val('school_name', school_name)
        set_val('school_type', school_type)
        set_val('domain', row.get('site', row.get('website', '')))
        set_val('state', row.get('state', ''))
        set_val('city', row.get('city', ''))
        set_val('phone', row.get('phone', ''))
        set_val('status', 'pending')
        set_val('notes', f"Imported from {SOURCE_SHEET_NAME}")
        
        new_rows.append(new_row_data)
        existing_emails.add(email)

    # 4. Append
    if new_rows:
        logger.info(f"Appending {len(new_rows)} new leads...")
        try:
            # Batch append
            worksheet.append_rows(new_rows)
            logger.info("✅ Import successful!")
        except Exception as e:
            logger.error(f"Import failed: {e}")
    else:
        logger.info("No new unique leads found to import.")

if __name__ == "__main__":
    import_source_to_leads()
