import os
import json
from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import mailreef_automation.automation_config as config
from dotenv import load_dotenv

load_dotenv()

# THE EXISTING FILTER LOGIC
IVY_FRAGMENTS = [
    "quick question", "supporting families", "test prep",
    "merit scholarship", "differentiation and outcomes", 
    "enhancing value", "supporting student-athletes", 
    "boosting enrollment", "academic outcomes",
    "families and college prep", "curriculum", "ivy bound"
]

WARMUP_PATTERNS = [
    "bug fixes", "software training", "expense reports", "rotation",
    "sales report", "feedback request", "performance reviews",
    "volunteer day", "vendor negotiations", "health benefits",
    "job application", "team building", "intern welcome",
    "strategic planning", "remote work", "client meeting",
    "project update", "policy reminder", "office move",
    "company picnic", "birthday celebration", "quarterly goals"
]

def is_warmup(from_email: str, subject: str, lead_list: set) -> bool:
    if not from_email: return True
    if from_email.lower().strip() in lead_list:
        return False # LEAD-FIRST LOGIC
        
    if not subject: return True
    subj_lower = subject.lower()
    for frag in IVY_FRAGMENTS:
        if frag in subj_lower: return False
    for pattern in WARMUP_PATTERNS:
        if pattern in subj_lower: return True
    return True

def run_deep_audit():
    # 1. Load all Lead Emails from Sheets
    print("📊 Loading leads from Google Sheets...")
    lead_emails = set()
    for profile in ["IVYBOUND", "STRATEGY_B"]:
        c = config.CAMPAIGN_PROFILES[profile]
        sheets = GoogleSheetsClient(input_sheet_name=c['input_sheet'], replies_sheet_name=c["replies_sheet"])
        sheets.setup_sheets()
        records = sheets.input_sheet.sheet1.get_all_records()
        for r in records:
            email = str(r.get('email', '')).lower().strip()
            if email: lead_emails.add(email)
    
    print(f"✅ Loaded {len(lead_emails)} total leads.")

    # 2. Fetch Mailreef
    client = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    page = 1
    total_scanned = 0
    confirmed_replies = []
    suspicious_matches = []
    
    print("📡 Scanning Mailreef inboxes...")
    
    while True:
        result = client.get_global_inbound(page=page, display=100)
        batch = result.get("data", [])
        if not batch: break
        
        for msg in batch:
            total_scanned += 1
            from_email = str(msg.get("from_email", "")).lower().strip()
            subject = (msg.get("subject_line") or "").lower()
            snippet = (msg.get("snippet_preview") or "").lower()
            
            # CHECK: Is this sender in our lead list?
            if from_email in lead_emails:
                # SENDER IS A LEAD. 
                # Does the current logic catch it?
                if is_warmup(from_email, subject, lead_emails):
                    # 🚨 DANGER: This is a lead email that we are FILTERING OUT.
                    suspicious_matches.append(msg)
                else:
                    # Logic is correctly catching it
                    confirmed_replies.append(msg)
        
        if len(batch) < 100 or page >= 50: break
        page += 1

    print("\n" + "="*80)
    print(f"🔎 FILTER AUDIT REPORT")
    print("="*80)
    print(f"Total Emails Scanned:  {total_scanned}")
    print(f"Lead-Derived Emails:   {len(confirmed_replies) + len(suspicious_matches)}")
    print(f"✅ Correctly Found:     {len(confirmed_replies)}")
    print(f"❌ MISSED BY FILTER:   {len(suspicious_matches)}")
    print("="*80)
    
    if suspicious_matches:
        print("\n🚨 URGENT: REAL LEAD EMAILS BLOCKED BY FILTER:")
        for i, m in enumerate(suspicious_matches, 1):
            print(f"{i}. [{m['from_email']}] | Subj: {m['subject_line']}")
            print(f"   Snippet: {m['snippet_preview']}\n")
    else:
        print("\n🏆 GREAT NEWS: Every single email from a known lead was successfully identified by the current filter.")

if __name__ == "__main__":
    run_deep_audit()
