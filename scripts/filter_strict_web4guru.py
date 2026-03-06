import os
import sys
import re

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient

# --- TEMPLATE SIGNATURES ---
# Constants from our templates that should appear in the reply's quoted text
# or subject line.
SUBJECT_KEYWORDS = [
    "question for", 
    "re: question for"
]

BODY_FRAGMENTS = [
    "taking on new clients this quarter",
    "using any ai tools",
    "high value clients in their first month",
    "ai-driven system",
    "without spending hours on manual outreach",
    "builds trust by starting real conversations",
    "replicate those results for you"
]

def is_valid_reply(subject: str, snippet: str, body: str = "") -> bool:
    subject = subject.lower()
    snippet = snippet.lower()
    body = body.lower()
    
    # 1. Check Subject
    # It usually starts with "re: question for" followed by company name
    for k in SUBJECT_KEYWORDS:
        if k in subject:
            return True
            
    # 2. Check Body/Snippet for Quoted Text
    # If the reply quotes our email, it should contain one of regular phrases
    content = body + " " + snippet
    for frag in BODY_FRAGMENTS:
        if frag in content:
            return True
            
    return False

def filter_strict():
    print("🚀 Starting Strict Filter for Web4Guru...")
    
    sheet_name = "Web4Guru Accountants - Reply Tracking"
    sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    raw_rows = worksheet.get_all_records()
    print(f"  🔍 Found {len(raw_rows)} total rows.")
    
    if not raw_rows:
        return
        
    kept_rows = []
    removed_count = 0
    
    for row in raw_rows:
        subject = str(row.get("Subject", ""))
        snippet = str(row.get("Snippet", ""))
        # We don't have full body in the sheet, usually just snippet.
        # But reconcile_replies might have logged body if we modified it?
        # Standard sheet has 'Snippet'.
        
        # NOTE: If we only have snippet (first 200 chars), we might miss the quoted text if it's at the bottom.
        # However, many replies put the quoted text right after.
        # But 'Snippet' is usually the *reply* content, not the quoted text.
        # So checking snippet for *our* text might yield False Positives if the user types "I am not taking on new clients".
        # Wait. "taking on new clients this quarter?" is our question.
        # If they reply "Yes, we are taking on new clients", that's a valid reply but doesn't contain our exact template text.
        
        # The user said: "filter out ... a reply that doesnt follow our exact template for subject and body"
        # This probably means the *thread* should look like it came from our template.
        # The most reliable indicator is the SUBJECT.
        # "Question for <Company>"
        
        # If the subject is "Networking Event" or "Vacation Policy", it matches NOTHING from our template.
        # So relying on Subject is safer and probably what the user intends given the noise we saw ("Cycling Club", etc).
        
        if is_valid_reply(subject, snippet):
            # Transform back to list
             headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
             kept_rows.append([str(row.get(h, "")) for h in headers])
        else:
            removed_count += 1
            # print(f"  ❌ Filtering out: {subject} | {snippet[:30]}...")

    print(f"  ✅ Kept: {len(kept_rows)}")
    print(f"  🗑️ Removed: {removed_count}")
    
    if removed_count > 0:
        print("  📝 Updating sheet...")
        headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
        worksheet.clear()
        worksheet.update('A1', [headers] + kept_rows)
        print("  ✨ Strict filter applied.")
    else:
        print("  ✅ Sheet is already clean.")

if __name__ == "__main__":
    filter_strict()
