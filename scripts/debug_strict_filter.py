import os
import sys
import re

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient

# --- TEMPLATE SIGNATURES ---
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
    
    # Check Subject
    for k in SUBJECT_KEYWORDS:
        if k in subject:
            return True
            
    # Check Body/Snippet
    content = body + " " + snippet
    for frag in BODY_FRAGMENTS:
        if frag in content:
            return True
            
    return False

def debug_filter():
    print("🚀 Debugging Strict Filter for Web4Guru...")
    
    sheet_name = "Web4Guru Accountants - Reply Tracking"
    sheets = GoogleSheetsClient(replies_sheet_name=sheet_name)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    # We might have cleared it already... 
    # But wait, if we cleared it, checking it now will show 0.
    # I should have printed what I was removing.
    # The previous run output said "Removed: 23" and "Updating sheet...".
    # So the sheet is EMPTY now (except headers).
    
    # I need to re-populate it or check the leads I *thought* were replies.
    # I can run reconcile_replies again to fetch them back?
    # Or just check the log of what reconcile found.
    
    print("⚠️ Sheet is likely empty now. Re-running reconcile to see what we find...")
    # This is risky if I don't change reconcile loop.
    
    # Let's just interpret the previous failure.
    # Subject: "Question for {{ company_name }}"
    # Real replies might be: "Re: Question for Acme"
    # My code checked: `if k in subject`.
    # "question for" in "re: question for acme" -> True.
    # So why did it fail?
    
    # Maybe the subject in the sheet was NOT "Question for...".
    # Maybe it was "Re: Accounting Services" or something else?
    
    # I can't undo the clear easily.
    # I should re-run reconcile but print the subjects it finds.
    pass

if __name__ == "__main__":
    debug_filter()
