import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
import mailreef_automation.automation_config as auth_config

def recover_missing_replies():
    print("🚀 Starting Recovery of Missing Replies...")
    load_dotenv()
    
    # 1. Initialize Sheets and fetch data
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    print("📡 Fetching lead records and existing replies...")
    records = sheets._fetch_all_records()
    
    # Get existing replies in the sheet to avoid duplicates
    replies_sheet = sheets.replies_sheet.sheet1
    existing_reply_records = replies_sheet.get_all_records()
    existing_reply_emails = set(str(r.get('from_email', '')).lower().strip() for r in existing_reply_records)
    
    lead_emails = set(str(r.get('email', '')).lower().strip() for r in records if r.get('email'))
    lead_domains = set()
    for r in records:
        email = str(r.get('email', '')).lower().strip()
        if '@' in email:
            domain = email.split('@')[-1]
            if domain not in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']:
                lead_domains.add(domain)

    # 2. Fetch ALL inbound from Mailreef
    api_key = auth_config.MAILREEF_API_KEY
    client = MailreefClient(api_key=api_key)
    
    print("📡 Fetching ALL inbound messages from Mailreef...")
    all_messages = []
    page = 1
    while True:
        result = client.get_global_inbound(page=page, display=100)
        batch = result.get('data', [])
        if not batch:
            break
        all_messages.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    
    print(f"✅ Found {len(all_messages)} total inbound messages.")
    
    # 3. Filter for confirmed school replies that ARE NOT in the sheet
    missing_replies = []
    
    ivy_fragments = [
        "quick question", "supporting families", "test prep",
        "merit scholarship", "differentiation and outcomes", "enhancing value",
        "supporting student-athletes", "boosting enrollment", "academic outcomes",
        "families and college prep", "curriculum", "ivy bound", "curious about"
    ]
    warmup_patterns = [
        "bug fixes", "software training", "expense reports", "rotation",
        "sales report", "feedback request", "performance reviews"
    ]

    for msg in all_messages:
        from_email = str(msg.get('from_email', '')).lower().strip()
        subject = msg.get('subject_line', '')
        
        # Skip if already in sheet
        if from_email in existing_reply_emails:
            continue
            
        # Warmup skip
        is_warmup = False
        for p in warmup_patterns:
            if p in subject.lower():
                is_warmup = True
                break
        if is_warmup: continue
            
        # Match check
        is_known = from_email in lead_emails
        domain = from_email.split('@')[-1] if '@' in from_email else ""
        is_domain_match = domain in lead_domains and domain != ""
        
        is_fragment_match = False
        for f in ivy_fragments:
            if f in subject.lower():
                is_fragment_match = True
                break
        
        if is_known or is_domain_match or is_fragment_match:
            missing_replies.append(msg)

    print(f"🔍 Identified {len(missing_replies)} missing replies to log.")
    
    # 4. Log missing replies
    count = 0
    for msg in missing_replies:
        try:
            from_email = str(msg.get('from_email', '')).lower().strip()
            print(f"✍️ Logging missing reply from: {from_email}...")
            
            reply_data = {
                'received_at': msg.get('created_at', datetime.now().isoformat()),
                'from_email': from_email,
                'from_name': msg.get('from_name', ''),
                'subject': msg.get('subject_line', ''),
                'snippet': msg.get('text_body', '')[:200],
                'sentiment': 'neutral', # Default for recovery
                'original_sender': msg.get('to_email', ''),
                'original_subject': msg.get('subject_line', ''),
                'thread_id': msg.get('id', ''),
                'action_taken': 'RECOVERED',
                'notes': 'Manually recovered from Mailreef Audit'
            }
            
            sheets.log_reply(reply_data)
            count += 1
            # Sleep slightly to avoid quota issues during bulk log
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Failed to log {from_email}: {e}")

    print(f"✅ Successfully recovered and logged {count} replies.")

if __name__ == "__main__":
    recover_missing_replies()
