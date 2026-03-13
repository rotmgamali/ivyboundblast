import os
import sys
import logging
import random
from datetime import datetime
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RANDOMIZE_DATES")

def randomize_dates():
    logger.info("🚀 STARTING DATE RANDOMIZATION")
    
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    try:
        worksheet = sheets.replies_sheet.worksheet("Sheet 1")
        records = worksheet.get_all_records()
        
        # Received At is Column A
        updates = []
        for i, record in enumerate(records):
            row_num = i + 2
            
            # Randomize day between 1 and 13
            random_day = random.randint(1, 13)
            # Standardize hour/min/sec for a clean look, or keep them slightly varied
            random_hour = random.randint(8, 18) # 8 AM to 6 PM
            random_min = random.randint(0, 59)
            
            # Format as YYYY-MM-DD (keeping it simple as per user request "march 1 to march 13")
            new_date = f"2026-03-{random_day:02d}"
            
            updates.append({'range': f'A{row_num}', 'values': [[new_date]]})
            
        if updates:
            # Chunk updates to avoid payload limits
            for j in range(0, len(updates), 100):
                batch = updates[j:j+100]
                worksheet.batch_update(batch)
            logger.info(f"✅ Randomly distributed dates across March 1-13 for {len(updates)} rows.")
            
    except Exception as e:
        logger.error(f"Failed to randomize dates: {e}")

    logger.info("🎉 RANDOMIZATION COMPLETE.")

if __name__ == "__main__":
    randomize_dates()
