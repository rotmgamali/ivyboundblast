import os
import sys
import logging
from typing import List, Dict

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DEDUP")

def deduplicate_sheet():
    logger.info("🚀 Starting Lead Deduplication...")
    
    # 1. Initialize Sheets Client
    client = GoogleSheetsClient(input_sheet_name='Ivy Bound - Campaign Leads')
    client.setup_sheets()
    
    # 2. Fetch all leads
    logger.info("📡 Fetching all leads for deduplication...")
    worksheet = client.input_sheet.sheet1
    all_records = worksheet.get_all_records()
    total_before = len(all_records)
    logger.info(f"✅ Found {total_before} leads total.")
    
    if total_before == 0:
        logger.info("No leads to deduplicate.")
        return

    # 3. Deduplicate in memory
    unique_leads = {} # email -> record
    
    # Priority: replied > email_2_sent > email_1_sent > pending
    status_priority = {
        'replied': 100,
        'email_2_sent': 50,
        'email_1_sent': 20,
        'pending': 10,
        'duplicate': 0,
        'invalid_email': -1
    }

    for record in all_records:
        email = str(record.get('email', '')).lower().strip()
        if not email:
            continue
            
        if email not in unique_leads:
            unique_leads[email] = record
        else:
            # Decide which one to keep
            existing = unique_leads[email]
            existing_priority = status_priority.get(existing.get('status', '').lower(), 0)
            current_priority = status_priority.get(record.get('status', '').lower(), 0)
            
            if current_priority > existing_priority:
                unique_leads[email] = record
            elif current_priority == existing_priority:
                # If priority is same, keep the one with more info (e.g. school_name)
                if len(str(record.get('school_name', ''))) > len(str(existing.get('school_name', ''))):
                    unique_leads[email] = record

    total_after = len(unique_leads)
    logger.info(f"📊 Deduplication Result: {total_before} -> {total_after} (Removed {total_before - total_after})")

    if total_before == total_after:
        logger.info("✨ No duplicates found. Sheet is clean.")
        return

    # 4. Overwrite Sheet
    logger.info("🧹 Clearing and re-writing sheet with unique leads...")
    # Get headers
    headers = worksheet.row_values(1)
    
    # Clear worksheet (preserves headers if we use our helper, but worksheet.clear() is fine too if we re-add)
    worksheet.clear()
    worksheet.append_row(headers)
    
    # Batch write unique records
    unique_rows = []
    # Use the client's internal mapping logic to ensure consistency
    for email, lead in unique_leads.items():
        row = client._map_data_to_row(lead, headers)
        unique_rows.append(row)
    
    # Batch update
    if unique_rows:
        logger.info(f"Writing {len(unique_rows)} unique leads back to the sheet...")
        # Break into chunks of 1000 to avoid large request errors
        chunk_size = 5000
        for i in range(0, len(unique_rows), chunk_size):
            chunk = unique_rows[i:i + chunk_size]
            worksheet.append_rows(chunk, value_input_option='USER_ENTERED')
            logger.info(f"  ...Wrote chunk {i//chunk_size + 1}")
    
    logger.info("🎉 Deduplication COMPLETE.")

if __name__ == "__main__":
    deduplicate_sheet()
