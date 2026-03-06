import os
import json
from mailreef_automation.mailreef_client import MailreefClient
from dotenv import load_dotenv

load_dotenv()

# THE EXISTING FILTER LOGIC (to see what we are current blocking)
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

def is_warmup(subject: str) -> bool:
    if not subject: return True
    subj_lower = subject.lower()
    for frag in IVY_FRAGMENTS:
        if frag in subj_lower: return False
    for pattern in WARMUP_PATTERNS:
        if pattern in subj_lower: return True
    return True

# AUDIT KEYWORDS
AUDIT_KEYWORDS = [
    "ivy", "bound", "sat", "act", "tutor", "prep", "scholarship", 
    "school", "high school", "college", "education", "student", 
    "meeting", "interested", "reply", "unsubscribe", "remove", "stop",
    "mark", "greenstein", "genelle", "andrew"
]

def run_deep_audit():
    client = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    page = 1
    total_scanned = 0
    suspicious_matches = []
    unique_warmup_subjects = set()
    
    print("📡 Loading all emails for deep filter audit...")
    
    while True:
        result = client.get_global_inbound(page=page, display=100)
        batch = result.get("data", [])
        if not batch: break
        
        for msg in batch:
            total_scanned += 1
            subject = (msg.get("subject_line") or "").lower()
            snippet = (msg.get("snippet_preview") or "").lower()
            
            if is_warmup(subject):
                # This email is currently being IGNORED.
                # Let's check it for audit keywords.
                found_keywords = [k for k in AUDIT_KEYWORDS if k in subject or k in snippet]
                
                if found_keywords:
                    suspicious_matches.append({
                        "from": msg.get("from_email"),
                        "subject": msg.get("subject_line"),
                        "snippet": msg.get("snippet_preview"),
                        "keywords": found_keywords
                    })
                
                unique_warmup_subjects.add(msg.get("subject_line"))
        
        if len(batch) < 100 or page >= 50: break
        page += 1
        print(f"  - Scanned {total_scanned} emails...")

    print("\n" + "="*80)
    print(f"🔎 FILTER AUDIT RESULTS")
    print("="*80)
    print(f"Total Scanned:         {total_scanned}")
    print(f"Suspect Warmup Emails: {len(suspicious_matches)}")
    print(f"Unique Warmup Subjs:   {len(unique_warmup_subjects)}")
    print("="*80)
    
    if suspicious_matches:
        print("\n🚨 POTENTIAL FALSE POSITIVES (Caught in Warmup Filter):")
        for i, m in enumerate(suspicious_matches[:20], 1): # Show top 20
            print(f"{i}. [{m['from']}] | Subj: {m['subject']}")
            print(f"   Keywords found: {m['keywords']}")
            print(f"   Snippet: {m['snippet']}\n")
        
        if len(suspicious_matches) > 20:
            print(f"... and {len(suspicious_matches) - 20} more.")
            
    print("\n📦 SAMPLE OF IGNORED WARMUP SUBJECTS:")
    for s in list(unique_warmup_subjects)[:15]:
        print(f" - {s}")

if __name__ == "__main__":
    run_deep_audit()
