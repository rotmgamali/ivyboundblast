import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from mailreef_automation.automation_config import MAILREEF_API_KEY, CAMPAIGN_PROFILES
from mailreef_automation.mailreef_client import MailreefClient

def check_history():
    print("Fetching last 2 weeks of replies from Mailreef (IVYBOUND campaign)...\\n")
    client = MailreefClient(api_key=MAILREEF_API_KEY)
    
    # Fetch inboxes and filter by 'errorskin' server
    all_inboxes = client.get_inboxes()
    ivybound_inboxes = [i['id'] for i in all_inboxes if i.get('server') == 'errorskin']
    print(f"Found {len(ivybound_inboxes)} inboxes on errorskin server.")
    
    two_weeks_ago = datetime.now() - timedelta(days=14)
    
    known_fragments = [
        "quick question", "supporting families", "boosting enrollment", 
        "academic outcomes", "differentiation", "merit scholarship",
        "college readiness", "student-athletes", "test prep", 
        "enhancing value", "families and college prep"
    ]
    
    total_emails = 0
    ivybound_emails = 0
    genuine_replies = []
    printed_subjects = []
    
    for page in range(1, 10):
        res = client.get_global_inbound(page=page, display=100)
        batch = res.get("data", [])
        if not batch:
            break
            
        for msg in batch:
            ts = msg.get("ts")
            if not ts: continue
            
            msg_dt = datetime.fromtimestamp(ts)
            if msg_dt < two_weeks_ago:
                break # We went past 2 weeks
                
            total_emails += 1
            
            to_email = msg.get("to", ["unknown"])[0]
            if to_email not in ivybound_inboxes:
                continue
                
            ivybound_emails += 1
            subject = str(msg.get("subject_line", "")).lower()
            clean_subject = subject.replace('re:', '').replace('fwd:', '').strip()
            
            if len(printed_subjects) < 30:
                print(f"Subject seen: {subject}")
                printed_subjects.append(subject)

            if any(frag in clean_subject for frag in known_fragments):
                genuine_replies.append({
                    "date": msg_dt.isoformat(),
                    "from": msg.get("from_email"),
                    "subject": msg.get("subject_line")
                })
                
        # If we broke inner loop because of date, break outer loop
        if batch and msg_dt < two_weeks_ago:
            break

    print(f"Total inbound emails scanned (all campaigns): {total_emails}")
    print(f"Total inbound directed at Ivybound inboxes: {ivybound_emails}")
    print(f"✅ Total GENUINE replies matched by strict subject logic: {len(genuine_replies)}\\n")
    
    if genuine_replies:
        print("--- MATCHED REPLIES ---")
        for r in genuine_replies:
            print(f"[{r['date']}] From: {r['from']}")
            print(f"Subject: {r['subject']}\\n")

if __name__ == "__main__":
    check_history()
