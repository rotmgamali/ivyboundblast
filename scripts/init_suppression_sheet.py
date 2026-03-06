import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.suppression_manager import SuppressionManager
from sheets_integration import GoogleSheetsClient
from mailreef_automation.automation_config import SUPPRESSION_SHEET_NAME

def init_sheet():
    print(f"🚀 Initializing Master Suppression List: {SUPPRESSION_SHEET_NAME}")
    
    # Ensure the sheet exists (GoogleSheetsClient.setup_sheets() does this for input_sheet)
    try:
        # We use the client to create/verify the sheet
        sheets = GoogleSheetsClient(input_sheet_name=SUPPRESSION_SHEET_NAME)
        sheets.setup_sheets()
        print(f"✅ Sheet '{SUPPRESSION_SHEET_NAME}' verified/created.")
        
        # Now sync the local backfilled data up
        sm = SuppressionManager()
        print("📤 Syncing local suppression database to Google Sheets...")
        sm.sync_to_sheets()
        print("✨ Synchronization complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    init_sheet()
