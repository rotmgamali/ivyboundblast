import os
import sys
import logging
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient
from classify_replies import classify_replies_pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MIGRATION")

def migrate_feb_to_march():
    logger.info("🚀 STARTING FEB TO MARCH MIGRATION")
    
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    try:
        feb_worksheet = sheets.replies_sheet.worksheet("Feb")
        march_worksheet = sheets.replies_sheet.worksheet("March")
    except Exception as e:
        logger.error(f"Could not find worksheets: {e}")
        return

    # 1. Fetch all records from Feb
    feb_records = feb_worksheet.get_all_records()
    logger.info(f"Loaded {len(feb_records)} records from Feb.")
    
    # 2. Filter for actionable leads (Sentiment Column H)
    # Check Sentiment column (Col 8) - handle 'ACTIONABLE 🟢' and similar
    actionable_leads = [r for r in feb_records if 'actionable' in str(r.get('Sentiment', '')).lower()]
    logger.info(f"Found {len(actionable_leads)} actionable leads in Feb.")
    
    if not actionable_leads:
        logger.info("No actionable leads found in Feb. Nothing to migrate.")
        return

    # 3. Get existing March records for deduplication
    march_records = march_worksheet.get_all_records()
    march_thread_ids = {str(r.get('Thread ID', '')) for r in march_records if r.get('Thread ID')}
    
    # 4. Filter out duplicates
    new_leads = []
    for lead in actionable_leads:
        thread_id = str(lead.get('Thread ID', ''))
        if thread_id and thread_id in march_thread_ids:
            logger.info(f"Skipping duplicate thread in March: {thread_id}")
            continue
        new_leads.append(lead)
    
    logger.info(f"Preparing to migrate {len(new_leads)} new leads to March.")
    
    if not new_leads:
        logger.info("All actionable leads from Feb already exist in March.")
    else:
        # 5. Append new leads to March
        # Map back to row format (A-M)
        rows_to_append = []
        for lead in new_leads:
            row = [
                lead.get('Received At', ''),
                lead.get('From Email', ''),
                lead.get('From Name', ''),
                lead.get('School Name', ''),
                lead.get('Role', ''),
                lead.get('Subject', ''),
                lead.get('Entire Thread', ''),
                'actionable', # Mark as actionable to ensure they are at least initially green
                lead.get('Original Sender', ''),
                lead.get('Original Subject', ''),
                lead.get('Thread ID', ''),
                lead.get('Action Taken', ''),
                lead.get('Notes', '')
            ]
            rows_to_append.append(row)
        
        march_worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        logger.info(f"✅ Successfully appended {len(rows_to_append)} rows to March.")

    # 6. Re-run classification on March to "recheck them"
    logger.info("🔄 Re-running classification on March to verify all leads...")
    classify_replies_pass()
    logger.info("🎉 MIGRATION AND RE-VERIFICATION COMPLETE.")

if __name__ == "__main__":
    migrate_feb_to_march()
