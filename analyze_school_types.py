import logging
import json
from sheets_integration import GoogleSheetsClient

# Configure logging
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"

def analyze_types():
    logger.info("Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    
    try:
        source_sheet = client.client.open(SOURCE_SHEET_NAME).sheet1
        logger.info(f"Reading source: {SOURCE_SHEET_NAME}...")
        records = source_sheet.get_all_records()
    except Exception as e:
        logger.error(f"Failed to load source sheet: {e}")
        return

    # Keywords to check
    keywords = {
        "High School": ["high school", "senior high", "secondary school"],
        "Middle School": ["middle school", "intermediate school"],
        "Junior High": ["junior high"]
    }
    
    stats = {k: 0 for k in keywords}
    total_valid = 0
    total_matched = 0
    
    logger.info("Analyzing records...")
    
    for record in records:
        # Strict validation filter (same as import)
        if str(record.get('business_status', '')).upper() != 'OPERATIONAL':
            continue
        if str(record.get('email.emails_validator.status', '')).upper() != 'RECEIVING':
            continue
        if not str(record.get('email', '')).strip():
            continue
            
        total_valid += 1
        
        # Check text fields
        text_content = (
            str(record.get('name', '')) + " " + 
            str(record.get('subtypes', '')) + " " + 
            str(record.get('category', ''))
        ).lower()
        
        matched_any = False
        for category, terms in keywords.items():
            if any(term in text_content for term in terms):
                stats[category] += 1
                matched_any = True
        
        if matched_any:
            total_matched += 1

    print("\n" + "="*40)
    print("VALIDATED EMAIL COUNTS BY SCHOOL TYPE")
    print("="*40)
    print(f"Total Validated & Operational Emails: {total_valid}")
    print("-" * 40)
    
    for category, count in stats.items():
        print(f"{category}: {count}")
        
    print("-" * 40)
    print(f"Total Matched (Any of above): {total_matched}")
    print(f"Other/Uncategorized: {total_valid - total_matched}")
    print("="*40)

if __name__ == "__main__":
    analyze_types()
