import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("REORG")

def reorganize_sheets():
    logger.info("🚀 STARTING SHEET REORGANIZATION")
    
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    # 1. Delete "Feb" sheet
    try:
        feb_worksheet = sheets.replies_sheet.worksheet("Feb")
        sheets.replies_sheet.del_worksheet(feb_worksheet)
        logger.info("✅ Deleted 'Feb' worksheet.")
    except Exception as e:
        logger.warning(f"Could not delete 'Feb': {e}")

    # 2. Rename "March" to "Sheet 1" (Renaming to avoid conflicts if Sheet 1 exists)
    try:
        # Check if Sheet 1 already exists
        try:
            old_s1 = sheets.replies_sheet.worksheet("Sheet 1")
            old_s1.update_title(f"Old Sheet 1_{int(datetime.now().timestamp())}")
            logger.info("Renamed existing 'Sheet 1' to avoid conflict.")
        except:
            pass
            
        march_worksheet = sheets.replies_sheet.worksheet("March")
        march_worksheet.update_title("Sheet 1")
        logger.info("✅ Renamed 'March' to 'Sheet 1'.")
    except Exception as e:
        logger.error(f"Could not rename 'March' to 'Sheet 1': {e}")
        return

    # 3. Update all dates to March 2026
    try:
        worksheet = sheets.replies_sheet.worksheet("Sheet 1")
        records = worksheet.get_all_records()
        
        # Received At is Column A
        updates = []
        for i, record in enumerate(records):
            row_num = i + 2
            current_date = str(record.get('Received At', ''))
            
            # If it's empty or doesn't look like March 2026, set it to a standard March date
            # Or just blindly overwrite as requested: "change all the dates in the entire sheet to mark dates"
            # I will use the existing date if it contains "2026-03" or "March", else set to 2026-03-13
            
            new_date = "2026-03-13" 
            if "2026-03" in current_date:
                new_date = current_date.split('T')[0] if 'T' in current_date else current_date
            
            updates.append({'range': f'A{row_num}', 'values': [[new_date]]})
            
        if updates:
            # Chunk updates
            for j in range(0, len(updates), 100):
                batch = updates[j:j+100]
                worksheet.batch_update(batch)
            logger.info(f"✅ Normalized dates to March 2026 for {len(updates)} rows.")
            
    except Exception as e:
        logger.error(f"Failed to update dates: {e}")

    logger.info("🎉 REORGANIZATION COMPLETE.")

if __name__ == "__main__":
    reorganize_sheets()
