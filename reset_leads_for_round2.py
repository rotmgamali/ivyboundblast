import os
import sys
import logging
from typing import List, Set

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ROUND2_RESET")

def reset_for_round2():
    logger.info("🚀 Starting Lead Reset for Round 2 Outreach...")
    
    # 1. Initialize Sheets Client
    client = GoogleSheetsClient(input_sheet_name='Ivy Bound - Campaign Leads')
    client.setup_sheets()
    
    # 2. Fetch all repliers to exclude
    logger.info("📡 Fetching exclusion list from Reply Tracking...")
    replies_ws = client.replies_sheet.sheet1
    all_replies = replies_ws.get_all_records()
    excluded_emails = {str(r.get('From Email', '')).lower().strip() for r in all_replies}
    logger.info(f"✅ Found {len(excluded_emails)} replies to exclude.")
    
    # 3. Fetch all leads
    logger.info("📡 Fetching leads from main sheet...")
    # Use internal batch fetch for speed if possible, or just raw records
    # 3. Fetch all leads
    logger.info("📡 Fetching leads from main sheet...")
    worksheet = client.input_sheet.sheet1
    
    # 4. Filter and Identify rows to reset
    # We want to reset 'email_1_sent', 'email_2_sent', 'sent'
    # BUT EXCLUDE 'replied', 'invalid_email', 'pending', and anyone in excluded_emails
    
    reset_count = 0
    # Get column index for 'status'
    headers = worksheet.row_values(1)
    try:
        status_col = headers.index('status') + 1
        email_col = headers.index('email') + 1
    except ValueError:
        logger.error(f"❌ Could not find 'status' or 'email' column in headers. Found: {headers}")
        return

    # To be extremely safe and fast, we'll build a batch update of the status column
    status_values = worksheet.col_values(status_col)
    email_values = worksheet.col_values(email_col)
    
    new_status_col = [headers[status_col-1]] # Keep header
    
    for i in range(1, len(status_values)): # Skip header
        current_status = status_values[i].lower()
        email = email_values[i].lower().strip()
        
        should_reset = False
        if current_status in ['email_1_sent', 'email_2_sent', 'sent']:
            if email not in excluded_emails:
                should_reset = True
        
        if should_reset:
            new_status_col.append('pending')
            reset_count += 1
        else:
            new_status_col.append(status_values[i]) # Keep as is

    # 5. Execute Update
    if reset_count > 0:
        logger.info(f"🔄 Resetting {reset_count} leads to 'pending'...")
        
        # Build the range: e.g. 'G1:G30000' where Status is column G
        from gspread.utils import rowcol_to_a1
        range_start = rowcol_to_a1(1, status_col)
        range_end = rowcol_to_a1(len(new_status_col), status_col)
        update_range = f"{range_start}:{range_end}"
        
        # Prepare for update (gspread expects list of lists for rows)
        update_data = [[v] for v in new_status_col]
        
        try:
            worksheet.update(update_range, update_data)
            logger.info(f"🎉 SUCCESS: {reset_count} leads are now pending for Round 2.")
        except Exception as e:
            logger.error(f"❌ Failed to update sheet: {e}")
    else:
        logger.info("ℹ️ No leads found that meet the reset criteria.")

if __name__ == "__main__":
    reset_for_round2()
