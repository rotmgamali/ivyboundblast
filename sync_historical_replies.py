import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
from reply_watcher import ReplyWatcher
import mailreef_automation.automation_config as automation_config

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HISTORICAL_SYNC")

def sync_historical_replies(profile_name="IVYBOUND"):
    logger.info(f"🚀 STARTING HISTORICAL REPLY SYNC FOR {profile_name}")
    
    # 1. Initialize Clients
    watcher = ReplyWatcher(profile_name=profile_name)
    mailreef = watcher.mailreef
    sheets = watcher.sheets_client
    
    # User's Profile Config
    profile_config = automation_config.CAMPAIGN_PROFILES[profile_name]
    worksheet_name = profile_config.get("replies_worksheet_name", getattr(automation_config, "ACTIVE_REPLIES_WORKSHEET", "Sheet 1"))
    
    # 2. Clear the target worksheet
    logger.info(f"🧹 Clearing worksheet: {worksheet_name}")
    sheets.clear_worksheet(worksheet_name)
    
    # 3. Fetch 3,000 emails (30 pages of 100)
    logger.info("📡 Scanning Mailreef for the most recent 3,000 inbound emails...")
    
    found_count = 0
    pages_to_scan = 30
    
    for page in range(1, pages_to_scan + 1):
        logger.info(f"📄 Fetching page {page}/{pages_to_scan}...")
        try:
            result = mailreef.get_global_inbound(page=page, display=100)
            batch = result.get("data", [])
            if not batch:
                logger.info("No more emails found.")
                break
                
            for msg in batch:
                from_email = str(msg.get("from_email", "")).lower().strip()
                subject = msg.get("subject_line", "")
                
                # Use watcher's lead-first matching logic
                is_known_lead = from_email in watcher.lead_emails
                if not is_known_lead and '@' in from_email:
                    sender_domain = from_email.split('@')[-1]
                    if sender_domain in watcher.lead_domains:
                        is_known_lead = True
                
                if is_known_lead:
                    logger.info(f"🎯 MATCH FOUND: {from_email} | Subject: {subject}")
                    
                    # Normalize for watcher's processing logic
                    body_text = msg.get("body_text")
                    if not body_text and msg.get("body_html"):
                        import re
                        body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
                    
                    msg_body = body_text if body_text else msg.get("snippet_preview", "")
                    
                    # Sentiment Analysis
                    sentiment = watcher.analyze_sentiment(msg_body)
                    
                    # Log to Sheets
                    ts = msg.get("ts")
                    received_at = datetime.fromtimestamp(ts).isoformat()
                    
                    reply_data = {
                        'received_at': received_at,
                        'from_email': from_email,
                        'from_name': msg.get("from_name", ""),
                        'subject': subject,
                        'body_text': msg_body,
                        'sentiment': sentiment,
                        'original_sender': msg.get("to")[0] if msg.get("to") else "unknown",
                        'thread_id': msg.get('conversation_id')
                    }
                    
                    try:
                        if sheets.log_reply(reply_data):
                            found_count += 1
                            logger.info(f"✅ Logged reply {found_count} from {from_email}")
                        else:
                            logger.info(f"⏭️ Skipped duplicate from {from_email}")
                    except Exception as le:
                        logger.error(f"❌ Failed to log reply from {from_email}: {le}")
                        
        except Exception as e:
            logger.error(f"❌ Error on page {page}: {e}")
            continue

    logger.info(f"🎉 SYNC COMPLETED. Total 'real' replies found and logged: {found_count}")

if __name__ == "__main__":
    sync_historical_replies()
