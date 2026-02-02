import logging
import argparse
import gspread
from datetime import datetime
from sheets_integration import GoogleSheetsClient
from import_leads import map_lead  # Reuse mapping logic

# Configure logging
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"
NEW_SHEET_NAME = "Ivy Bound - Validated Leads Only"

def extract_validated():
    logger.info("Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    gc = client.client
    
    # 1. Read Source
    try:
        source_sheet = gc.open(SOURCE_SHEET_NAME).sheet1
        logger.info(f"Reading source: {SOURCE_SHEET_NAME}...")
        records = source_sheet.get_all_records()
    except Exception as e:
        logger.error(f"Failed to load source: {e}")
        return

    # 2. Filter & Map
    logger.info("Filtering for RECEIVING + OPERATIONAL...")
    valid_rows = []
    
    for record in records:
        # Strict validation filter
        if str(record.get('business_status', '')).upper() != 'OPERATIONAL':
            continue
        if str(record.get('email.emails_validator.status', '')).upper() != 'RECEIVING':
            continue
        if not str(record.get('email', '')).strip():
            continue
            
        # Map using our clean schema
        mapped = map_lead(record)
        valid_rows.append(mapped)

    logger.info(f"Found {len(valid_rows)} validated leads.")

    if not valid_rows:
        logger.warning("No validated leads found. Aborting.")
        return

    # 3. Create New Sheet
    try:
        logger.info(f"Creating new spreadsheet: {NEW_SHEET_NAME}...")
        try:
            new_sh = gc.open(NEW_SHEET_NAME)
            logger.info("Sheet already exists, clearing it...")
            # If exists, clear it
            new_sh.sheet1.clear()
        except gspread.SpreadsheetNotFound:
            new_sh = gc.create(NEW_SHEET_NAME)
            logger.info("Created new sheet.")
        
        # Share with user if possible (user email is in the token usually, but we can just print the URL)
        # We'll just define the headers and write.
        
        headers = [
            "email", "first_name", "last_name", "role", "school_name", 
            "domain", "state", "city", "phone", "status", 
            "email_1_sent_at", "email_2_sent_at", "sender_email", "notes"
        ]
        
        worksheet = new_sh.sheet1
        worksheet.update_title("Validated Leads")
        
        # Prepare data
        data = [headers]
        for item in valid_rows:
            data.append([item.get(h, "") for h in headers])
            
        # Write in batches
        logger.info("Writing data...")
        worksheet.update(data)
        
        # Format Header
        worksheet.format('A1:N1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.4}
        })

        print("\n" + "="*40)
        print("EXTRACTION COMPLETE")
        print("="*40)
        print(f"Spreadsheet: {NEW_SHEET_NAME}")
        print(f"URL: {new_sh.url}")
        print(f"Total Rows: {len(valid_rows)}")
        print("="*40)

    except Exception as e:
        logger.error(f"Failed to create/write to new sheet: {e}")

if __name__ == "__main__":
    extract_validated()
