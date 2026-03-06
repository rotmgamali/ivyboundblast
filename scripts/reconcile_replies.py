#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, timedelta
import pytz
from typing import List, Dict

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import automation_config

# Warmup Filter Patterns (Copy from reply_watcher.py)
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

def is_warmup(subject: str, body: str) -> bool:
    content = (str(subject) + " " + str(body)).lower()
    for pattern in WARMUP_PATTERNS:
        if pattern in content:
            return True
    return False

def reconcile():
    print("🚀 Starting 7-Day Reply Reconciliation...")
    
    # 1. Initialize API Client
    mailreef = MailreefClient(api_key=automation_config.MAILREEF_API_KEY)
    
    # 2. Setup Campaigns
    profiles = ["IVYBOUND", "WEB4GURU_ACCOUNTANTS"]
    campaign_data = {}
    
    # Fetch all inboxes once and sort for consistent indexing
    print("📡 Fetching and sorting all inboxes...")
    all_inboxes_raw = mailreef.get_inboxes()
    all_inboxes_raw.sort(key=lambda x: x['id'])
    
    for p_name in profiles:
        config = automation_config.CAMPAIGN_PROFILES[p_name]
        start, end = config["inbox_indices"]
        # Mailreef uses 'id' for the email address
        campaign_inboxes = {inbox["id"].lower(): inbox for inbox in all_inboxes_raw[start:end]}
        
        # Load leads and current replies
        print(f"📊 Loading data for {p_name}...")
        sheets = GoogleSheetsClient(
            input_sheet_name=config["input_sheet"],
            replies_sheet_name=config["replies_sheet"]
        )
        sheets.setup_sheets()
        
        # Load all lead emails for matching
        leads = set()
        lead_records = sheets._fetch_all_records()
        for r in lead_records:
            email = r.get("email", "").lower().strip()
            if email: leads.add(email)
            
        # Load current replies to avoid duplicates
        existing_replies = set()
        try:
            replies_worksheet = sheets.replies_sheet.get_worksheet(0)
            reply_records = replies_worksheet.get_all_records()
            for r in reply_records:
                email = r.get("email", "").lower().strip()
                if email: existing_replies.add(email)
        except Exception as e:
            print(f"⚠️ Could not load existing replies for {p_name}: {e}")

        campaign_data[p_name] = {
            "inboxes": campaign_inboxes,
            "leads": leads,
            "existing": existing_replies,
            "sheets": sheets,
            "new_replies": []
        }
    
    # 3. Fetch Inbound Emails (Last 7 Days)
    import time
    seven_days_ago_ts = time.time() - (7 * 24 * 3600)
    print(f"📡 Fetching global inbound emails since {datetime.fromtimestamp(seven_days_ago_ts).date()}...")
    
    all_replies = []
    page = 1
    while True:
        data = mailreef.get_global_inbound(page=page)
        # Mailreef response might have 'data' key or be a list
        batch = data.get("data", []) if isinstance(data, dict) else data
        if not batch: break
        
        for email in batch:
            # Check date using 'ts' (unix timestamp integer)
            ts = email.get("ts", 0)
            if ts < seven_days_ago_ts:
                # If we get here, the rest are likely older
                if ts < seven_days_ago_ts - (24 * 3600):
                    break
                continue
            
            all_replies.append(email)
        
        if len(batch) < 100: break
        page += 1
        
    print(f"🔍 Found {len(all_replies)} total inbound emails in the last 7 days.")
    
    # 4. Categorize and Filter
    stats = {"IVYBOUND": 0, "WEB4GURU": 0, "WARMUP": 0, "NO_MATCH": 0}
    
    # Heuristic for sorting noise/warmup
    NOISE_SUBJECTS = [
        "cycling club", "travel plans", "staff wellness", "project milestone",
        "sales performance", "annual conference", "kickoff meeting", "presentation feedback",
        "weekend ride", "feedback on recent", "company retreat", "onboarding session",
        "quarterly budget", "office space", "safety protocol", "security awareness",
        "internal audit", "team outing", "holiday party", "service anniversary"
    ]
    NOISE_DOMAINS = [
        "melnyresults.com", "brandingsavoir", "marketingsavoir", "sendemallcloud",
        "gcodeai.club", "influumcn", "firmsavoir"
    ]

    for email in all_replies:
        sender = email.get("from_email", "").lower().strip()
        to_list = email.get("to", [])
        recipient = to_list[0].lower().strip() if to_list else ""
        subject = email.get("subject_line", "").lower()
        body = email.get("body_text", "").lower()
        
        # --- PHASE 1: WARMUP FILTERING ---
        is_noise = False
        if is_warmup(subject, body): is_noise = True
        for p in NOISE_SUBJECTS:
            if p in subject: is_noise = True; break
        if not is_noise:
            for d in NOISE_DOMAINS:
                if d in sender: is_noise = True; break
                
        if is_noise:
            stats["WARMUP"] += 1
            continue
            
        # --- PHASE 2: SENDER-BASED MATCHING (HIGHEST PRIORITY) ---
        matched_campaign = None
        
        # Check leads lists first to solve overlap issue
        if sender in campaign_data["IVYBOUND"]["leads"]:
            matched_campaign = "IVYBOUND"
        elif sender in campaign_data["WEB4GURU_ACCOUNTANTS"]["leads"]:
            matched_campaign = "WEB4GURU_ACCOUNTANTS"
        
        # Domain-based fallback for known leads
        if not matched_campaign and "@" in sender:
            domain = sender.split("@")[-1]
            if domain not in ["gmail.com", "yahoo.com", "outlook.com"]:
                 # Check Ivy leads domain
                 for lead_email in campaign_data["IVYBOUND"]["leads"]:
                     if f"@{domain}" in lead_email:
                         matched_campaign = "IVYBOUND"
                         break
                 # Check Web4Guru leads domain
                 if not matched_campaign:
                     for lead_email in campaign_data["WEB4GURU_ACCOUNTANTS"]["leads"]:
                         if f"@{domain}" in lead_email:
                             matched_campaign = "WEB4GURU_ACCOUNTANTS"
                             break

        # --- PHASE 3: RECIPIENT-BASED MATCHING (FALLBACK) ---
        if not matched_campaign:
            if recipient in campaign_data["IVYBOUND"]["inboxes"]:
                 # It's an Ivy inbox. If it contains Ivy-specific keywords, categorize it.
                 # Otherwise, it might be warmup.
                 ivy_keywords = ["boosting enrollment", "merit scholarship", "academic outcomes", "school", "principals"]
                 if any(k in subject or k in body for k in ivy_keywords):
                     matched_campaign = "IVYBOUND"
                 else:
                     # Could be noise that bypassed filters
                     pass
            
            if not matched_campaign and recipient in campaign_data["WEB4GURU_ACCOUNTANTS"]["inboxes"]:
                 w4g_keywords = ["accountant", "cpa", "tax", "firm", "revenue", "leads"]
                 if any(k in subject or k in body for k in w4g_keywords):
                     matched_campaign = "WEB4GURU_ACCOUNTANTS"
        
        # --- PHASE 4: ASSIGNMENT ---
        if matched_campaign:
            data = campaign_data[matched_campaign]
            if sender not in data["existing"]:
                data["new_replies"].append(email)
                stats["IVYBOUND" if matched_campaign == "IVYBOUND" else "WEB4GURU"] += 1
        else:
            stats["NO_MATCH"] += 1

    print("\n📊 Categorization Results:")
    print(f"  - Ivy Bound: {stats['IVYBOUND']} new")
    print(f"  - Web4Guru: {stats['WEB4GURU']} new")
    print(f"  - Warmup: {stats['WARMUP']}")
    print(f"  - Unmatched/Unknown: {stats['NO_MATCH']}")
    
    # 5. Sync Sheets
    for p_name, data in campaign_data.items():
        if data["new_replies"]:
            print(f"📝 Syncing {len(data['new_replies'])} new leads to {p_name} tracker...")
            sheets = data["sheets"]
            for reply in data["new_replies"]:
                sender = reply.get("from_email", "").lower().strip()
                subject = reply.get("subject_line", "")
                to_email = reply.get("to", [""])[0] if reply.get("to") else ""
                
                try:
                    sheets.log_reply({
                        'from_email': sender,
                        'to_email': to_email,
                        'subject': subject,
                        'body_text': reply.get("body_text", ""),
                        'snippet': reply.get("body_text", reply.get("snippet_preview", ""))
                    })
                    print(f"  ✅ Logged: {sender}")
                except Exception as e:
                    print(f"  ❌ Failed to log {sender}: {e}")

    # 6. Cleanup Web4Guru Sheets (Remove Ivy Bound leakage)
    print("\n🧹 Cleaning up Web4Guru Tracker from leakage...")
    w4g_data = campaign_data["WEB4GURU_ACCOUNTANTS"]
    ivy_inboxes = campaign_data["IVYBOUND"]["inboxes"]
    
    try:
        w4g_sheets = w4g_data["sheets"]
        worksheet = w4g_sheets.replies_sheet.get_worksheet(0)
        all_reply_rows = worksheet.get_all_records()
        
        to_delete = []
        for i, row in enumerate(all_reply_rows):
            to_email = row.get("To Email", "").lower().strip()
            # If the recipient inbox belongs to IVYBOUND, it's leakage
            if to_email in ivy_inboxes:
                to_delete.append(i + 2) # 1-indexed + header
                
        if to_delete:
            print(f"  🗑️ Found {len(to_delete)} Ivy Bound entries in Web4Guru tracker. Deleting...")
            # Delete in reverse to keep indices valid
            for row_idx in sorted(to_delete, reverse=True):
                worksheet.delete_rows(row_idx)
                print(f"  🗑️ Deleted row {row_idx}")
        else:
            print("  ✅ No leakage found in Web4Guru tracker.")
            
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

    print("\n✨ Reconciliation Complete!")

if __name__ == "__main__":
    reconcile()
