import logging
import gspread
from datetime import datetime
from sheets_integration import GoogleSheetsClient

# Configure logging
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"
NEW_SHEET_NAME = "Ivy Bound - High & Middle Schools (Validated)"

KEYWORDS = {
    "High School": ["high school", "senior high", "secondary school"],
    "Middle School": ["middle school", "intermediate school"],
    "Junior High": ["junior high"]
}

def is_target_school(record):
    """Check if record matches target school types."""
    text_content = (
        str(record.get('name', '')) + " " + 
        str(record.get('subtypes', '')) + " " + 
        str(record.get('category', ''))
    ).lower()
    
    for category, terms in KEYWORDS.items():
        if any(term in text_content for term in terms):
            return True, category
            
    return False, None

def extract_targeted():
    logger.info("Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    gc = client.client
    
    # 1. Read Source (ALL DATA)
    try:
        source_sheet = gc.open(SOURCE_SHEET_NAME).sheet1
        logger.info(f"Reading source: {SOURCE_SHEET_NAME}...")
        
        # Get ALL data including headers
        all_values = source_sheet.get_all_values()
        headers = all_values[0]
        logger.info(f"Found {len(headers)} columns in source.")
        
        # Convert to records
        records = []
        for row in all_values[1:]:
            record = dict(zip(headers, row))
            records.append(record)
        
        logger.info(f"Total source records: {len(records)}")
        
    except Exception as e:
        logger.error(f"Failed to load source: {e}")
        return

    # 2. Filter: VALIDATED + TARGET SCHOOL TYPES
    logger.info("Filtering for VALIDATED + TARGET SCHOOL TYPES...")
    valid_rows = []
    
    for record in records:
        # Strict validation filter
        if str(record.get('business_status', '')).upper() != 'OPERATIONAL':
            continue
        if str(record.get('email.emails_validator.status', '')).upper() != 'RECEIVING':
            continue
        if not str(record.get('email', '')).strip():
            continue
            
        # Target School Filter
        is_target, category = is_target_school(record)
        if not is_target:
            continue
            
        # Add category for reference
        record['_school_category'] = category
        valid_rows.append(record)

    logger.info(f"Found {len(valid_rows)} target leads.")

    if not valid_rows:
        logger.warning("No target leads found. Aborting.")
        return

    # 3. Create New Sheet with ALL COLUMNS
    try:
        logger.info(f"Creating new spreadsheet: {NEW_SHEET_NAME}...")
        try:
            new_sh = gc.open(NEW_SHEET_NAME)
            logger.info("Sheet already exists, clearing it...")
            new_sh.sheet1.clear()
        except gspread.SpreadsheetNotFound:
            new_sh = gc.create(NEW_SHEET_NAME)
            logger.info("Created new sheet.")
        
        # Use original headers + our category column
        output_headers = headers + ['_school_category']
        
        worksheet = new_sh.sheet1
        worksheet.update_title("Targeted Leads (All Fields)")
        
        # Prepare data
        data = [output_headers]
        for item in valid_rows:
            row = [item.get(h, "") for h in output_headers]
            data.append(row)
            
        # Write
        logger.info(f"Writing {len(valid_rows)} rows with {len(output_headers)} columns...")
        worksheet.update(data)
        
        # Format header row
        worksheet.format('1:1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6}
        })

        print("\n" + "="*50)
        print("EXTRACTION COMPLETE (ALL FIELDS)")
        print("="*50)
        print(f"Spreadsheet: {NEW_SHEET_NAME}")
        print(f"URL: {new_sh.url}")
        print(f"Total Rows: {len(valid_rows)}")
        print(f"Total Columns: {len(output_headers)}")
        print("="*50)
        
        # Print some sample headers to verify
        print("\nSample Headers (first 20):")
        for h in output_headers[:20]:
            print(f"  - {h}")

    except Exception as e:
        logger.error(f"Failed to create/write to new sheet: {e}")

if __name__ == "__main__":
    extract_targeted()
