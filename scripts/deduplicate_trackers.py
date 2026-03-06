import os
import sys
import hashlib

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient

def deduplicate_trackers():
    print("🚀 Starting Tracker Deduplication...")
    
    profiles = {
        "IVYBOUND": "Ivy Bound - Reply Tracking",
        "WEB4GURU": "Web4Guru Accountants - Reply Tracking"
    }

    for p_name, sheet_name in profiles.items():
        print(f"\n🔍 Checking {p_name} ({sheet_name})...")
        sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
        sheets.setup_sheets()
        worksheet = sheets.replies_sheet.sheet1
        
        raw_rows = worksheet.get_all_records()
        print(f"  - Total rows found: {len(raw_rows)}")
        
        if not raw_rows:
            continue
            
        unique_rows = []
        seen_keys = set()
        duplicates_count = 0
        
        for row in raw_rows:
            # Create a unique key for the reply
            # Key = (From Email, Subject, Snippet[0:50])
            # This allows multiple DISTINCT replies from same person, but catches same reply logged twice
            
            sender = str(row.get("From Email", "")).lower().strip()
            subject = str(row.get("Subject", "")).lower().strip()
            snippet = str(row.get("Snippet", "")).lower().strip()[:50]
            
            # Timestamp check?? Timestamps might differ slightly between logs.
            # We ignore timestamp for deduplication to compare content.
            
            unique_key = f"{sender}|{subject}|{snippet}"
            
            if unique_key in seen_keys:
                duplicates_count += 1
                continue
                
            seen_keys.add(unique_key)
            unique_rows.append(row)
            
        print(f"  - duplicates found: {duplicates_count}")
        print(f"  - Unique rows retained: {len(unique_rows)}")
        
        if duplicates_count > 0:
            print(f"  📝 Removing {duplicates_count} duplicates...")
            
            # Prepare rows for writing (ordered dict to list)
            # Headers from sheets_integration.py
            headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
            
            clean_values = []
            for row in unique_rows:
                clean_values.append([str(row.get(h, "")) for h in headers])
                
            worksheet.clear()
            worksheet.update('A1', [headers] + clean_values)
            print(f"  ✅ {p_name} deduplicated.")
        else:
            print(f"  ✅ No duplicates found for {p_name}.")

if __name__ == "__main__":
    deduplicate_trackers()
