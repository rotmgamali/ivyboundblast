import sys
import os
import logging

# Add path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))

from mailreef_automation.scheduler import EmailScheduler
from mailreef_automation.logger_util import get_logger

# Setup logging to see output
logging.basicConfig(level=logging.INFO)
logger = get_logger("FORCE_SEND")

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.contact_manager import ContactManager
from mailreef_automation import config

def force_send():
    print("🚀 Forcing ONE email send...")
    
    # Initialize dependencies
    client = MailreefClient(api_key=config.MAILREEF_API_KEY)
    db_path = os.path.join(os.path.dirname(__file__), "mailreef_automation/campaign.db")
    contact_manager = ContactManager(database_path=db_path)
    
    # Initialize Scheduler
    scheduler = EmailScheduler(client, contact_manager, config)
    
    # Manually trigger the slot execution logic
    from datetime import datetime
    # We call the internal method that processes ONE slot
    # Pass dummy inbox_id=1 and current time
    scheduler._execute_slot(inbox_id=1, scheduled_time=datetime.now()) 
    print("✅ Send attempt complete.")

if __name__ == "__main__":
    force_send()
