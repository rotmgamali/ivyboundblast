import os
import sys
import time
from datetime import datetime

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import automation_config

def full_sync():
    print("🚀 Starting FULL HISTORICAL SYNC...")
    
    # 1. Setup Clients
    mailreef = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    
    print("📊 Loading Ivy Bound leads...")
    sheets = GoogleSheetsClient(
        input_sheet_name="Ivy Bound - Campaign Leads",
        replies_sheet_name="Ivy Bound - Reply Tracking"
    )
    sheets.setup_sheets()
    
    # 2. Load ALL leads for matching
    leads_cache = {} # email -> record
    known_domains = {} # domain -> list of lead emails
    
    lead_records = sheets._fetch_all_records()
    print(f"  Found {len(lead_records)} leads in database.")
    
    for r in lead_records:
        email = str(r.get("email", "")).lower().strip()
        if email:
            leads_cache[email] = r
            
        # Extract domain
        if "@" in email:
            domain = email.split("@")[-1]
            if domain not in ["gmail.com", "yahoo.com", "outlook.com"]:
                 if domain not in known_domains:
                     known_domains[domain] = []
                 known_domains[domain].append(email)
                 
    # 3. Fetch ALL Inbound Emails
    print("📡 Fetching ALL inbound emails from Mailreef (no time limit)...")
    
    all_inbound = []
    page = 1
    max_pages = 200 # Safety limit (20,000 emails)
    
    while page <= max_pages:
        try:
            data = mailreef.get_global_inbound(page=page)
            batch = data.get("data", []) if isinstance(data, dict) else data
            
            if not batch:
                break
                
            all_inbound.extend(batch)
            print(f"  - Page {page}: Fetched {len(batch)} emails (Total: {len(all_inbound)})")
            
            if len(batch) < 100:
                break
                
            page += 1
            # Rate limit politeness
            # time.sleep(0.2) 
        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
            break
            
    print(f"✅ Downloaded {len(all_inbound)} total inbound emails.")
    
    # 4. Filter & Match
    print("🔍 Matching against Ivy Bound leads...")
    
    matched_replies = []
    
    # Heuristic for sorting noise/warmup (Minimal filter, let sentiment strictness handle it later?)
    # User said "make sure its from the ivybound schools".
    # So we MUST match against leads.
    
    for email_data in all_inbound:
        sender = email_data.get("from_email", "").lower().strip()
        # sender_name = email_data.get("from_name", "")
        # subject = email_data.get("subject_line", "")
        # snippet = email_data.get("snippet_preview", "")
        # ts = email_data.get("ts", 0)
        
        match_reason = None
        lead_info = None
        
        # A. Direct Email Match
        if sender in leads_cache:
            match_reason = "Direct Email"
            lead_info = leads_cache[sender]
            
        # B. Domain Match
        elif "@" in sender:
            domain = sender.split("@")[-1]
            if domain in known_domains:
                match_reason = f"Domain Match ({domain})"
                # Pick the first lead with this domain for info
                lead_email = known_domains[domain][0]
                lead_info = leads_cache[lead_email]
        
        if lead_info:
            # Enrich
            email_data["match_reason"] = match_reason
            email_data["matched_lead"] = lead_info
            matched_replies.append(email_data)
            
    print(f"✅ Found {len(matched_replies)} matching replies from Ivy Bound leads.")
    
    # 5. Sort by Date (Earliest to Oldest -> Ascending)
    # User said "earliest to oldest".
    # ts is unix timestamp. Smaller = earlier.
    matched_replies.sort(key=lambda x: x.get("ts", 0))
    
    # 6. Format for Sheet
    clean_rows = []
    headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Entire Thread", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
    
    # We need to preserve existing sentiment/notes if possible?
    # Or overwrite? User implies a full refresh "analyze all... sort them all".
    # I'll rely on analyze_sentiment.py to re-populate sentiment after this.
    # So here I just dump the raw data.
    
    for reply in matched_replies:
        ts = reply.get("ts", 0)
        date_str = datetime.fromtimestamp(ts).isoformat()
        
        sender = reply.get("from_email", "")
        lead = reply.get("matched_lead", {})
        
        row = [
            date_str,
            sender,
            reply.get("from_name", ""),
            lead.get("school_name", ""),
            lead.get("role", ""),
            reply.get("subject_line", ""),
            reply.get("body_text") or reply.get("snippet_preview", ""), # Full Thread (with fallback)
            "NEUTRAL", # Reset sentiment for re-analysis
            "", # Original Sender (unknown from inbound endpoint unless we parse headers)
            "", # Original Subject
            reply.get("id", ""), # Thread ID
            f"Matched via {reply.get('match_reason')}", # Action/Notes
            ""
        ]
        clean_rows.append(row)
        
    # 7. Update Sheet
    replies_sheet = sheets.replies_sheet.sheet1
    print(f"📝 Overwriting sheet with {len(clean_rows)} rows...")
    replies_sheet.clear()
    replies_sheet.update('A1', [headers] + clean_rows)
    
    print("✨ Sync Complete! Now run analyze_sentiment.py to color code.")

if __name__ == "__main__":
    full_sync()
