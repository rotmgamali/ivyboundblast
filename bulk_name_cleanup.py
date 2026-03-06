import time
from sheets_integration import GoogleSheetsClient
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHEET_NAME = "Ivy Bound - Campaign Leads"

# Terms that should be cleared if found in the first_name column
BLOCKLIST_TERMS = [
    "administrator", "admin", "info", "office", "contact", 
    "principal", "manager", "leader", "team", "coordinator", 
    "assistant", "staff"
]

def cleanup_names():
    logger.info(f"🚀 Starting bulk cleanup for '{SHEET_NAME}'...")
    sheets = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
    sheets.setup_sheets()
    
    # Get all records to identify which rows need updating
    records = sheets.input_sheet.sheet1.get_all_values()
    if not records:
        logger.error("No records found.")
        return

    headers = records[0]
    try:
        first_name_idx = headers.index('first_name') + 1 # 1-indexed for gspread
    except ValueError:
        logger.error("Could not find 'first_name' column.")
        return

    updates = []
    cleaned_count = 0
    
    # Start from row 2 (first data row)
    for row_idx, row in enumerate(records[1:], start=2):
        name = str(row[first_name_idx-1]).strip()
        if not name:
            continue
            
        lower_name = name.lower()
        if any(term in lower_name for term in BLOCKLIST_TERMS):
            # Queue for clearing
            updates.append({
                'range': f'B{row_idx}' if first_name_idx == 2 else None, # Hardcoded optimization if first_name is col B
                'index': row_idx,
                'old_name': name
            })
            cleaned_count += 1

    if not updates:
        logger.info("✅ No bad names found to clean.")
        return

    logger.info(f"🧹 Found {cleaned_count} names to clear. Starting batch update...")
    
    # We use batch_update to clear values to avoid hitting quota
    # Since we only want to clear the first_name column, we'll create cells for each row
    
    batch_cells = []
    # Re-identify the column letter for gspread format
    col_letter = chr(64 + first_name_idx) # Works for A-Z
    
    # Process in chunks of 500 to be safe
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        logger.info(f"Processing chunk {i//chunk_size + 1}...")
        
        batch_requests = []
        for update in chunk:
            batch_requests.append({
                'range': f'{col_letter}{update["index"]}',
                'values': [['']]
            })
            
        try:
            sheets.input_sheet.sheet1.batch_update(batch_requests)
            logger.info(f"  ✓ Cleared {len(chunk)} names.")
            time.sleep(1) # Small delay to respect quota
        except Exception as e:
            logger.error(f"  ❌ Batch update failed: {e}")
            break

    logger.info(f"✅ Cleanup complete. Total names cleared: {cleaned_count}")

if __name__ == "__main__":
    cleanup_names()
