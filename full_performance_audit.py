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

def performance_audit():
    print("🚀 Starting Comprehensive Campaign Performance Audit...")
    load_dotenv()
    
    # 1. Initialize Sheets and fetch data
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    print("📡 Fetching lead records from Google Sheets...")
    records = sheets._fetch_all_records()
    
    total_leads = len(records)
    emailed_leads = [r for r in records if r.get('status') in ['email_1_sent', 'email_2_sent', 'replied']]
    replied_leads = [r for r in records if r.get('status') == 'replied']
    
    lead_emails = set(str(r.get('email', '')).lower().strip() for r in records if r.get('email'))
    lead_domains = set()
    for r in records:
        email = str(r.get('email', '')).lower().strip()
        if '@' in email:
            domain = email.split('@')[-1]
            if domain not in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']:
                lead_domains.add(domain)

    print(f"✅ Total Leads in Sheet: {total_leads}")
    print(f"✅ Leads with Sent Status: {len(emailed_leads)}")
    print(f"✅ Leads marked as 'Replied': {len(replied_leads)}")
    
    # 2. Initialize Mailreef and fetch ALL inbound
    api_key = auth_config.MAILREEF_API_KEY
    client = MailreefClient(api_key=api_key)
    
    print("📡 Fetching ALL inbound messages from Mailreef (this may take a moment)...")
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
        print(f"  - Loaded {len(all_messages)} messages...", end="\r")
    
    print(f"\n✅ Total Inbound Messages Found: {len(all_messages)}")
    
    # 3. Analyze Inbound Messages
    confirmed_school_replies = []
    warmup_replies = 0
    unknown_non_warmup = []
    
    # Simple is_warmup local logic
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

    seen_emails = set()
    bounces = 0
    
    for msg in all_messages:
        from_email = str(msg.get('from_email', '')).lower().strip()
        subject = msg.get('subject_line', '')
        
        # Bounce Check (look for postmaster or mailer-daemon)
        if 'postmaster' in from_email or 'mailer-daemon' in from_email or 'mail system' in subject.lower():
            bounces += 1
            continue

        # Exact match
        is_known = from_email in lead_emails
        
        # Domain match
        domain = from_email.split('@')[-1] if '@' in from_email else ""
        is_domain_match = domain in lead_domains
        
        # Warmup check
        is_warmup = False
        for p in warmup_patterns:
            if p in subject.lower():
                is_warmup = True
                break
        
        if is_warmup:
            warmup_replies += 1
            continue
            
        if is_known or is_domain_match:
            if from_email not in seen_emails:
                confirmed_school_replies.append({
                    'email': from_email,
                    'subject': subject,
                    'is_known': is_known,
                    'is_domain': is_domain_match
                })
                seen_emails.add(from_email)
        else:
            # Check for ivy fragments in subject - might be a reply we missed
            is_fragment_match = False
            for f in ivy_fragments:
                if f in subject.lower():
                    is_fragment_match = True
                    break
            
            if is_fragment_match:
                confirmed_school_replies.append({
                    'email': from_email,
                    'subject': subject,
                    'is_known': False,
                    'is_domain': False,
                    'fragment_match': True
                })
                seen_emails.add(from_email)

    # Calculate rates
    total_sent = len(emailed_leads)
    reply_rate = (len(confirmed_school_replies) / total_sent * 100) if total_sent > 0 else 0
    bounce_rate = (bounces / total_sent * 100) if total_sent > 0 else 0

    print("\n--- PERFORMANCE SUMMARY ---")
    print(f"Total Unique Leads Contacted: {total_sent}")
    print(f"Total Unique School Replies Identified: {len(confirmed_school_replies)}")
    print(f"Total Bounces Detected in Inbound: {bounces}")
    print(f"-------------------------------")
    print(f"📊 Overall Reply Rate: {reply_rate:.2f}%")
    print(f"📊 Observed Bounce Rate: {bounce_rate:.2f}%")
    print(f"-------------------------------")
    print(f"Warmup noise filtered: {warmup_replies}")
    
    print("\n--- TOP RECENT CONFIRMED REPLIES ---")
    for r in confirmed_school_replies[:20]:
        tag = "[EXACT]" if r.get('is_known') else "[DOMAIN]" if r.get('is_domain') else "[FRAGMENT]"
        print(f"  {tag} {r['email']} | {r['subject']}")

if __name__ == "__main__":
    performance_audit()
