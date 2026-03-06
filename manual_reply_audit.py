import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import mailreef_automation.automation_config as auth_config

# Dummy is_warmup logic based on what's in reply_watcher.py
def is_warmup_manual(lead_emails, from_email, subject):
    if not from_email: return True
    if from_email.lower().strip() in lead_emails: return False
    if not subject: return True
    
    subj_lower = subject.lower()
    ivy_fragments = [
        "quick question", "supporting families", "test prep",
        "merit scholarship", "differentiation and outcomes", "enhancing value",
        "supporting student-athletes", "boosting enrollment", "academic outcomes",
        "families and college prep", "curriculum", "ivy bound", "curious about"
    ]
    for frag in ivy_fragments:
        if frag in subj_lower: return False
        
    warmup_patterns = [
        "bug fixes", "software training", "expense reports", "rotation",
        "sales report", "feedback request", "performance reviews",
        "volunteer day", "vendor negotiations", "health benefits",
        "job application", "team building", "intern welcome",
        "strategic planning", "remote work", "client meeting",
        "project update", "policy reminder", "office move",
        "company picnic", "birthday celebration", "quarterly goals"
    ]
    for pattern in warmup_patterns:
        if pattern in subj_lower: return True
        
    return False # Relaxed logic we implemented

def audit_replies():
    print("📋 Starting Reply Audit (Lock-Less)...")
    load_dotenv()
    
    api_key = auth_config.MAILREEF_API_KEY
    client = MailreefClient(api_key=api_key)
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    print("📡 Fetching lead emails from sheet...")
    records = sheets._fetch_all_records()
    lead_emails = set(str(r.get('email', '')).lower().strip() for r in records if r.get('email'))
    print(f"✅ Loaded {len(lead_emails)} lead emails.")
    
    print("📡 Fetching last 300 inbound emails (3 pages) from Mailreef...")
    messages = []
    for p in range(1, 4):
        inbound = client.get_global_inbound(page=p, display=100)
        messages.extend(inbound.get('data', []))
    
    print(f"🔍 Analyzing {len(messages)} messages...")
    
    potential_leads = []
    
    for msg in messages:
        from_email = str(msg.get('from_email', '')).lower().strip()
        subject = msg.get('subject_line', '')
        ts = msg.get('ts', 0)
        date = datetime.fromtimestamp(ts).isoformat() if ts else "unknown"
        
        is_warmup = is_warmup_manual(lead_emails, from_email, subject)
        is_known = from_email in lead_emails
        
        match_str = "[KNOWN LEAD]" if is_known else "[UNKNOWN]"
        if is_known:
            print(f"✨ REPLY {match_str} | {date} | {from_email} | {subject}")
        elif not is_warmup:
            print(f"❓ POTENTIAL MISS {match_str} | {date} | {from_email} | {subject}")
            potential_leads.append((from_email, subject))
        else:
            print(f"⚪ WARMUP | {date} | {from_email} | {subject}")
    
    print("\n--- AUDIT SUMMARY ---")
    print(f"Total analyzed: {len(messages)}")
    print(f"Confirmed Lead Replies: {sum(1 for m in messages if str(m.get('from_email', '')).lower().strip() in lead_emails)}")
    print(f"Potential missed replies: {len(potential_leads)}")
    for p, s in potential_leads:
        print(f"  - {p} | {s}")

if __name__ == "__main__":
    audit_replies()
