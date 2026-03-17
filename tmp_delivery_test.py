
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.automation_config import MAILREEF_API_KEY, CAMPAIGN_PROFILES
from generators.email_generator import EmailGenerator

def run_test(target_email, school_url="https://www.thegroveschool.org/"):
    load_dotenv()
    
    if not MAILREEF_API_KEY:
        print("Error: MAILREEF_API_KEY not found.")
        return

    # 1. Initialize Components
    client = MailreefClient(MAILREEF_API_KEY)
    generator = EmailGenerator()
    
    # 2. Mock Lead Data (Real school for scraping)
    lead_data = {
        "email": target_email,
        "school_name": "The Grove School",
        "first_name": "Test",
        "role": "Principal",
        "website": school_url,
        "city": "Redlands",
        "state": "CA",
        "custom_data": "{}"
    }
    
    print(f"Personalizing email for {school_url}...")
    
    # 3. Generate Personalized Email
    result = generator.generate_email(
        campaign_type="school",
        sequence_number=1,
        lead_data=lead_data,
        enrichment_data={} # Scraper will fetch live
    )
    
    print("\n--- GENERATED EMAIL ---")
    print(f"Subject: {result['subject']}")
    print(f"Body:\n{result['body']}")
    print("-----------------------\n")
    
    with open("test_email_output.txt", "w") as f:
        f.write(f"Subject: {result['subject']}\n\n{result['body']}")
    
    # 4. Pick an inbox to send from
    inboxes = client.get_inboxes()
    # FILTER OUT None values and get a real ID
    valid_ids = [ib.get('id') for ib in inboxes if ib and ib.get('id')]
    
    # We want one from the IVYBOUND range if possible
    profile = CAMPAIGN_PROFILES.get("IVYBOUND")
    start, end = profile.get("inbox_indices")
    
    # Fallback if range is weird
    if len(valid_ids) > start:
         test_inbox = valid_ids[start]
    else:
         test_inbox = valid_ids[0]
    
    print(f"Sending test from {test_inbox} to {target_email}...")
    
    # 5. Send
    try:
        response = client.send_email(
            inbox_id=test_inbox,
            to_email=target_email,
            subject=result['subject'],
            body=result['body']
        )
        print(f"✅ Send Success! MsgID: {response.get('message_id')}")
    except Exception as e:
        print(f"❌ Send Failed: {e}")

if __name__ == "__main__":
    test_target = "test-f60v08zxe@srv1.mail-tester.com"
    test_url = "https://www.thegroveschool.org/"
    
    if len(sys.argv) > 1:
        test_target = sys.argv[1]
    if len(sys.argv) > 2:
        test_url = sys.argv[2]
    
    run_test(test_target, test_url)
