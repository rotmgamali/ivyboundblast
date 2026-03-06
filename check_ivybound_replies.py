import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient
from mailreef_automation.automation_config import CAMPAIGN_PROFILES

def count_replies():
    profile = CAMPAIGN_PROFILES["IVYBOUND"]
    sheet_name = profile["replies_sheet"]
    
    print(f"Connecting to Google Sheets to check '{sheet_name}'...")
    
    try:
        # Initialize the client with specific sheet names
        sheets = GoogleSheetsClient(
            input_sheet_name=profile["input_sheet"],
            replies_sheet_name=sheet_name
        )
        sheets.setup_sheets()
        
        # Open the replies sheet (it's sheet1 by default in setup_sheets)
        replies_sheet = sheets.replies_sheet.sheet1
        
        # Get all records to count (excluding header)
        records = replies_sheet.get_all_records()
        total_replies = len(records)
        
        # Now check the Leads sheet
        input_sheet = sheets.input_sheet.sheet1
        input_records = input_sheet.get_all_records()
        replied_status_count = sum(1 for r in input_records if (r.get("status") or "").lower() == "replied")
        
        print(f"\n==========================================")
        print(f"📊 CAMPAIGN: IVYBOUND")
        print(f"📝 SHEET: {sheet_name}")
        print(f"✅ TOTAL REPLIES TRACKED: {total_replies}")
        print(f"🎯 LEADS MARKED 'REPLIED': {replied_status_count}")
        print(f"==========================================\n")
        
        if total_replies != replied_status_count:
            print(f"⚠️  Note: There is a discrepancy between tracked replies ({total_replies}) and leads marked as 'replied' ({replied_status_count}).")
            print(f"This is normal if some replies were from addresses not in the initial lead list or if tracking is still syncing.")
            
        return total_replies

    except Exception as e:
        print(f"❌ Error counting replies: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    count_replies()
