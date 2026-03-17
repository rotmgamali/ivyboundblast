import os
import sys
import json
import logging
import time

# Add project root to path
sys.path.append(os.getcwd())

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.automation_config import MAILREEF_API_KEY, MAILREEF_API_BASE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GOLDEN_DISPATCH")

def dispatch():
    manifest_path = "/Users/mac/Ivybound/golden_outreach_manifest.json"
    if not os.path.exists(manifest_path):
        logger.error("❌ Manifest not found. Run prepare_golden_outreach.py first.")
        return

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    logger.info(f"🚀 Starting dispatch for {len(manifest)} Golden Leads...")
    client = MailreefClient(MAILREEF_API_KEY, MAILREEF_API_BASE)

    success_count = 0
    for email, data in manifest.items():
        logger.info(f"📧 Sending reply to {email} from {data['from_inbox']}...")
        
        try:
            # Set up the reply parameters
            subject = f"Re: {data['last_subject']}" if not data['last_subject'].startswith("Re:") else data['last_subject']
            
            # API call to send
            result = client.send_email(
                inbox_id=data['from_inbox'],
                to_email=email,
                subject=subject,
                body=data['body'].replace('\n', '<br>'),
                reply_to=data['thread_id'] # This threads it in Mailreef
            )
            
            if result.get('status') == 'success':
                logger.info(f"✅ Successfully dispatched to {email}")
                success_count += 1
            else:
                logger.error(f"❌ Failed to send to {email}: {result}")
                
        except Exception as e:
            logger.error(f"❌ Exception sending to {email}: {e}")
        
        # Respect rate limits/spacing
        time.sleep(2)

    logger.info(f"🎉 DISPATCH COMPLETE. Success: {success_count}/{len(manifest)}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to SEND these 9 golden emails? (yes/no): ")
    if confirm.lower() == 'yes':
        dispatch()
    else:
        print("Dispatch aborted.")
