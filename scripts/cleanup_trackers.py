import os
import sys
from datetime import datetime
import json
import time

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from sheets_integration import GoogleSheetsClient
from mailreef_client import MailreefClient
import automation_config

# --- WARMUP PATTERNS (FROM RECONCILE_REPLIES) ---
WARMUP_PATTERNS = [
    "software training", "company picnic", "employee satisfaction", "sales report",
    "team building", "training session", "bug fixes", "project update",
    "project timeline", "productivity tips", "new hire", "security update",
    "it support", "client feedback", "marketing strategies", "office supplies",
    "human resources", "payroll", "vacation policy", "networking event",
    "internal announcement", "performance review", "department meeting",
    "budget plan", "quarterly results", "customer engagement", "tech stack",
    "workflow optimization", "knowledge base", "webinar invitation",
    "cycling club", "travel plans", "staff wellness", "project milestone",
    "sales performance", "annual conference reminder", "new project kickoff",
    "presentation feedback", "weekend ride", "feedback on recent", "kickoff meeting",
    "melnyresults.com", "brandingsavoirltd.forum", "marketingsavoir.forum",
    "sendemallcloud.com", "gcodeai.club", "influumcn.us"
]

def is_warmup(subject: str, body: str, sender: str) -> bool:
    subject = subject.lower()
    body = body.lower()
    sender = sender.lower()
    
    # Check subjects
    for p in WARMUP_PATTERNS:
        if p in subject or p in body or p in sender:
            return True
            
    # Heuristic: Sender is likely warmup if they have 'melny' or 'sendemall' or 'influu' in domain
    return False

def cleanup_trackers():
    print("🚀 Starting Tracker Cleanup (Purging Noise/Leakage)...")
    
    # 1. Initialize Profiles
    profiles = {
        "IVYBOUND": {
            "keywords": ["enrollment", "boosting", "merit scholarship", "academic outcomes", "tutoring", "test prep", "curriculum", "principal", "school"],
            "sheet_name": "Ivy Bound - Reply Tracking",
            "leads_sheet": "Ivy Bound - Campaign Leads"
        },
        "WEB4GURU_ACCOUNTANTS": {
            "keywords": ["accountant", "cpa", "tax", "firm", "leads", "revenue", "marketing", "client", "business"],
            "sheet_name": "Web4Guru Accountants - Reply Tracking",
            "leads_sheet": "Web4Guru Accountants - Campaign Leads"
        }
    }

    # Load all leads for cross-campaign validation
    print("📊 Loading leads for both campaigns...")
    all_leads = {}
    for p_name, config in profiles.items():
        sheets = GoogleSheetsClient(input_sheet_name=config["leads_sheet"])
        sheets.setup_sheets()
        records = sheets._fetch_all_records()
        all_leads[p_name] = {r["email"].lower().strip() for r in records if r.get("email")}
        print(f"  - {p_name}: {len(all_leads[p_name])} leads loaded.")

    # 2. Process each tracker
    for p_name, config in profiles.items():
        print(f"\n🧹 Cleaning up {p_name} tracker...")
        sheets = GoogleSheetsClient(replies_sheet_name=config["sheet_name"])
        sheets.setup_sheets()
        worksheet = sheets.replies_sheet.sheet1
        
        raw_rows = worksheet.get_all_records()
        print(f"  🔍 Found {len(raw_rows)} total rows.")
        
        if not raw_rows:
            continue
            
        clean_rows = []
        counts = {"REMOVED_WARMUP": 0, "REMOVED_LEAKAGE": 0, "REMOVED_IRRELEVANT": 0, "KEPT": 0}
        
        other_campaign = "WEB4GURU_ACCOUNTANTS" if p_name == "IVYBOUND" else "IVYBOUND"
        
        for row in raw_rows:
            sender = str(row.get("From Email", "")).lower().strip()
            subject = str(row.get("Subject", "")).lower()
            snippet = str(row.get("Snippet", "")).lower()
            
            # --- PHASE 1: WARMUP ---
            if is_warmup(subject, snippet, sender):
                counts["REMOVED_WARMUP"] += 1
                continue
            
            # --- PHASE 2: LEAKAGE ---
            if sender in all_leads[other_campaign] and sender not in all_leads[p_name]:
                counts["REMOVED_LEAKAGE"] += 1
                continue
                
            # --- PHASE 3: RELEVANCE ---
            is_relevant = False
            # If they are a lead in THIS campaign, keep them
            if sender in all_leads[p_name]:
                is_relevant = True
            else:
                # If they match keywords, keep them (could be a referral or alternate email)
                for k in config["keywords"]:
                    if k in subject or k in snippet:
                        is_relevant = True
                        break
            
            if is_relevant:
                # Map back to ordered list for sheet update
                # Headers: Received At, From Email, From Name, School Name, Role, Subject, Snippet, Sentiment, Original Sender, Original Subject, Thread ID, Action Taken, Notes
                clean_rows.append([
                    row.get("Received At", ""),
                    row.get("From Email", ""),
                    row.get("From Name", ""),
                    row.get("School Name", ""),
                    row.get("Role", ""),
                    row.get("Subject", ""),
                    row.get("Snippet", ""),
                    row.get("Sentiment", ""),
                    row.get("Original Sender", ""),
                    row.get("Original Subject", ""),
                    row.get("Thread ID", ""),
                    row.get("Action Taken", ""),
                    row.get("Notes", "")
                ])
                counts["KEPT"] += 1
            else:
                counts["REMOVED_IRRELEVANT"] += 1

        print(f"  ✅ Cleanup Results for {p_name}:")
        print(f"    - Kept: {counts['KEPT']}")
        print(f"    - Removed Warmup: {counts['REMOVED_WARMUP']}")
        print(f"    - Removed Leakage: {counts['REMOVED_LEAKAGE']}")
        print(f"    - Removed Irrelevant: {counts['REMOVED_IRRELEVANT']}")
        
        # 3. Write back
        if len(clean_rows) < len(raw_rows):
            print(f"  📝 Updating sheet with {len(clean_rows)} clean rows...")
            # Headers are already at row 1, we want to clear from A2 onwards
            # But it's safer to clear and write with headers to ensure alignment
            headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
            
            # Batch update for speed
            worksheet.clear()
            worksheet.update('A1', [headers] + clean_rows)
            print(f"  ✨ {p_name} tracker cleaned!")
        else:
            print(f"  ℹ️ No changes needed for {p_name}.")

    print("\n✨ All trackers cleaned successfully!")

if __name__ == "__main__":
    cleanup_trackers()
