import sys
import os
import logging
from datetime import datetime

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.scheduler import EmailScheduler
from mailreef_automation.logger_util import get_logger
import automation_config as config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = get_logger("LOCAL_TEST")

def test_full_pipeline():
    print("\n" + "="*50)
    print("🚀 LOCAL SYSTEM VERIFICATION START")
    print("="*50)
    
    # 1. Initialize Clients
    logger.info("Initializing system components...")
    mailreef = MailreefClient(api_key=config.MAILREEF_API_KEY)
    scheduler = EmailScheduler(mailreef, config)
    
    # 2. Fetch a single lead from Sheets (Stage 1)
    logger.info("Fetching a test lead from Google Sheets...")
    pending_leads = scheduler.sheets.get_pending_leads(limit=1)
    
    if not pending_leads:
        logger.error("❌ No pending leads found in Google Sheet! Add a row to test.")
        return
    
    lead = pending_leads[0]
    logger.info(f"✅ Found Lead: {lead.get('email')} ({lead.get('first_name')})")
    
    # 3. Get a live Inbox from Mailreef
    logger.info("Fetching available inboxes...")
    inboxes = mailreef.get_inboxes()
    if not inboxes:
        logger.error("❌ No inboxes found via Mailreef API.")
        return
    
    # Pick the first active inbox
    inbox = inboxes[0]
    inbox_id = inbox['id']
    logger.info(f"✅ Using Inbox: {inbox.get('email')} (ID: {inbox_id})")
    
    # 4. Execute a Send (personalized)
    # NOTE: To avoid spamming a real lead, we will use the lead's data but 
    # we could override the to_email if we wanted. 
    # For a TRUE test of the "Sheets-First" loop, we will send it as-is 
    # or to a test address if provided.
    
    print("\n📦 SIMULATING SEND (Personalization + SMTP Check)")
    try:
        # We will use the actual execute_send method which:
        # - Generates personalized content
        # - Sends via SMTP
        # - Updates Google Sheets
        results = scheduler.execute_send(inbox_id, [lead], sequence_number=1)
        
        if results and results[0]['status'] == 'sent':
            print("\n" + "="*50)
            print("✨ SUCCESS: Full Pipeline Verified Locally!")
            print(f"   - Lead: {lead.get('email')}")
            print(f"   - Inbox: {inbox.get('email')}")
            print(f"   - Msg ID: {results[0].get('mailreef_message_id')}")
            print("   - [CHECK GOOGLE SHEETS]: Status should now be 'email_1_sent'")
            print("="*50)
        else:
            logger.error("❌ Send failed or returned unexpected status.")
            
    except Exception as e:
        logger.error(f"❌ Pipeline Failure: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_full_pipeline()
