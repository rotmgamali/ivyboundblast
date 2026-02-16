import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.automation_config import CAMPAIGN_PROFILES
from sheets_integration import GoogleSheetsClient

def purge_sheet(profile_name):
    print(f"🧹 Purging unrelated entries from {profile_name} Reply Tracking...")
    
    profile = CAMPAIGN_PROFILES.get(profile_name)
    if not profile:
        print(f"❌ Profile {profile_name} not found.")
        return

    subject_patterns = profile.get("subject_patterns", [])
    if not subject_patterns:
        print(f"⚠️ No subject patterns defined for {profile_name}. Skipping purge to avoid deleting everything.")
        return

    sheet_name = profile.get("replies_sheet")
    print(f"  - Sheet: {sheet_name}")
    print(f"  - Patterns: {subject_patterns}")

    try:
        sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
        sheets.setup_sheets()
        
        # We need to access the replies sheet
        replies_worksheet = sheets.replies_sheet.sheet1
        all_rows = replies_worksheet.get_all_values()
        
        if not all_rows:
            print("  - Sheet is empty.")
            return

        headers = all_rows[0]
        rows = all_rows[1:]
        
        # Identify the 'subject' column
        try:
            subj_idx = [h.lower().strip() for h in headers].index('subject')
        except ValueError:
            print("  ❌ Could not find 'subject' column in sheet.")
            return

        filtered_rows = [all_rows[0]] # Keep headers
        removed_count = 0
        
        for row in rows:
            if len(row) <= subj_idx:
                filtered_rows.append(row)
                continue
                
            subject = row[subj_idx]
            # Check if it matches ANY pattern
            matches = any(p.lower() in subject.lower() for p in subject_patterns)
            
            # Additional check: If it's a "Re: ..." it might be a reply to an outreach
            # But the patterns are usually in the original subject
            
            if matches:
                filtered_rows.append(row)
            else:
                removed_count += 1
        
        if removed_count > 0:
            print(f"  - Removing {removed_count} unrelated rows...")
            replies_worksheet.clear()
            replies_worksheet.update('A1', filtered_rows)
            print("  ✅ Purge complete!")
        else:
            print("  ✅ No unrelated rows found.")

    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    # Target Web4Guru Accountants primarily as requested
    purge_sheet("WEB4GURU_ACCOUNTANTS")
    purge_sheet("STRATEGY_B")
